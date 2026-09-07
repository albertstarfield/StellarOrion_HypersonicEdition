#!/usr/bin/env python3
"""Check which procedures in target files still lack exception handlers."""

import re
import os

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

base_dir = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/simulation_engine"

for fname in files:
    filepath = os.path.join(base_dir, fname)
    if not os.path.exists(filepath):
        continue
    
    with open(filepath) as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Find all end statements and check for exception handlers
    proc_pattern = re.compile(r'^(\s*)(procedure|function)\s+(\w+)', re.IGNORECASE)
    end_pattern = re.compile(r'^(\s*)end\s+(\w+)\s*;', re.IGNORECASE)
    
    missing = []
    
    for i, line in enumerate(lines):
        end_match = end_pattern.match(line)
        if not end_match:
            continue
        
        name = end_match.group(2)
        indent = len(end_match.group(1))
        
        # Check if there's an exception handler before this end
        has_exception = False
        for j in range(i - 1, max(i - 200, -1), -1):
            check_line = lines[j].strip()
            if check_line.startswith('exception'):
                has_exception = True
                break
            if check_line.startswith('begin'):
                break
        
        if has_exception:
            continue
        
        # Find matching procedure/function declaration
        for j in range(i - 1, max(i - 500, -1), -1):
            proc_match = proc_pattern.match(lines[j])
            if proc_match and proc_match.group(3).lower() == name.lower():
                # Check if it's top-level (not deeply nested)
                proc_indent = len(lines[j]) - len(lines[j].lstrip())
                if proc_indent <= 4:  # Top-level in package body
                    is_func = proc_match.group(2).lower() == 'function'
                    missing.append(f"{'function' if is_func else 'procedure'} {name} (line {j+1})")
                break
    
    if missing:
        print(f"\n{fname} - MISSING HANDLERS ({len(missing)}):")
        for m in missing:
            print(f"  {m}")
    else:
        print(f"\n{fname} - ALL HANDLERS PRESENT")
