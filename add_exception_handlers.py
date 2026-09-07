#!/usr/bin/env python3
"""
Add exception handlers to Ada procedure/function bodies.

CORRECT approach: Track nesting using only procedure/function starts and their
matching 'end Name;' statements. Do NOT use begin/end for nesting - they are
NOT reliable nesting markers in Ada.

For each top-level procedure/function:
1. Find its start line (procedure/function declaration with 'is')
2. Find its end line by scanning forward, tracking nested procedure/function count
3. Find the 'begin' line between start and end
4. Check if there's an 'exception' block between begin and end
5. If not, insert one before the final 'end Name;'
"""

import re
import os


def find_procedure_end(lines, start_line, proc_name):
    """
    Find the matching 'end Proc_Name;' for a procedure starting at start_line.
    
    Strategy: Scan forward from start_line, tracking nested procedure/function count.
    When we see another procedure/function declaration, increment nesting.
    When we see 'end Proc_Name;' with nesting=0, that's our match.
    """
    nesting = 0
    
    # Pattern for procedure/function declaration (nested ones)
    nested_proc = re.compile(
        r'^\s+(procedure|function)\s+\w+',
        re.IGNORECASE
    )
    
    # Pattern for end matching this procedure
    end_pattern = re.compile(
        r'^\s*end\s+' + re.escape(proc_name) + r'\s*;',
        re.IGNORECASE
    )
    
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        
        # Check for nested procedure/function start
        if nested_proc.match(line):
            nesting += 1
            continue
        
        # Check for end matching this procedure
        if end_pattern.match(line):
            if nesting == 0:
                return i
            nesting -= 1
    
    return None


def find_begin_line(lines, start_line, end_line):
    """Find the 'begin' line between start_line and end_line."""
    for i in range(start_line + 1, end_line):
        stripped = lines[i].strip().lower()
        # Match 'begin' at start of line (after whitespace), possibly followed by '--' comment
        if stripped == 'begin' or stripped.startswith('begin ') or stripped.startswith('begin--'):
            return i
    return None


def has_exception_handler(lines, begin_line, end_line):
    """Check if there's an exception handler between begin and end."""
    for i in range(begin_line + 1, end_line):
        if lines[i].strip().lower().startswith('exception'):
            return True
    return False


def add_exception_handlers(filepath):
    """Add exception handlers to all procedures/functions missing them."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Pattern for top-level procedure/function start (in package body, indent <= 4)
    proc_start = re.compile(
        r'^(\s{0,4})(procedure|function)\s+(\w+)\s*(?:\([^)]*\))?\s*(?:return\s+\w+\s+)?is\b',
        re.IGNORECASE
    )
    
    # Find all top-level procedure/function starts
    procs = []
    for i, line in enumerate(lines):
        m = proc_start.match(line)
        if m:
            name = m.group(3)
            is_func = m.group(2).lower() == 'function'
            indent = len(m.group(1))
            procs.append({
                'name': name,
                'is_function': is_func,
                'start_line': i,
                'indent': indent
            })
    
    # For each procedure, find its end and check for exception handler
    to_fix = []
    for proc in procs:
        end_line = find_procedure_end(lines, proc['start_line'], proc['name'])
        if end_line is None:
            continue
        
        begin_line = find_begin_line(lines, proc['start_line'], end_line)
        if begin_line is None:
            continue
        
        if has_exception_handler(lines, begin_line, end_line):
            continue
        
        proc['end_line'] = end_line
        proc['begin_line'] = begin_line
        to_fix.append(proc)
    
    if not to_fix:
        return 0
    
    # Sort by end_line in reverse so we can insert without offset issues
    to_fix.sort(key=lambda p: p['end_line'], reverse=True)
    
    added = 0
    for proc in to_fix:
        name = proc['name']
        end_line = proc['end_line']
        is_func = proc['is_function']
        indent = proc['indent']
        
        # Build exception block
        indent_str = ' ' * indent
        inner_indent = ' ' * (indent + 3)
        
        if is_func:
            handler = (
                f"{indent_str}exception\n"
                f"{inner_indent}when E : others =>\n"
                f"{inner_indent}   Ada.Text_IO.Put_Line(\"[SAFE_FALLBACK] Exception in {name}: \" & Ada.Exceptions.Exception_Message(E));\n"
                f"{inner_indent}   raise;\n"
            )
        else:
            handler = (
                f"{indent_str}exception\n"
                f"{inner_indent}when E : others =>\n"
                f"{inner_indent}   Ada.Text_IO.Put_Line(\"[SAFE_FALLBACK] Exception in {name}: \" & Ada.Exceptions.Exception_Message(E));\n"
            )
        
        # Insert before the end line
        lines.insert(end_line, handler)
        added += 1
        print(f"  Added handler to: {'function' if is_func else 'procedure'} {name} (line {end_line+1})")
    
    # Write back
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    
    return added


def ensure_with_clauses(filepath):
    """Ensure Ada.Text_IO and Ada.Exceptions are imported."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    changes = 0
    lines = content.split('\n')
    
    # Find the last 'with' clause line, or the 'package body' line if no with clauses
    last_with = -1
    package_body_line = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('with ') and stripped.endswith(';'):
            last_with = i
        if stripped.lower().startswith('package body '):
            package_body_line = i
    
    # Insert point: after last with clause, or before package body if no with clauses
    insert_after = last_with if last_with >= 0 else package_body_line - 1
    
    # Check for Ada.Text_IO
    if 'with Ada.Text_IO' not in content:
        if insert_after >= 0:
            lines.insert(insert_after + 1, 'with Ada.Text_IO;')
            insert_after += 1  # Adjust for next insert
            content = '\n'.join(lines)
            changes += 1
            print("  Added: with Ada.Text_IO;")
    
    # Check for Ada.Exceptions (re-find lines since we modified)
    if 'with Ada.Exceptions' not in content:
        lines = content.split('\n')
        # Re-find insert point
        last_with = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('with ') and stripped.endswith(';'):
                last_with = i
        
        if last_with >= 0:
            lines.insert(last_with + 1, 'with Ada.Exceptions;')
            content = '\n'.join(lines)
            changes += 1
            print("  Added: with Ada.Exceptions;")
    
    if changes > 0:
        with open(filepath, 'w') as f:
            f.write(content)
    
    return changes


def main():
    base_dir = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/simulation_engine"
    
    files = [
        "stellarorion_orion.adb",
        "stellarorion_runtime_guard.adb",
        "stellarorion_sparta.adb",
        "stellarorion_dual_watchdog.adb",
        "main.adb",
        "stellarorion_status_writer.adb",
        "stellarorion_test_modes.adb",
        "stellarorion_history.adb",
        "stellarorion_project.adb",
        "stellarorion_self_test.adb",
        "stellarorion_cli.adb",
        "stellarorion_physics.adb",
        "stellarorion_validation.adb",
        "stellarorion_atomic_parity.adb",
        "stellarorion_types.adb",
        "stellarorion_environment.adb",
        "stellarorion_optimization.adb",
        "stellarorion_geometry.adb",
        "stellarorion_reports.adb",
        "stellarorion_optimize.adb",
    ]
    
    total_added = 0
    file_counts = {}
    
    for fname in files:
        filepath = os.path.join(base_dir, fname)
        
        if not os.path.exists(filepath):
            print(f"\nWARNING: File not found: {fname}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing: {fname}")
        print(f"{'='*60}")
        
        ensure_with_clauses(filepath)
        count = add_exception_handlers(filepath)
        file_counts[fname] = count
        total_added += count
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    for fname, count in file_counts.items():
        print(f"  {fname}: {count} handlers added")
    print(f"  TOTAL: {total_added} handlers added")


if __name__ == '__main__':
    main()
