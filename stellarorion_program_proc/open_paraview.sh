#!/bin/sh
# Open the StellarOrion validation ParaView collection.
# macOS : double-click (rename to .command) or run:  sh open_paraview.sh
# Linux : ensure `paraview` is on PATH.
# Requires a validation run first (--validate), which writes:
#   results_validation/paraview/validation.pvd
HERE="$(cd "$(dirname "$0")" && pwd)"
PVD="$HERE/results_validation/paraview/validation.pvd"
if [ ! -f "$PVD" ]; then
  echo "ParaView collection not found: $PVD"
  echo "Run a validation first (--validate) to generate it."
  exit 1
fi
case "$(uname)" in
  Darwin) open -a ParaView "$PVD" 2>/dev/null || open "$PVD" ;;
  Linux)  paraview "$PVD" 2>/dev/null || xdg-open "$PVD" ;;
  *)      echo "Unsupported OS; open manually: $PVD" ;;
esac
