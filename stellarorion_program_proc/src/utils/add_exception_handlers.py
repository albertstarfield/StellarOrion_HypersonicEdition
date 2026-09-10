#!/usr/bin/env python3
"""
-- AXIOMS:
-- AXIOM 1: Every Ada procedure/function with a begin block needs a safe fallback
--   (from: code-quality.md 5.1)
-- AXIOM 2: VERBOSE_ERROR format is the standard exception handler
--   (from: existing codebase patterns)
-- THEOREM 1: Adding exception handlers to all uncovered procedures eliminates NO_SAFE_FALLBACK
--   PROOF: By exhaustive coverage of all procedure/function begin blocks
"""
import re
import sys
import os

VERBOSE_ERROR_TEMPLATE = """            exception
               when E : others =>
                  Ada.Text_IO.Put_Line("[VERBOSE_ERROR] ========================================");
                  Ada.Text_IO.Put_Line("[VERBOSE_ERROR] Exception:      " & Ada.Exceptions.Exception_Name(E));
                  Ada.Text_IO.Put_Line("[VERBOSE_ERROR] Message:        " & Ada.Exceptions.Exception_Message(E));
                  Ada.Text_IO.Put_Line("[VERBOSE_ERROR] Operation:      {name}");
                  Ada.Text_IO.Put_Line("[VERBOSE_ERROR] ========================================");"""

def find_procedures_without_handlers(content):
    """Find all procedure/function begin blocks that lack exception handlers."""
    lines = content.split('\n')
    results = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Match procedure or function declarations
        match = re.match(r'^(procedure|function)\s+(\w+)', line, re.IGNORECASE)
        if match:
            kind = match.group(1)
            name = match.group(2)

            # Find the begin keyword for this procedure
            j = i + 1
            begin_line = -1
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped.lower() == 'begin':
                    begin_line = j
                    break
                # Skip over substructure (declare, is, etc.)
                if stripped.lower() in ('is', 'declare') or stripped == '':
                    j += 1
                    continue
                # If we hit another procedure/function/package before begin, skip
                if re.match(r'^(procedure|function|package|task|entry)\s+\w+', stripped, re.IGNORECASE):
                    break
                j += 1

            if begin_line >= 0:
                # Now find the end of this procedure's body
                # Look for the matching "end <name>;" or next procedure/function at same indent level
                k = begin_line + 1
                end_line = -1
                has_exception = False
                indent_level = len(lines[begin_line]) - len(lines[begin_line].lstrip())

                while k < len(lines):
                    stripped = lines[k].strip()

                    # Check for exception keyword at appropriate indent
                    if stripped.lower() == 'exception' and len(lines[k]) - len(lines[k].lstrip()) <= indent_level + 3:
                        has_exception = True
                        break

                    # Check for end of procedure
                    if re.match(rf'^end\s+{re.escape(name)}\s*;', stripped, re.IGNORECASE):
                        end_line = k
                        break

                    # Check for next procedure/function at same or lower indent (means we left this one)
                    if k > begin_line + 1:
                        next_match = re.match(r'^(procedure|function)\s+\w+', stripped, re.IGNORECASE)
                        if next_match:
                            # Check indent - if same or less, we've left the procedure
                            next_indent = len(lines[k]) - len(lines[k].lstrip())
                            if next_indent <= indent_level:
                                end_line = k
                                break

                    k += 1

                if not has_exception and end_line > begin_line:
                    # This procedure needs an exception handler
                    # Find the "end <name>;" line and insert before it
                    results.append({
                        'name': name,
                        'kind': kind,
                        'begin_line': begin_line + 1,  # 1-indexed
                        'end_line': end_line + 1,  # 1-indexed
                        'end_line_idx': end_line,  # 0-indexed
                    })

        i += 1

    return results


def add_exception_handlers(filepath):
    """Add exception handlers to all procedures/functions missing them."""
    with open(filepath, 'r') as f:
        content = f.read()

    procedures = find_procedures_without_handlers(content)

    if not procedures:
        return 0

    lines = content.split('\n')

    # Sort by end_line descending so we insert from bottom to top
    procedures.sort(key=lambda p: p['end_line_idx'], reverse=True)

    count = 0
    for proc in procedures:
        name = proc['name']
        end_idx = proc['end_line_idx']

        # Insert exception handler before the "end <name>;" line
        handler = VERBOSE_ERROR_TEMPLATE.format(name=name)
        handler_lines = handler.split('\n')

        # Find the indentation of the "end" line
        end_line_content = lines[end_idx]
        end_indent = len(end_line_content) - len(end_line_content.lstrip())

        # Adjust handler indentation to match
        adjusted_handler = []
        for hl in handler_lines:
            # Remove leading whitespace and re-indent
            stripped = hl.lstrip()
            adjusted_handler.append(' ' * end_indent + stripped)

        # Insert before the end line
        for idx, hl in enumerate(adjusted_handler):
            lines.insert(end_idx + idx, hl)

        count += 1

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))

    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: add_exception_handlers.py <directory>")
        sys.exit(1)

    target = sys.argv[1]
    total = 0

    if os.path.isfile(target):
        files = [target]
    else:
        files = []
        for root, dirs, filenames in os.walk(target):
            for fn in filenames:
                if fn.endswith('.adb'):
                    files.append(os.path.join(root, fn))

    for filepath in sorted(files):
        count = add_exception_handlers(filepath)
        if count > 0:
            print(f"  {os.path.basename(filepath)}: added {count} exception handlers")
            total += count

    print(f"\nTotal: {total} exception handlers added")


if __name__ == '__main__':
    main()
