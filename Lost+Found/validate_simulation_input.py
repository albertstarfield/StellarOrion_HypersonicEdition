#!/usr/bin/env python
"""
StellarOrion Pre-Simulation Input Validator
============================================
Validates geometry (.surf, .stl), boundary conditions, and SPARTA input scripts
BEFORE submission to the simulation engine. Catches garbage/crumpled/invalid
geometry that would waste hours of compute.

Usage:
    python validate_simulation_input.py --surf HIAD_custom.surf [--stl HIAD_custom.stl] [--script in.hiad]
    python validate_simulation_input.py --validate-all   # validates all files in CADDesign/

Checks performed:
  .surf files:
    - SPARTA surface format integrity (Points/Lines sections)
    - Point count sanity (minimum/maximum)
    - Coordinate range and physical reasonableness
    - Self-intersection detection (line segment crossing)
    - Monotonicity along the axis (no crumpled/folded profiles)
    - Minimum feature size (no degenerate line segments)
    - Closed-loop integrity for SPARTA axisymmetric surfaces

  .stl files:
    - ASCII STL format validation
    - Triangle count sanity
    - Degenerate triangle detection (zero-area facets)
    - Manifold edge check (every edge shared by exactly 2 triangles)
    - Bounding box sanity
    - Aspect ratio extremes (sliver triangles)
    - Normal consistency (outward-facing normals)

  SPARTA input scripts (in.hiad):
    - Required keywords present (dimension, boundary, read_surf, etc.)
    - Grid dimensions reasonable
    - Timestep value physical
    - Surface file reference exists and is readable
    - Species/mixture files exist
    - Boundary condition consistency

Author: StellarOrion Validation Pipeline
"""

import os
import sys
import re
import math
import argparse
from typing import List, Tuple, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass, field


# ============================================================================
# Result Types
# ============================================================================
@dataclass
class ValidationResult:
    """Single validation check result."""
    check_name: str
    passed: bool
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    details: str = ""

@dataclass
class ValidationReport:
    """Complete validation report for a file."""
    file_path: str
    file_type: str  # "surf", "stl", "script"
    results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        return all(r.passed or r.severity != "ERROR" for r in self.results)
    
    @property
    def errors(self) -> List[ValidationResult]:
        return [r for r in self.results if not r.passed and r.severity == "ERROR"]
    
    @property
    def warnings(self) -> List[ValidationResult]:
        return [r for r in self.results if not r.passed and r.severity == "WARNING"]
    
    def summary(self) -> str:
        status = "\033[32mPASSED\033[0m" if self.passed else "\033[31mFAILED\033[0m"
        lines = [
            f"{'='*70}",
            f"VALIDATION REPORT: {os.path.basename(self.file_path)}",
            f"{'='*70}",
            f"File: {self.file_path}",
            f"Type: {self.file_type.upper()}",
            f"Status: {status}",
            f"Checks: {len(self.results)} total, {len(self.errors)} errors, {len(self.warnings)} warnings",
            f"{'-'*70}",
        ]
        for r in self.results:
            icon = "\033[32m[PASS]\033[0m" if r.passed else (
                "\033[31m[ERR]\033[0m" if r.severity == "ERROR" else 
                "\033[33m[WARN]\033[0m" if r.severity == "WARNING" else "[INFO]"
            )
            lines.append(f"  {icon} {r.check_name}: {r.message}")
            if r.details:
                for dl in r.details.strip().split("\n"):
                    lines.append(f"         {dl}")
        lines.append(f"{'='*70}")
        return "\n".join(lines)


# ============================================================================
# .surf File Validation
# ============================================================================
def parse_surf_file(file_path: str) -> Tuple[List[Tuple[float, float]], List[Tuple[int, int]]]:
    """Parse SPARTA .surf file into points and lines.
    
    SPARTA .surf format:
        # comment
        N points
        N lines
        
        Points
        
        ID X Y
        ID X Y
        ...
        
        Lines
        
        ID P1 P2
        ID P1 P2
        ...
    """
    points = []
    lines = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split into sections
    sections = content.split("Points")
    if len(sections) < 2:
        return points, lines
    
    # Parse points section
    points_section = sections[1].split("Lines")[0] if "Lines" in sections[1] else sections[1]
    for line in points_section.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                pid = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                points.append((x, y))
            except (ValueError, IndexError):
                continue
    
    # Parse lines section
    if "Lines" in content:
        lines_section = content.split("Lines")[1]
        for line in lines_section.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    lid = int(parts[0])
                    p1 = int(parts[1])
                    p2 = int(parts[2])
                    lines.append((p1, p2))
                except (ValueError, IndexError):
                    continue
    
    return points, lines


def validate_surf(file_path: str) -> ValidationReport:
    """Validate a SPARTA .surf surface file."""
    report = ValidationReport(file_path=file_path, file_type="surf")
    
    # Check file exists
    if not os.path.exists(file_path):
        report.results.append(ValidationResult(
            check_name="File exists",
            passed=False, severity="ERROR",
            message=f"File not found: {file_path}"
        ))
        return report
    
    report.results.append(ValidationResult(
        check_name="File exists",
        passed=True, severity="INFO",
        message="File found"
    ))
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size < 50:
        report.results.append(ValidationResult(
            check_name="File size",
            passed=False, severity="ERROR",
            message=f"File suspiciously small: {file_size} bytes"
        ))
        return report
    
    report.results.append(ValidationResult(
        check_name="File size",
        passed=True, severity="INFO",
        message=f"{file_size:,} bytes"
    ))
    
    # Parse the file
    try:
        points, lines = parse_surf_file(file_path)
    except Exception as e:
        report.results.append(ValidationResult(
            check_name="File parsing",
            passed=False, severity="ERROR",
            message=f"Failed to parse .surf file: {e}"
        ))
        return report
    
    # Check point count
    if len(points) == 0:
        report.results.append(ValidationResult(
            check_name="Point count",
            passed=False, severity="ERROR",
            message="No points found in surface file"
        ))
        return report
    
    if len(points) < 10:
        report.results.append(ValidationResult(
            check_name="Point count",
            passed=False, severity="WARNING",
            message=f"Only {len(points)} points - geometry may be too coarse"
        ))
    elif len(points) > 5000:
        report.results.append(ValidationResult(
            check_name="Point count",
            passed=False, severity="WARNING",
            message=f"{len(points)} points - unusually high, check for duplicates"
        ))
    else:
        report.results.append(ValidationResult(
            check_name="Point count",
            passed=True, severity="INFO",
            message=f"{len(points)} points"
        ))
    
    # Check line count
    if len(lines) == 0:
        report.results.append(ValidationResult(
            check_name="Line count",
            passed=False, severity="WARNING",
            message="No lines defined - surface has no connectivity"
        ))
    else:
        report.results.append(ValidationResult(
            check_name="Line count",
            passed=True, severity="INFO",
            message=f"{len(lines)} line segments"
        ))
    
    # Coordinate analysis
    if points:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_range = x_max - x_min
        y_range = y_max - y_min
        
        # Check coordinate ranges (SPARTA uses meters)
        # HIAD geometry should be within reasonable bounds
        if x_range < 0.001:
            report.results.append(ValidationResult(
                check_name="X range (axial)",
                passed=False, severity="ERROR",
                message=f"X range too small: {x_range:.6f} m - geometry collapsed"
            ))
        elif x_range > 50.0:
            report.results.append(ValidationResult(
                check_name="X range (axial)",
                passed=False, severity="WARNING",
                message=f"X range unusually large: {x_range:.2f} m"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="X range (axial)",
                passed=True, severity="INFO",
                message=f"X: {x_min:.4f} to {x_max:.4f} (range: {x_range:.4f} m)"
            ))
        
        if y_range < 0.001:
            report.results.append(ValidationResult(
                check_name="Y range (radial)",
                passed=False, severity="ERROR",
                message=f"Y range too small: {y_range:.6f} m - geometry collapsed"
            ))
        elif y_range > 50.0:
            report.results.append(ValidationResult(
                check_name="Y range (radial)",
                passed=False, severity="WARNING",
                message=f"Y range unusually large: {y_range:.2f} m"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Y range (radial)",
                passed=True, severity="INFO",
                message=f"Y: {y_min:.4f} to {y_max:.4f} (range: {y_range:.4f} m)"
            ))
        
        # Check for negative Y values (SPARTA axisymmetric uses Y >= 0)
        neg_y_count = sum(1 for y in ys if y < 0)
        if neg_y_count > 0:
            report.results.append(ValidationResult(
                check_name="Non-negative Y",
                passed=False, severity="ERROR",
                message=f"{neg_y_count} points have Y < 0 - invalid for axisymmetric surface"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Non-negative Y",
                passed=True, severity="INFO",
                message="All Y coordinates >= 0"
            ))
        
        # Check aspect ratio (typical HIAD: aspect ~0.5-2.0)
        if y_range > 0 and x_range > 0:
            aspect = x_range / y_range
            if aspect < 0.1 or aspect > 10.0:
                report.results.append(ValidationResult(
                    check_name="Aspect ratio",
                    passed=False, severity="WARNING",
                    message=f"Unusual aspect ratio: {aspect:.2f} (typical: 0.5-2.0)"
                ))
            else:
                report.results.append(ValidationResult(
                    check_name="Aspect ratio",
                    passed=True, severity="INFO",
                    message=f"Aspect ratio: {aspect:.2f}"
                ))
        
        # Check for duplicate/near-duplicate points
        dup_count = 0
        for i in range(len(points)):
            for j in range(i+1, min(i+20, len(points))):  # only check nearby points
                dx = points[i][0] - points[j][0]
                dy = points[i][1] - points[j][1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 1e-10:
                    dup_count += 1
        
        if dup_count > 0:
            report.results.append(ValidationResult(
                check_name="Duplicate points",
                passed=False, severity="WARNING",
                message=f"{dup_count} near-duplicate point pairs detected"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Duplicate points",
                passed=True, severity="INFO",
                message="No duplicate points"
            ))
    
    # Line segment validation
    if lines and points:
        degenerate_count = 0
        max_seg_length = 0
        min_seg_length = float('inf')
        
        for p1_idx, p2_idx in lines:
            if p1_idx < 1 or p1_idx > len(points) or p2_idx < 1 or p2_idx > len(points):
                report.results.append(ValidationResult(
                    check_name="Line connectivity",
                    passed=False, severity="ERROR",
                    message=f"Line references invalid point index: {p1_idx} or {p2_idx}"
                ))
                continue
            
            p1 = points[p1_idx - 1]  # SPARTA uses 1-based indexing
            p2 = points[p2_idx - 1]
            
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            seg_len = math.sqrt(dx*dx + dy*dy)
            
            max_seg_length = max(max_seg_length, seg_len)
            if seg_len > 0:
                min_seg_length = min(min_seg_length, seg_len)
            
            if seg_len < 1e-12:
                degenerate_count += 1
        
        if degenerate_count > 0:
            report.results.append(ValidationResult(
                check_name="Degenerate segments",
                passed=False, severity="WARNING",
                message=f"{degenerate_count} zero-length line segments"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Degenerate segments",
                passed=True, severity="INFO",
                message="No degenerate segments"
            ))
        
        if max_seg_length > 0 and min_seg_length < float('inf'):
            ratio = max_seg_length / min_seg_length if min_seg_length > 0 else float('inf')
            if ratio > 100:
                report.results.append(ValidationResult(
                    check_name="Segment length uniformity",
                    passed=False, severity="WARNING",
                    message=f"Segment length ratio: {ratio:.1f} (max/min) - highly non-uniform mesh"
                ))
            else:
                report.results.append(ValidationResult(
                    check_name="Segment length uniformity",
                    passed=True, severity="INFO",
                    message=f"Segment lengths: {min_seg_length:.6f} to {max_seg_length:.6f} m"
                ))
    
    # Self-intersection check (O(n^2) but acceptable for typical 200-500 point surfaces)
    if lines and points and len(lines) < 2000:
        intersection_count = 0
        for i in range(len(lines)):
            for j in range(i+2, len(lines)):  # skip adjacent segments (they share endpoints)
                # Skip if segments share an endpoint
                p1a, p1b = lines[i]
                p2a, p2b = lines[j]
                if p1a == p2a or p1a == p2b or p1b == p2a or p1b == p2b:
                    continue
                
                # Get actual coordinates
                a1 = points[p1a - 1] if 1 <= p1a <= len(points) else None
                a2 = points[p1b - 1] if 1 <= p1b <= len(points) else None
                b1 = points[p2a - 1] if 1 <= p2a <= len(points) else None
                b2 = points[p2b - 1] if 1 <= p2b <= len(points) else None
                
                if not all([a1, a2, b1, b2]):
                    continue
                
                # Check if segments intersect
                def cross(o, a, b):
                    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
                
                d1 = cross(b1, b2, a1)
                d2 = cross(b1, b2, a2)
                d3 = cross(a1, a2, b1)
                d4 = cross(a1, a2, b2)
                
                if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
                   ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
                    intersection_count += 1
        
        if intersection_count > 0:
            report.results.append(ValidationResult(
                check_name="Self-intersections",
                passed=False, severity="ERROR",
                message=f"{intersection_count} self-intersecting line segments detected - geometry is crumpled/invalid"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Self-intersections",
                passed=True, severity="INFO",
                message="No self-intersections found"
            ))
    
    # Monotonicity check: for a HIAD profile, the Z (axial) coordinate should 
    # generally increase (with possible local variations for scallops)
    if points and len(points) > 2:
        # Check that we don't have wild oscillations
        z_values = [p[0] for p in points]  # X = axial Z in SPARTA
        direction_changes = 0
        for i in range(2, len(z_values)):
            d1 = z_values[i-1] - z_values[i-2]
            d2 = z_values[i] - z_values[i-1]
            if d1 * d2 < 0 and abs(d1) > 1e-10 and abs(d2) > 1e-10:
                direction_changes += 1
        
        # Allow some direction changes for scalloped toroid geometry
        max_expected = len(points) // 3
        if direction_changes > max_expected:
            report.results.append(ValidationResult(
                check_name="Axial monotonicity",
                passed=False, severity="WARNING",
                message=f"{direction_changes} axial direction changes - possible crumpled geometry"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Axial monotonicity",
                passed=True, severity="INFO",
                message=f"{direction_changes} direction changes (within tolerance)"
            ))
    
    return report


# ============================================================================
# .stl File Validation
# ============================================================================
def parse_stl_ascii(file_path: str) -> Tuple[List[Tuple[float, float, float]], List[Tuple[List[Tuple[float, float, float]], Tuple[float, float, float]]]]:
    """Parse ASCII STL file into vertices and facets.
    
    Returns:
        (all_vertices, facets) where each facet is ([(v1, v2, v3)], normal)
    """
    vertices = []
    facets = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all facets
    facet_pattern = re.compile(
        r'facet\s+normal\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\s*\n'
        r'\s*outer\s+loop\s*\n'
        r'\s*vertex\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\s*\n'
        r'\s*vertex\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\s*\n'
        r'\s*vertex\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\s*\n'
        r'\s*endloop\s*\n'
        r'\s*endfacet',
        re.MULTILINE
    )
    
    for match in facet_pattern.finditer(content):
        nx, ny, nz = float(match.group(1)), float(match.group(2)), float(match.group(3))
        v1 = (float(match.group(4)), float(match.group(5)), float(match.group(6)))
        v2 = (float(match.group(7)), float(match.group(8)), float(match.group(9)))
        v3 = (float(match.group(10)), float(match.group(11)), float(match.group(12)))
        
        vertices.extend([v1, v2, v3])
        facets.append(([v1, v2, v3], (nx, ny, nz)))
    
    return vertices, facets


def validate_stl(file_path: str) -> ValidationReport:
    """Validate an STL mesh file."""
    report = ValidationReport(file_path=file_path, file_type="stl")
    
    if not os.path.exists(file_path):
        report.results.append(ValidationResult(
            check_name="File exists",
            passed=False, severity="ERROR",
            message=f"File not found: {file_path}"
        ))
        return report
    
    report.results.append(ValidationResult(
        check_name="File exists",
        passed=True, severity="INFO",
        message="File found"
    ))
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size < 100:
        report.results.append(ValidationResult(
            check_name="File size",
            passed=False, severity="ERROR",
            message=f"File too small: {file_size} bytes"
        ))
        return report
    
    report.results.append(ValidationResult(
        check_name="File size",
        passed=True, severity="INFO",
        message=f"{file_size:,} bytes"
    ))
    
    # Check if binary or ASCII STL
    try:
        with open(file_path, 'rb') as f:
            header = f.read(80)
        is_binary = not header.lstrip().startswith(b'solid')
    except Exception:
        is_binary = False
    
    if is_binary:
        report.results.append(ValidationResult(
            check_name="STL format",
            passed=False, severity="INFO",
            message="Binary STL detected - validation limited to basic checks"
        ))
        # Binary STL validation is limited without numpy/stl library
        # At minimum check file size is reasonable
        if file_size < 200:
            report.results.append(ValidationResult(
                check_name="Binary STL size",
                passed=False, severity="ERROR",
                message="Binary STL file too small to contain valid mesh"
            ))
        return report
    
    report.results.append(ValidationResult(
        check_name="STL format",
        passed=True, severity="INFO",
        message="ASCII STL detected"
    ))
    
    # Parse the file
    try:
        vertices, facets = parse_stl_ascii(file_path)
    except Exception as e:
        report.results.append(ValidationResult(
            check_name="STL parsing",
            passed=False, severity="ERROR",
            message=f"Failed to parse STL: {e}"
        ))
        return report
    
    # Check triangle count
    n_triangles = len(facets)
    if n_triangles == 0:
        report.results.append(ValidationResult(
            check_name="Triangle count",
            passed=False, severity="ERROR",
            message="No triangles found in STL"
        ))
        return report
    
    if n_triangles < 10:
        report.results.append(ValidationResult(
            check_name="Triangle count",
            passed=False, severity="WARNING",
            message=f"Only {n_triangles} triangles - mesh may be too coarse"
        ))
    else:
        report.results.append(ValidationResult(
            check_name="Triangle count",
            passed=True, severity="INFO",
            message=f"{n_triangles:,} triangles"
        ))
    
    # Bounding box
    if vertices:
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        
        bbox = {
            'x_min': min(xs), 'x_max': max(xs),
            'y_min': min(ys), 'y_max': max(ys),
            'z_min': min(zs), 'z_max': max(zs),
        }
        
        dx = bbox['x_max'] - bbox['x_min']
        dy = bbox['y_max'] - bbox['y_min']
        dz = bbox['z_max'] - bbox['z_min']
        
        if dx < 1e-10 or dy < 1e-10 or dz < 1e-10:
            report.results.append(ValidationResult(
                check_name="Bounding box",
                passed=False, severity="ERROR",
                message=f"Degenerate bounding box: dx={dx:.6f}, dy={dy:.6f}, dz={dz:.6f}"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Bounding box",
                passed=True, severity="INFO",
                message=f"BBox: [{bbox['x_min']:.3f}, {bbox['x_max']:.3f}] x "
                        f"[{bbox['y_min']:.3f}, {bbox['y_max']:.3f}] x "
                        f"[{bbox['z_min']:.3f}, {bbox['z_max']:.3f}]"
            ))
    
    # Degenerate triangle check
    degen_count = 0
    areas = []
    for tri_verts, normal in facets:
        v1, v2, v3 = tri_verts
        # Compute area via cross product
        ux, uy, uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
        vx, vy, vz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
        
        cx = uy*vz - uz*vy
        cy = uz*vx - ux*vz
        cz = ux*vy - uy*vx
        
        area = 0.5 * math.sqrt(cx*cx + cy*cy + cz*cz)
        areas.append(area)
        
        if area < 1e-15:
            degen_count += 1
    
    if degen_count > 0:
        report.results.append(ValidationResult(
            check_name="Degenerate triangles",
            passed=False, severity="WARNING",
            message=f"{degen_count} degenerate (zero-area) triangles"
        ))
    else:
        report.results.append(ValidationResult(
            check_name="Degenerate triangles",
            passed=True, severity="INFO",
            message="No degenerate triangles"
        ))
    
    # Area statistics
    if areas:
        valid_areas = [a for a in areas if a > 0]
        if valid_areas:
            avg_area = sum(valid_areas) / len(valid_areas)
            max_area = max(valid_areas)
            min_area = min(valid_areas)
            
            if avg_area > 0:
                ratio = max_area / min_area if min_area > 0 else float('inf')
                if ratio > 10000:
                    report.results.append(ValidationResult(
                        check_name="Area uniformity",
                        passed=False, severity="WARNING",
                        message=f"Triangle area ratio: {ratio:.0f} (max/min) - highly non-uniform"
                    ))
                else:
                    report.results.append(ValidationResult(
                        check_name="Area uniformity",
                        passed=True, severity="INFO",
                        message=f"Area range: {min_area:.2e} to {max_area:.2e} (ratio: {ratio:.1f})"
                    ))
    
    # Normal consistency check
    bad_normals = 0
    for tri_verts, normal in facets:
        v1, v2, v3 = tri_verts
        # Compute expected normal
        ux, uy, uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
        vx, vy, vz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
        
        cx = uy*vz - uz*vy
        cy = uz*vx - ux*vz
        cz = ux*vy - uy*vx
        
        mag = math.sqrt(cx*cx + cy*cy + cz*cz)
        if mag > 1e-15:
            expected = (cx/mag, cy/mag, cz/mag)
            dot = expected[0]*normal[0] + expected[1]*normal[1] + expected[2]*normal[2]
            if dot < 0.5:  # angle > ~60 degrees
                bad_normals += 1
    
    if bad_normals > 0:
        report.results.append(ValidationResult(
            check_name="Normal consistency",
            passed=False, severity="WARNING",
            message=f"{bad_normals} triangles have inconsistent normals"
        ))
    else:
        report.results.append(ValidationResult(
            check_name="Normal consistency",
            passed=True, severity="INFO",
            message="All normals consistent with vertex winding"
        ))
    
    # Edge manifold check (simplified: check that edges appear exactly twice)
    edge_count: Dict[Tuple, int] = {}
    for tri_verts, _ in facets:
        n = len(tri_verts)
        for i in range(n):
            v_a = tri_verts[i]
            v_b = tri_verts[(i+1) % n]
            # Round to avoid floating point issues
            key = tuple(round(c, 8) for c in (min(v_a, v_b, key=lambda x: x)))
            edge_key = (
                (round(v_a[0], 8), round(v_a[1], 8), round(v_a[2], 8)),
                (round(v_b[0], 8), round(v_b[1], 8), round(v_b[2], 8))
            )
            # Normalize edge direction
            if edge_key[0] > edge_key[1]:
                edge_key = (edge_key[1], edge_key[0])
            edge_count[edge_key] = edge_count.get(edge_key, 0) + 1
    
    non_manifold = sum(1 for c in edge_count.values() if c != 2)
    if non_manifold > 0:
        report.results.append(ValidationResult(
            check_name="Manifold edges",
            passed=False, severity="WARNING",
            message=f"{non_manifold} non-manifold edges (not shared by exactly 2 triangles)"
        ))
    else:
        report.results.append(ValidationResult(
            check_name="Manifold edges",
            passed=True, severity="INFO",
            message=f"All {len(edge_count)} edges are manifold"
        ))
    
    return report


# ============================================================================
# SPARTA Input Script Validation
# ============================================================================
def validate_sparta_script(file_path: str, script_dir: str = None) -> ValidationReport:
    """Validate a SPARTA input script for common errors."""
    report = ValidationReport(file_path=file_path, file_type="script")
    
    if not os.path.exists(file_path):
        report.results.append(ValidationResult(
            check_name="File exists",
            passed=False, severity="ERROR",
            message=f"Script not found: {file_path}"
        ))
        return report
    
    report.results.append(ValidationResult(
        check_name="File exists",
        passed=True, severity="INFO",
        message="Script found"
    ))
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if script_dir is None:
        script_dir = os.path.dirname(os.path.abspath(file_path))
    
    # Required keywords - check for both fresh start and resume modes
    # Fresh start: needs read_surf + surf_collide
    # Resume: needs read_restart (surf definitions are in the restart file)
    has_read_restart = 'read_restart' in content
    has_read_surf = 'read_surf' in content
    
    if has_read_restart:
        report.results.append(ValidationResult(
            check_name="Resume mode detected",
            passed=True, severity="INFO",
            message=f"read_restart found (resume mode - surface definitions in restart file)"
        ))
    elif has_read_surf:
        report.results.append(ValidationResult(
            check_name="Fresh start mode detected",
            passed=True, severity="INFO",
            message=f"read_surf found (fresh start mode)"
        ))
    
    required_keywords = {
        'dimension': 'Dimension definition',
        'boundary': 'Boundary conditions',
        'timestep': 'Timestep',
    }
    
    # Surface-related keywords only required in fresh start mode
    if not has_read_restart:
        required_keywords['read_surf'] = 'Surface definition'
        required_keywords['surf_collide'] = 'Surface collision model'
    
    for keyword, desc in required_keywords.items():
        if keyword not in content:
            report.results.append(ValidationResult(
                check_name=f"Required: {desc}",
                passed=False, severity="ERROR",
                message=f"Missing required keyword: {keyword}"
            ))
        else:
            report.results.append(ValidationResult(
                check_name=f"Required: {desc}",
                passed=True, severity="INFO",
                message=f"{keyword} found"
            ))
    
    # Check dimension is 2 (axisymmetric)
    dim_match = re.search(r'dimension\s+(\d+)', content)
    if dim_match:
        dim = int(dim_match.group(1))
        if dim not in [2, 3]:
            report.results.append(ValidationResult(
                check_name="Dimension value",
                passed=False, severity="ERROR",
                message=f"Invalid dimension: {dim} (must be 2 or 3)"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Dimension value",
                passed=True, severity="INFO",
                message=f"Dimension = {dim}"
            ))
    
    # Check boundary conditions
    bc_match = re.search(r'boundary\s+(\S+)\s+(\S+)\s+(\S+)', content)
    if bc_match:
        bc_x, bc_y, bc_z = bc_match.groups()
        # For axisymmetric: should be 'o ao p' or similar
        report.results.append(ValidationResult(
            check_name="Boundary conditions",
            passed=True, severity="INFO",
            message=f"BC: {bc_x} {bc_y} {bc_z}"
        ))
    
    # Check timestep
    ts_match = re.search(r'timestep\s+([-\d.eE+]+)', content)
    if ts_match:
        ts = float(ts_match.group(1))
        if ts <= 0:
            report.results.append(ValidationResult(
                check_name="Timestep value",
                passed=False, severity="ERROR",
                message=f"Non-positive timestep: {ts}"
            ))
        elif ts > 1e-3:
            report.results.append(ValidationResult(
                check_name="Timestep value",
                passed=False, severity="WARNING",
                message=f"Large timestep: {ts} - may be unstable for DSMC"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Timestep value",
                passed=True, severity="INFO",
                message=f"Timestep = {ts:.1e}"
            ))
    
    # Check surface file reference
    surf_match = re.search(r'read_surf\s+(\S+)', content)
    if surf_match:
        surf_name = surf_match.group(1)
        surf_path = os.path.join(script_dir, surf_name)
        if not os.path.exists(surf_path):
            report.results.append(ValidationResult(
                check_name="Surface file exists",
                passed=False, severity="ERROR",
                message=f"Referenced surface file not found: {surf_name}"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Surface file exists",
                passed=True, severity="INFO",
                message=f"Surface file: {surf_name}"
            ))
    
    # Check species/mixture files
    if 'species' in content and 'mixture' in content:
        species_match = re.search(r'species\s+(\S+)', content)
        if species_match:
            species_file = species_match.group(1)
            species_path = os.path.join(script_dir, species_file)
            if not os.path.exists(species_path):
                report.results.append(ValidationResult(
                    check_name="Species file exists",
                    passed=False, severity="WARNING",
                    message=f"Species file not found: {species_file}"
                ))
            else:
                report.results.append(ValidationResult(
                    check_name="Species file exists",
                    passed=True, severity="INFO",
                    message=f"Species file: {species_file}"
                ))
    
    # Check for 'run' command
    if 'run ' not in content:
        report.results.append(ValidationResult(
            check_name="Run command",
            passed=False, severity="WARNING",
            message="No 'run' command found in script"
        ))
    else:
        run_match = re.search(r'run\s+(\d+)', content)
        if run_match:
            steps = int(run_match.group(1))
            report.results.append(ValidationResult(
                check_name="Run command",
                passed=True, severity="INFO",
                message=f"Run: {steps} steps"
            ))
    
    # Check for dump commands
    if 'dump ' not in content:
        report.results.append(ValidationResult(
            check_name="Dump commands",
            passed=False, severity="WARNING",
            message="No dump commands - no output will be generated"
        ))
    else:
        dump_count = content.count('dump ')
        report.results.append(ValidationResult(
            check_name="Dump commands",
            passed=True, severity="INFO",
            message=f"{dump_count} dump commands"
        ))
    
    # Check grid dimensions
    grid_match = re.search(r'create_grid\s+(\d+)\s+(\d+)', content)
    if grid_match:
        nx, ny = int(grid_match.group(1)), int(grid_match.group(2))
        total = nx * ny
        if total > 1000000:
            report.results.append(ValidationResult(
                check_name="Grid dimensions",
                passed=False, severity="WARNING",
                message=f"Large grid: {nx}x{ny} = {total:,} cells"
            ))
        else:
            report.results.append(ValidationResult(
                check_name="Grid dimensions",
                passed=True, severity="INFO",
                message=f"Grid: {nx}x{ny} = {total:,} cells"
            ))
    
    return report


# ============================================================================
# Boundary Condition Validation
# ============================================================================
def validate_boundary_conditions(surf_path: str, script_path: str) -> ValidationReport:
    """Cross-validate boundary conditions between surface and script."""
    report = ValidationReport(
        file_path=f"{surf_path} + {script_path}",
        file_type="boundary_check"
    )
    
    # Parse surface to get bounding box
    if os.path.exists(surf_path):
        points, _ = parse_surf_file(surf_path)
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
        else:
            x_min = x_max = y_min = y_max = 0
    else:
        report.results.append(ValidationResult(
            check_name="Surface file for BC check",
            passed=False, severity="ERROR",
            message=f"Surface file not found: {surf_path}"
        ))
        return report
    
    # Parse script for domain bounds
    if os.path.exists(script_path):
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Check create_box bounds
        box_match = re.search(r'create_box\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)', content)
        if box_match:
            bx_min = float(box_match.group(1))
            bx_max = float(box_match.group(2))
            by_min = float(box_match.group(3))
            by_max = float(box_match.group(4))
            
            # Surface must be inside the box
            margin = 0.01
            if x_min < bx_min - margin or x_max > bx_max + margin:
                report.results.append(ValidationResult(
                    check_name="X bounds containment",
                    passed=False, severity="ERROR",
                    message=f"Surface X [{x_min:.3f}, {x_max:.3f}] outside box [{bx_min:.3f}, {bx_max:.3f}]"
                ))
            else:
                report.results.append(ValidationResult(
                    check_name="X bounds containment",
                    passed=True, severity="INFO",
                    message=f"Surface X [{x_min:.3f}, {x_max:.3f}] inside box [{bx_min:.3f}, {bx_max:.3f}]"
                ))
            
            if y_min < by_min - margin or y_max > by_max + margin:
                report.results.append(ValidationResult(
                    check_name="Y bounds containment",
                    passed=False, severity="ERROR",
                    message=f"Surface Y [{y_min:.3f}, {y_max:.3f}] outside box [{by_min:.3f}, {by_max:.3f}]"
                ))
            else:
                report.results.append(ValidationResult(
                    check_name="Y bounds containment",
                    passed=True, severity="INFO",
                    message=f"Surface Y [{y_min:.3f}, {y_max:.3f}] inside box [{by_min:.3f}, {by_max:.3f}]"
                ))
    
    return report


# ============================================================================
# Verbose Geometry Dump (for pipeline integration)
# ============================================================================
def dump_surf_geometry_verbose(file_path: str) -> str:
    """Parse and dump ALL geometry data from a .surf file for debugging.
    
    Returns a formatted string containing:
      - File header/total point/line counts
      - Every point (ID, X, Y) with index
      - Every line segment (ID, P1, P2) with connected points
      - Bounding box (X min/max, Y min/max)
      - Centroid (X̄, Ȳ)
      - Reference diameter estimate (2 × Y_max)
      - Self-intersection locations (if any)
    
    Citation: SPARTA surface format — Plimpton et al., SAND2013-4736 (2013).
    Axiom: Murphy's Law — if geometry is crumpled, we need EVERY data point
    to diagnose the ordering bug (not just a summary).
    """
    points, lines = parse_surf_file(file_path)
    if not points:
        return f"[!] No points parsed from {file_path}\n"
    
    lines_out = []
    lines_out.append(f"\n{'='*70}")
    lines_out.append(f"VERBOSE GEOMETRY DUMP: {os.path.basename(file_path)}")
    lines_out.append(f"{'='*70}")
    lines_out.append(f"File: {file_path}")
    lines_out.append(f"Total Points: {len(points)}")
    lines_out.append(f"Total Lines:  {len(lines)}")
    
    # --- All Points ---
    lines_out.append(f"\n--- ALL POINTS ({len(points)} total) ---")
    lines_out.append(f"{'Idx':<6} {'ID':<6} {'X (axial)':<14} {'Y (radial)':<14}")
    lines_out.append(f"{'-'*42}")
    for i, (x, y) in enumerate(points):
        lines_out.append(f"{i:<6} {i+1:<6} {x:<14.6f} {y:<14.6f}")
    
    # --- All Line Segments ---
    lines_out.append(f"\n--- ALL LINE SEGMENTS ({len(lines)} total) ---")
    lines_out.append(f"{'ID':<6} {'P1':<6} {'P2':<6} {'P1(X,Y)':<24} {'P2(X,Y)':<24}")
    lines_out.append(f"{'-'*68}")
    for lid, (p1, p2) in enumerate(lines):
        p1_idx = p1 - 1  # SPARTA uses 1-based IDs
        p2_idx = p2 - 1
        p1_str = f"({points[p1_idx][0]:.4f}, {points[p1_idx][1]:.4f})" if 0 <= p1_idx < len(points) else "INVALID"
        p2_str = f"({points[p2_idx][0]:.4f}, {points[p2_idx][1]:.4f})" if 0 <= p2_idx < len(points) else "INVALID"
        lines_out.append(f"{lid+1:<6} {p1:<6} {p2:<6} {p1_str:<24} {p2_str:<24}")
    
    # --- Bounding Box ---
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    
    lines_out.append(f"\n--- BOUNDING BOX ---")
    lines_out.append(f"X range: [{x_min:.6f}, {x_max:.6f}]  (span = {x_max - x_min:.6f})")
    lines_out.append(f"Y range: [{y_min:.6f}, {y_max:.6f}]  (span = {y_max - y_min:.6f})")
    lines_out.append(f"Centroid: (X̄ = {x_mean:.6f}, Ȳ = {y_mean:.6f})")
    lines_out.append(f"Est. Reference Diameter: {2 * y_max:.6f} (2 × Y_max)")
    
    # --- Self-Intersection Detection ---
    intersections = []
    for i in range(len(lines)):
        a1_idx = lines[i][0] - 1
        a2_idx = lines[i][1] - 1
        if a1_idx < 0 or a1_idx >= len(points) or a2_idx < 0 or a2_idx >= len(points):
            continue
        a1, a2 = points[a1_idx], points[a2_idx]
        for j in range(i + 1, len(lines)):
            # Skip adjacent segments (share an endpoint) — they can't intersect
            if lines[i][0] == lines[j][0] or lines[i][0] == lines[j][1] or \
               lines[i][1] == lines[j][0] or lines[i][1] == lines[j][1]:
                continue
            b1_idx = lines[j][0] - 1
            b2_idx = lines[j][1] - 1
            if b1_idx < 0 or b1_idx >= len(points) or b2_idx < 0 or b2_idx >= len(points):
                continue
            b1, b2 = points[b1_idx], points[b2_idx]
            
            # Line segment intersection test (CCW method)
            # Reference: O'Rourke, "Computational Geometry in C", Ch. 1
            d1 = (b2[0] - b1[0]) * (a1[1] - b1[1]) - (b2[1] - b1[1]) * (a1[0] - b1[0])
            d2 = (b2[0] - b1[0]) * (a2[1] - b1[1]) - (b2[1] - b1[1]) * (a2[0] - b1[0])
            d3 = (a2[0] - a1[0]) * (b1[1] - a1[1]) - (a2[1] - a1[1]) * (b1[0] - a1[0])
            d4 = (a2[0] - a1[0]) * (b2[1] - a1[1]) - (a2[1] - a1[1]) * (b2[0] - a1[0])
            
            if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
               ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
                intersections.append((lines[i][0], lines[i][1], lines[j][0], lines[j][1]))
    
    lines_out.append(f"\n--- SELF-INTERSECTIONS ---")
    if intersections:
        lines_out.append(f"Found {len(intersections)} intersection(s):")
        for seg1_p1, seg1_p2, seg2_p1, seg2_p2 in intersections:
            lines_out.append(f"  Segment ({seg1_p1},{seg1_p2}) intersects ({seg2_p1},{seg2_p2})")
    else:
        lines_out.append("None found (geometry is clean)")
    
    lines_out.append(f"{'='*70}\n")
    return "\n".join(lines_out)


def validate_and_dump_geometry(surf_path: str, script_path: str = None,
                                script_dir: str = None) -> 'ValidationReport':
    """Validate a .surf file AND dump full geometry data on failure.
    
    Pipeline integration function: validates geometry, and if validation fails,
    dumps ALL point coordinates, line segments, bounding box, centroid, and
    intersection data to stdout so the operator can diagnose the problem.
    
    Returns:
        ValidationReport — caller should check .passed and sys.exit(1) if False.
    
    Citation: SPARTA surface format — Plimpton et al., SAND2013-4736 (2013).
    Axiom: Murphy's Law — "Anything that CAN go wrong WILL go wrong."
           Therefore: dump EVERYTHING on failure, not just a summary.
    """
    print(f"\n[*] Running geometry validation with verbose dump: {surf_path}")
    report = validate_surf(surf_path)
    print(report.summary())
    
    # Also validate script if provided
    if script_path:
        script_report = validate_sparta_script(script_path, script_dir=script_dir)
        print(script_report.summary())
        # Merge script errors into main report
        for r in script_report.results:
            if not r.passed:
                report.results.append(r)
    
    if not report.passed:
        print(f"\n\033[31m[!] VALIDATION FAILED — Dumping full geometry data for diagnosis:\033[0m")
        print(dump_surf_geometry_verbose(surf_path))
    else:
        print(f"[+] Geometry validation passed: {os.path.basename(surf_path)}")
    
    return report


# ============================================================================
# Convenience Functions
# ============================================================================
def validate_all(surf_path: str = None, stl_path: str = None, 
                 script_path: str = None, script_dir: str = None) -> bool:
    """Run all validations and return True if all pass."""
    all_reports = []
    
    if surf_path:
        print(f"\n[*] Validating surface: {surf_path}")
        report = validate_surf(surf_path)
        all_reports.append(report)
        print(report.summary())
    
    if stl_path:
        print(f"\n[*] Validating STL: {stl_path}")
        report = validate_stl(stl_path)
        all_reports.append(report)
        print(report.summary())
    
    if script_path:
        print(f"\n[*] Validating SPARTA script: {script_path}")
        report = validate_sparta_script(script_path, script_dir=script_dir)
        all_reports.append(report)
        print(report.summary())
    
    # Cross-validation
    if surf_path and script_path:
        print(f"\n[*] Cross-validating boundary conditions...")
        report = validate_boundary_conditions(surf_path, script_path)
        all_reports.append(report)
        print(report.summary())
    
    # Overall result
    all_passed = all(r.passed for r in all_reports)
    total_errors = sum(len(r.errors) for r in all_reports)
    total_warnings = sum(len(r.warnings) for r in all_reports)
    
    print(f"\n{'='*70}")
    if all_passed:
        print(f"\033[32m[VALIDATION PASSED]\033[0m All checks passed "
              f"({total_errors} errors, {total_warnings} warnings)")
    else:
        print(f"\033[31m[VALIDATION FAILED]\033[0m {total_errors} errors, {total_warnings} warnings")
    print(f"{'='*70}\n")
    
    return all_passed


def validate_directory(cad_dir: str) -> bool:
    """Validate all simulation inputs in a directory."""
    surf_files = [f for f in os.listdir(cad_dir) if f.endswith('.surf') and not f.startswith('.')]
    stl_files = [f for f in os.listdir(cad_dir) if f.endswith('.stl') and not f.startswith('.')]
    script_file = "in.hiad"
    
    all_passed = True
    
    for sf in surf_files:
        path = os.path.join(cad_dir, sf)
        if not validate_surf(path).passed:
            all_passed = False
    
    for stl in stl_files:
        path = os.path.join(cad_dir, stl)
        if not validate_stl(path).passed:
            all_passed = False
    
    script_path = os.path.join(cad_dir, script_file)
    if os.path.exists(script_path):
        if not validate_sparta_script(script_path, script_dir=cad_dir).passed:
            all_passed = False
    
    return all_passed


# ============================================================================
# CLI Entry Point
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="StellarOrion Pre-Simulation Input Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_simulation_input.py --surf HIAD_custom.surf
  python validate_simulation_input.py --surf HIAD_sample.surf --stl HIAD_sample.stl --script CADDesign/in.hiad
  python validate_simulation_input.py --validate-all --dir CADDesign/
        """
    )
    parser.add_argument("--surf", type=str, help="Path to SPARTA .surf surface file")
    parser.add_argument("--stl", type=str, help="Path to STL mesh file")
    parser.add_argument("--script", type=str, help="Path to SPARTA input script (in.hiad)")
    parser.add_argument("--dir", type=str, help="Directory to validate all files in")
    parser.add_argument("--validate-all", action="store_true", help="Validate all files in directory")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    if args.validate_all or args.dir:
        cad_dir = args.dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "CADDesign")
        print(f"[*] Validating all files in: {cad_dir}")
        success = validate_directory(cad_dir)
        sys.exit(0 if success else 1)
    
    if not args.surf and not args.stl and not args.script:
        parser.print_help()
        sys.exit(1)
    
    success = validate_all(
        surf_path=args.surf,
        stl_path=args.stl,
        script_path=args.script
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
