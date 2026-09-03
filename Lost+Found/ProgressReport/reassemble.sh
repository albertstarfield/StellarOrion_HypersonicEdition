#!/bin/bash
# Reassemble split tar.zst files back into original archives.
# Usage: cd Lost+Found/ProgressReport && bash reassemble.sh
#
# Files split with: split -b 25m <file>.tar.zst <file>.tar.zst.part_
# Reassembled with: cat <file>.tar.zst.part_* > <file>.tar.zst
#
# After reassembly, verify with: sha256sum <file>.tar.zst (if checksums available)

set -euo pipefail

SPLIT_FILES=(
  "Week 6.tar.zst"
  "Week 7.tar.zst"
  "Week 8.tar.zst"
  "Week 9.tar.zst"
  "Week 10.tar.zst"
  "Week 11.tar.zst"
  "Iter2Latex.tar.zst"
)

echo "=== Reassembling split tar.zst files ==="

for base in "${SPLIT_FILES[@]}"; do
  parts=(${base}.tar.zst.part_*)
  
  # Check if any parts exist
  if [[ ! -e "${parts[0]}" ]]; then
    echo "SKIP: No parts found for $base"
    continue
  fi
  
  echo "Reassembling: $base (${#parts[@]} parts)"
  cat "${parts[@]}" > "$base"
  echo "  -> $base ($(du -h "$base" | cut -f1))"
  
  # Optionally remove parts after reassembly
  # rm "${parts[@]}"
done

echo ""
echo "=== Done ==="
echo "Reassembled files:"
ls -lh *.tar.zst
