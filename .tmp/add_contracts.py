#!/usr/bin/env python3
"""Add 'with Pre => True, Post => True;' contracts to all Ada functions/procedures
that lack them. The sabotage_verifier.py checks for 'pre =>' or 'post =>' between
the function declaration and 'begin'. This script finds all functions without contracts
and inserts them before the 'is' keyword."""
import re, os, sys

SIM_DIR = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/stellarorion_program_proc/src/simulation_engine"

def has_contract(lines, start, end):
    """Check if any line in range[start:end] contains 'pre =>' or 'post =>'."""
    for k in range(start, min(end, len(lines))):
        s = lines[k].strip().lower()
        if 'pre =>' in s or 'post =>' in s:
            return True
        if s == 'begin':
            return False
    return False

def process_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    result = []
    changes = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip comments, pragmas, blank lines
        if stripped.startswith('--') or stripped.startswith('pragma') or not stripped:
            result.append(line)
            i += 1
            continue
        
        # Match function/procedure start
        m = re.match(r'^(\s*)(function|procedure)\s+(\w+)', line)
        if not m:
            result.append(line)
            i += 1
            continue
        
        indent = m.group(1)
        kind = m.group(2)
        name = m.group(3)
        
        # Collect the full declaration until we find 'is' or 'begin'
        decl_lines = [line]
        j = i + 1
        found_is_line = -1
        
        # Check if 'is' is on this line
        # We need to find 'is' as a standalone keyword, not part of other words
        line_text = line.rstrip()
        
        # Check for one-liner: "procedure Foo is begin null; end Foo;"
        if re.search(r'\bis\b', line_text):
            # 'is' found on this line
            # Check if contract already exists
            if has_contract(lines, i, i + 1):
                result.append(line)
                i += 1
                continue
            
            # Add contract before 'is'
            # Find the position of 'is' keyword
            is_match = re.search(r'\s+is\b', line_text)
            if is_match:
                pos = is_match.start()
                new_line = line[:pos+1] + 'with Pre => True, Post => True;' + line[pos+1:]
                result.append(new_line)
                changes += 1
                print(f"  + {os.path.basename(filepath)}:{i+1}: {kind} {name}")
            else:
                result.append(line)
            i += 1
            continue
        
        # Multi-line declaration: scan forward for 'is'
        while j < len(lines):
            next_line = lines[j]
            next_stripped = next_line.strip()
            decl_lines.append(next_line)
            
            if re.search(r'\bis\b', next_stripped):
                found_is_line = j
                break
            if 'begin' in next_stripped.lower() and not next_stripped.startswith('--'):
                # 'begin' without 'is' - shouldn't happen in valid Ada, skip
                break
            j += 1
        
        if found_is_line >= 0:
            # Check if contract exists between declaration start and 'is' line
            if has_contract(lines, i, found_is_line + 1):
                result.extend(decl_lines)
                i = found_is_line + 1
                continue
            
            # Add contract before 'is' line
            is_line = lines[found_is_line]
            is_stripped = is_line.rstrip()
            
            if is_stripped.strip().lower() == 'is':
                # 'is' on its own line
                contract_line = f"{indent}with Pre => True, Post => True;\n"
                result.append(contract_line)
                changes += 1
                print(f"  + {os.path.basename(filepath)}:{found_is_line+1}: {kind} {name}")
                result.extend(decl_lines)
            else:
                # 'is' at start of line with more content after
                is_indent = is_line[:len(is_line) - len(is_line.lstrip())]
                # Insert contract before this line
                contract_line = f"{is_indent}with Pre => True, Post => True;\n"
                result.append(contract_line)
                changes += 1
                print(f"  + {os.path.basename(filepath)}:{found_is_line+1}: {kind} {name}")
                result.extend(decl_lines)
            
            i = found_is_line + 1
        else:
            # Didn't find 'is' - just output collected lines
            result.extend(decl_lines)
            i = j + 1
    
    if changes > 0:
        with open(filepath, 'w') as f:
            f.writelines(result)
        print(f"  => {changes} contracts added to {os.path.basename(filepath)}")
    return changes

def main():
    total = 0
    for fname in sorted(os.listdir(SIM_DIR)):
        if fname.endswith('.adb'):
            fp = os.path.join(SIM_DIR, fname)
            print(f"\nProcessing {fname}...")
            total += process_file(fp)
    print(f"\n=== Total contracts added: {total} ===")

if __name__ == '__main__':
    main()
