#!/usr/bin/env bash
# =====================================================================
# StellarOrion STAGE-1 CALIBRATION DoE RUNNER (DSMC+PINN_AUX).
#
# PURPOSE
#     Fly the 9-point local Central Composite Design of
#     CALIBRATION_DESIGN.md Sec 2.7 through the SPARTA DSMC solver so that
#     the ANALYTIC screening model can be refitted against DSMC responses
#     (Sec 2.6 / Sec 2.6.1: the orthogonal residual correction).
#
#     The design is sampled in MODEL SPACE (the analytic vector
#     X = (R_N, r_tor, half_cone_deg)) and EVALUATED in PHYSICAL SPACE (the
#     Geometry_Parameters that SPARTA actually flies).  The two spaces are
#     connected by the single convention of Sec 2.1:
#
#         Diameter_M      := 2 * X(1)
#         Nose_Radius_M   := (0.55 / 1.5) * X(1)
#         Toroid_Radius_M := X(2)
#         Angle_Deg       := X(3)
#
#     WHY this mapping: the analytic model's X(1) is the body/CONE JUNCTION
#     radius while SPARTA flies a body of Diameter_M with a SEPARATE nose
#     bluntness radius.  With the ratio 0.55/1.5 the REFERENCE anchor
#     X = (1.5, 0.135, 60) maps byte-identically to the flown reference
#     (D = 3.0 m, nose = 0.55 m, torus = 0.135 m, cone = 60 deg), so the
#     reference run does NOT have to be repeated.
#
# AXIOMS
#     A1  The design is the 8 corners of a 2^3 factorial in CODED
#         coordinates (+-1) plus the CENTRE point: 9 DSMC runs.
#     A2  The coded coordinates are mapped to MODEL space as
#         X_k = centre_k + code_k * half_k with the centre and half-widths
#         of Sec 2.7 (X* = (1.03967, 0.219741, 53.7247),
#         half = (0.25, 0.06, 8.0)).  The Sec 2.7 centre is the BINDING
#         default; --centre overrides it, and the live GA optimum is
#         cross-checked against it (a WARNING, never a silent move).
#     A3  MODEL space is mapped to PHYSICAL space by the Sec 2.1 convention
#         above and by nothing else.
#     A4  Every point is flown with the SAME protocol as the reference run
#         (--skin scalloped, --steps 2200) so the responses are comparable.
#     A5  A point whose validation_timeseries.csv already holds the EXPECTED
#         number of rows (STEPS / DUMP_STATS_INTERVAL) is SKIPPED: the run
#         is idempotent and resumable, and every skip is logged.
#     A6  A point whose run fails is recorded as FAILED in the manifest and
#         does NOT abort the campaign; the campaign's exit status is the
#         number of failed points.
#     A7  The binary MUST have been built with MACOSX_DEPLOYMENT_TARGET=26.0
#         (the GNAT 16.1.0 toolchain default is minos 28.0, which is not
#         loadable on this macOS host).
#     A8  The DOCKER DAEMON MUST be reachable (`docker ps` exits 0) before
#         any work is done: the DSMC leg runs SPARTA in a container
#         (`docker run --rm --name hiad-runner ...`).
#     A9  The CODED SIGN CONVENTION of this script is IDENTICAL to the one
#         proved in proofs/lean/StellarOrionProofs/Design.lean
#         (designPoint) and proofs/coq/Calibration.v (xsign):
#             point id 1..8  ->  design index 0..7  ->  (+1,+1,+1),
#             (+1,+1,-1), (+1,-1,+1), (+1,-1,-1), (-1,+1,+1), (-1,+1,-1),
#             (-1,-1,+1), (-1,-1,-1)
#             point id 9     ->  design index 8     ->  ( 0, 0, 0)  (centre)
#         The manifest records the codes of every point, so the Stage-2 fit
#         must read the codes from the manifest (or apply this same
#         convention) -- never from the point id order alone.
#
# THEORIES
#     T1  (McKay et al. 1979, Technometrics 21(2)) The 2^3 factorial layout
#         is orthogonal, so the seven contrasts of the fitted residual are
#         decoupled from the mean and the fit is the exact least-squares
#         solution on the model span.
#     T2  (Kennedy & O'Hagan 2000, Biometrika 87(1)) A model-fidelity
#         correction fitted on an orthogonal basis is exact for responses in
#         the model span and vanishes identically when the model is right.
#
# APPLICATIONS
#     scripts/run_calibration_dsmc.sh --dry-run          # print the plan
#     scripts/run_calibration_dsmc.sh                    # fly what is missing
#     scripts/run_calibration_dsmc.sh --only 1,2,5       # a subset
#     scripts/run_calibration_dsmc.sh --force             # re-fly everything
#     scripts/run_calibration_dsmc.sh --rebuild           # rebuild bin/main first
#     scripts/run_calibration_dsmc.sh --centre R_N,r_tor,cone   # recentre
#
#     The manifest (results/calibration/manifest.csv) is the campaign's
#     index; the per-point time series land in
#     results/calibration/ccd_<point_id>/validation_timeseries.csv.
#
# CITATIONS
#     - McKay, D. et al. (1979), Technometrics 21(2), 239-248.
#     - Montgomery, D.C. (2017), "Design and Analysis of Experiments", 9th ed.
#     - Kennedy, M.C. & O'Hagan, A. (2000), Biometrika 87(1), 65-82.
#     - Rapisarda, A. et al. (2023), RAPISARDA F-TPS design of experiments.
#     - [Citation: stellarorion_sparta.ads:31 - DUMP_STATS_INTERVAL = 100,
#       the single source of truth for the CSV dump cadence.]
#     - [Citation: stellarorion_sparta.adb:3907 - the surf dump filter
#       `Step >= 100 and Step mod 100 = 0 and Step <= Steps`, which fixes the
#       number of CSV rows per run at floor(STEPS / 100).]
#
# ==== END HEADER ====
# =====================================================================

set -euo pipefail

# ---------------------------------------------------------------------
# 0.  Configuration
# ---------------------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BIN_REL="bin/main"
BIN="${ROOT}/${BIN_REL}"

# Sec 2.7: the local CCD around the GA optimum (model space).  These are the
# BINDING values of CALIBRATION_DESIGN.md Sec 2.7 (and Sec 2.1), so the plan
# is reproducible from this script alone and cannot silently drift.  An
# explicit --centre overrides them; the live optimiser artefact is then
# cross-checked against the contract centre, and a WARNING is printed when
# the current optimum has left the Sec 2.7 screen (Sec 2.7's own rationale:
# "the CCD must cover the region the GA actually explored").  The script
# NEVER recentres on its own -- the contract centre is the default.
CENTRE_X1=1.03967      # X(1): body / cone-junction radius [m]
CENTRE_X2=0.219741     # X(2): toroid radius [m]
CENTRE_X3=53.7247      # X(3): half-cone angle [deg]
CENTRE_OVERRIDE=0      # 1 when --centre was given on the command line
HALF_X1=0.25           # dR_N
HALF_X2=0.06           # dR_tor
HALF_X3=8.0            # dCone
# The live optimiser artefact: used ONLY as a cross-check, never as the
# default (the contract centre is the default and the artefact is optional).
RESULTS_JSON_REL="src/python/hiad_optimization_results.json"

# Sec 2.1: Nose_Radius_Ratio := 0.55 / 1.5 -- kept as the RATIO, never as a
# rounded literal, so the script implements the specification literally.
NOSE_NUM=0.55
NOSE_DEN=1.5

STEPS=2200
SKIN=scalloped
DUMP_INTERVAL=100      # DUMP_STATS_INTERVAL (stellarorion_sparta.ads:31)

OUT_REL="results/calibration"
RUN_TIMEOUT_S=14400    # 4 h per DSMC run (the measured cost is ~2 h)
HEARTBEAT_S=30         # heartbeat cadence of the watchdog contract (A5/A6)

DRY_RUN=0
FORCE=0
REBUILD=0
ONLY=""
FAILED_POINTS=0
CHILD_PID=""
HB_PID=""
GPRBUILD_CMD=()

usage() {
  awk '/^# ==== END HEADER ====/ { exit } NR>1 { sub(/^# ?/, ""); print }' \
      "${BASH_SOURCE[0]}"
  cat <<'EOF'

Options:
  --dry-run          print the full plan (the exact CLI of every point) and exit
  --force            re-fly points that already have a complete time series
  --rebuild          rebuild bin/main (MACOSX_DEPLOYMENT_TARGET=26.0) first
  --steps N          DSMC steps per point (default 2200)
  --outdir DIR       campaign root, relative to the project root
                     (default results/calibration)
  --only "1,2,5"     fly only the listed point ids (1..9)
  --centre R_N,r_tor,cone
                     override the CCD centre (default: the Sec 2.7 binding
                     centre 1.03967,0.219741,53.7247)
  -h, --help         this text
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force)   FORCE=1; shift ;;
    --rebuild) REBUILD=1; shift ;;
    --steps)   STEPS="$2"; shift 2 ;;
    --outdir)  OUT_REL="$2"; shift 2 ;;
    --only)    ONLY="$2"; shift 2 ;;
    --centre)  CENTRE_OVERRIDE=1
               CENTRE_RAW="$(printf '%s' "$2" | tr -d '[:space:]')"
               IFS=',' read -r CENTRE_X1 CENTRE_X2 CENTRE_X3 <<< "${CENTRE_RAW}"
               shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "run_calibration_dsmc.sh: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "${STEPS}" in
  ''|*[!0-9]*) echo "FATAL: --steps must be a positive integer (got '${STEPS}')." >&2; exit 2 ;;
esac
[ "${STEPS}" -ge 1 ] || { echo "FATAL: --steps must be >= 1 (got '${STEPS}')." >&2; exit 2; }

# ---------------------------------------------------------------------
# 0b. The CCD centre: the Sec 2.7 binding value, cross-checked against
#     the live GA optimum.
# ---------------------------------------------------------------------
# Compare the contract centre with the live GA optimum and WARN (never
# fail) when the optimum has left the Sec 2.7 screen.  The optimiser
# artefact is OPTIONAL: a missing or unreadable artefact only silences
# this cross-check, it never blocks the campaign.
check_centre_against_optimum() {
  local opt_py opt_vals ox1 ox2 ox3 warn c
  [ -f "${RESULTS_JSON_REL}" ] || return 0
  opt_py=""
  for c in python3 python3.14 python; do
    if command -v "${c}" >/dev/null 2>&1; then opt_py="${c}"; break; fi
  done
  [ -n "${opt_py}" ] || return 0
  opt_vals="$("${opt_py}" - "${RESULTS_JSON_REL}" <<'PYEOF_READ' 2>/dev/null
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    opt = json.load(fh)["optimized"]
print(opt["R_N"], opt["r_tor"], opt["half_cone_deg"])
PYEOF_READ
  )" || return 0
  read -r ox1 ox2 ox3 <<< "${opt_vals}"
  case "${ox1}${ox2}${ox3}" in
    ''|*[!0-9.]*) return 0 ;;
  esac
  warn="$(awk -v cx1="${CENTRE_X1}" -v cx2="${CENTRE_X2}" -v cx3="${CENTRE_X3}" \
              -v ox1="${ox1}" -v ox2="${ox2}" -v ox3="${ox3}" \
              -v h1="${HALF_X1}" -v h2="${HALF_X2}" -v h3="${HALF_X3}" \
        'BEGIN {
           d1 = cx1 - ox1; if (d1 < 0) d1 = -d1
           d2 = cx2 - ox2; if (d2 < 0) d2 = -d2
           d3 = cx3 - ox3; if (d3 < 0) d3 = -d3
           out = ""
           if (d1 > h1) out = out sprintf("X1 off by %.6f m (half-width %.6f m); ", d1, h1)
           if (d2 > h2) out = out sprintf("X2 off by %.6f m (half-width %.6f m); ", d2, h2)
           if (d3 > h3) out = out sprintf("X3 off by %.6f deg (half-width %.6f deg); ", d3, h3)
           printf "%s", out
         }')"
  if [ -n "${warn}" ]; then
    echo "WARNING: the current GA optimum (${ox1}, ${ox2}, ${ox3}) lies OUTSIDE" >&2
    echo "         the CALIBRATION_DESIGN.md Sec 2.7 CCD screen centred on" >&2
    echo "         (${CENTRE_X1}, ${CENTRE_X2}, ${CENTRE_X3}): ${warn}" >&2
    echo "         The Sec 2.7 centre is used (it is the binding contract)." >&2
    echo "         Re-run with --centre ${ox1},${ox2},${ox3} to recentre the DoE." >&2
  fi
  return 0
}

if [ "${CENTRE_OVERRIDE}" -eq 1 ]; then
  for v in "${CENTRE_X1}" "${CENTRE_X2}" "${CENTRE_X3}"; do
    case "${v}" in
      ''|*[!0-9.]*) echo "FATAL: --centre needs three positive numbers (R_N,r_tor,cone)." >&2; exit 2 ;;
    esac
  done
else
  check_centre_against_optimum
fi

MANIFEST_REL="${OUT_REL}/manifest.csv"
STATE_REL="${OUT_REL}/.state"
EXPECTED_ROWS=$(( STEPS / DUMP_INTERVAL ))

# ---------------------------------------------------------------------
# 1.  The design (A1, A2, A9) and the physical geometry (A3)
# ---------------------------------------------------------------------
# The coded coordinates are IDENTICAL to proofs/lean .../Design.lean
# (designPoint) and proofs/coq/Calibration.v (xsign): the design index k
# (0-based) has b2 = k/4, b1 = (k/2) mod 2, b0 = k mod 2, and every coded
# coordinate is +1 iff its bit is 0.
design_points() {
  local k b2 b1 b0 c1 c2 c3
  for k in 0 1 2 3 4 5 6 7; do
    b2=$(( k / 4 ))
    b1=$(( (k / 2) % 2 ))
    b0=$(( k % 2 ))
    c1=$(( b2 == 0 ? 1 : -1 ))
    c2=$(( b1 == 0 ? 1 : -1 ))
    c3=$(( b0 == 0 ? 1 : -1 ))
    echo "$(( k + 1 )) ${c1} ${c2} ${c3}"
  done
  echo "9 0 0 0"
}

# ---------------------------------------------------------------------
# 2.  Pre-flight checks (A8 first: no work before the daemon is proven up)
# ---------------------------------------------------------------------
resolve_timeout() {
  if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_BIN="timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_BIN="gtimeout"
  else
    return 1
  fi
  return 0
}

resolve_gprbuild() {
  if command -v gprbuild >/dev/null 2>&1; then
    GPRBUILD_CMD=(gprbuild)
  elif [ -x "${HOME}/.local/bin/gprbuild" ]; then
    GPRBUILD_CMD=("${HOME}/.local/bin/gprbuild")
  elif command -v alr >/dev/null 2>&1; then
    GPRBUILD_CMD=(alr exec -- gprbuild)
  else
    return 1
  fi
  return 0
}

build_binary() {
  if ! resolve_gprbuild; then
    echo "FATAL: no gprbuild found (looked on PATH, in ${HOME}/.local/bin and via alr)." >&2
    echo "       Install the GNAT toolchain (Alire: 'alr toolchain --install gnat_native')," >&2
    echo "       then re-run with --rebuild." >&2
    return 3
  fi
  echo "== building ${BIN_REL} (MACOSX_DEPLOYMENT_TARGET=26.0, A7) =="
  MACOSX_DEPLOYMENT_TARGET=26.0 "${GPRBUILD_CMD[@]}" \
      -f -P stellarorion_program_proc.gpr -j0
}

preflight() {
  # A8: the docker daemon is checked FIRST -- it is the only external
  # service the campaign needs, and a dead daemon would waste a 4 h slot.
  if ! command -v docker >/dev/null 2>&1; then
    echo "FATAL: docker is not on PATH; the DSMC leg runs SPARTA in a container." >&2
    return 3
  fi
  if ! docker ps >/dev/null 2>&1; then
    echo "FATAL: the docker daemon is not reachable ('docker ps' failed)." >&2
    echo "       Start it first:  colima start --cpu 6 --memory 8 --disk 100" >&2
    echo "       (or: 'docker context use <context>' / launch Docker Desktop)." >&2
    return 3
  fi
  if ! resolve_timeout; then
    echo "FATAL: neither 'timeout' nor 'gtimeout' is on PATH; the 4 h per-run" >&2
    echo "       watchdog cannot be armed.  Install coreutils (brew install" >&2
    echo "       coreutils) or put gtimeout on PATH." >&2
    return 3
  fi
  if ! command -v awk >/dev/null 2>&1; then
    echo "FATAL: awk is not on PATH; the coded->physical map needs it." >&2
    return 3
  fi
  if [ "${REBUILD}" -eq 1 ] || [ ! -x "${BIN}" ]; then
    build_binary || return 3
  fi
  if [ ! -x "${BIN}" ]; then
    echo "FATAL: ${BIN_REL} not found or not executable." >&2
    echo "       Build it first:" >&2
    echo "       cd ${ROOT} && MACOSX_DEPLOYMENT_TARGET=26.0 \\" >&2
    echo "         gprbuild -f -P stellarorion_program_proc.gpr -j0" >&2
    return 3
  fi
  return 0
}

# ---------------------------------------------------------------------
# 3.  Helpers
# ---------------------------------------------------------------------
# The number of DATA rows of a validation_timeseries.csv (header excluded).
csv_data_rows() {
  [ -f "$1" ] || { echo 0; return 0; }
  awk 'NR>1 && NF>0 { c++ } END { print c+0 }' "$1" 2>/dev/null || echo 0
}

# The exact CLI of one point, as a single argv array.  The ORDER is the
# order of the calibration contract: nose, diameter, tradius, angle.
point_command() {
  local nose="$1" diameter="$2" torus="$3" angle="$4" results_dir="$5"
  CMD=("${BIN_REL}" --validate --headless \
       --nose "${nose}" --diameter "${diameter}" --tradius "${torus}" \
       --angle "${angle}" --skin "${SKIN}" --steps "${STEPS}" \
       --results-dir "${results_dir}")
}

print_command() {
  local first=1 a
  for a in "$@"; do
    if [ "${first}" -eq 1 ]; then first=0; else printf ' '; fi
    printf '%s' "${a}"
  done
  printf '\n'
}

# The manifest row of one point (CSV, one line).
manifest_row() {
  local id="$1" idx="$2" c1="$3" c2="$4" c3="$5" x1="$6" x2="$7" x3="$8" \
        dia="$9" nose="${10}" tor="${11}" ang="${12}" rdir="${13}" st="${14}"
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "${id}" "${idx}" "${c1}" "${c2}" "${c3}" "${x1}" "${x2}" "${x3}" \
    "${dia}" "${nose}" "${tor}" "${ang}" "${STEPS}" "${EXPECTED_ROWS}" \
    "${rdir}" "${st}"
}

MANIFEST_HEADER="point_id,design_index,code_x1,code_x2,code_x3,x1_body_radius_m,x2_toroid_radius_m,x3_half_cone_deg,diameter_m,nose_radius_m,toroid_radius_m,angle_deg,steps,expected_rows,results_dir,status"

# The manifest is REGENERATED from one state file per point, so the file is
# always a faithful index of the campaign, is idempotent across re-runs,
# and a point that is not visited in this run keeps its previous status.
write_manifest() {
  local mid
  {
    printf '%s\n' "${MANIFEST_HEADER}"
    for mid in 1 2 3 4 5 6 7 8 9; do
      if [ -f "${STATE_REL}/ccd_${mid}.row" ]; then
        cat "${STATE_REL}/ccd_${mid}.row"
      fi
    done
  } > "${MANIFEST_REL}.tmp" && mv "${MANIFEST_REL}.tmp" "${MANIFEST_REL}"
}

# ---------------------------------------------------------------------
# 4.  The watchdog contract: heartbeat + dead-man detection
# ---------------------------------------------------------------------
# While a point runs, a heartbeat file is refreshed every HEARTBEAT_S.  The
# file's MTIME is the dead-man signal: an external detector that finds it
# older than 3 * HEARTBEAT_S knows the worker is gone.
start_heartbeat() {
  local hb="$1" pid="$2" id="$3"
  (
    while kill -0 "${pid}" 2>/dev/null; do
      printf 'point=%s pid=%s utc=%s\n' "${id}" "${pid}" \
             "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${hb}"
      sleep "${HEARTBEAT_S}"
    done
  ) &
  HB_PID=$!
}

stop_heartbeat() {
  if [ -n "${HB_PID}" ]; then
    kill "${HB_PID}" 2>/dev/null || true
    wait "${HB_PID}" 2>/dev/null || true
    HB_PID=""
  fi
}

on_exit() {
  local rc=$?
  stop_heartbeat
  if [ -n "${CHILD_PID}" ] && kill -0 "${CHILD_PID}" 2>/dev/null; then
    kill -TERM "${CHILD_PID}" 2>/dev/null || true
    wait "${CHILD_PID}" 2>/dev/null || true
  fi
  CHILD_PID=""
  return "${rc}"
}
trap on_exit EXIT
trap 'echo "run_calibration_dsmc.sh: interrupted (SIGINT)." >&2; exit 130' INT
trap 'echo "run_calibration_dsmc.sh: terminated (SIGTERM)." >&2; exit 143' TERM

# ---------------------------------------------------------------------
# 5.  The campaign
# ---------------------------------------------------------------------
campaign() {
  local id c1 c2 c3 x1 x2 x3 diameter nose torus angle results_dir csv log hb
  local status rows rc idx

  if [ "${DRY_RUN}" -eq 1 ]; then
    echo "== StellarOrion Stage-1 calibration DoE (DRY RUN) =="
    echo "   root        : ${ROOT}"
    echo "   design      : 2^3 factorial + centre (9 points), MODEL space"
    echo "   centre      : X = (${CENTRE_X1}, ${CENTRE_X2}, ${CENTRE_X3})"
    echo "   half-widths : X = (${HALF_X1}, ${HALF_X2}, ${HALF_X3})"
    echo "   mapping     : D = 2*X1, nose = (${NOSE_NUM}/${NOSE_DEN})*X1,"
    echo "                 torus = X2, angle = X3            (Sec 2.1)"
    echo "   protocol    : --skin ${SKIN} --steps ${STEPS}"
    echo "   expected    : ${EXPECTED_ROWS} data rows per point"
    echo "   binary      : ${BIN_REL}"
    echo "   results     : ${OUT_REL}/ccd_<point_id>"
    echo "   manifest    : ${MANIFEST_REL}"
    echo ""
    echo "--- PLAN ---"
  else
    echo "== StellarOrion Stage-1 calibration DoE =="
    echo "   root        : ${ROOT}"
    echo "   design      : 2^3 factorial + centre (9 points), MODEL space"
    echo "   centre      : X = (${CENTRE_X1}, ${CENTRE_X2}, ${CENTRE_X3})"
    echo "   half-widths : X = (${HALF_X1}, ${HALF_X2}, ${HALF_X3})"
    echo "   protocol    : --skin ${SKIN} --steps ${STEPS}"
    echo "   expected    : ${EXPECTED_ROWS} data rows per point"
    echo "   manifest    : ${MANIFEST_REL}"
    echo ""
  fi

  while read -r id c1 c2 c3; do
    [ -z "${id}" ] && continue

    if [ -n "${ONLY}" ]; then
      case ",${ONLY}," in
        *",${id},"*) : ;;
        *) continue ;;
      esac
    fi

    idx=$(( id - 1 ))

    # A2: model space (the coded coordinate -> X map).
    x1=$(awk -v c="${CENTRE_X1}" -v h="${HALF_X1}" -v k="${c1}" \
              'BEGIN{printf "%.6f", c + k*h}')
    x2=$(awk -v c="${CENTRE_X2}" -v h="${HALF_X2}" -v k="${c2}" \
              'BEGIN{printf "%.6f", c + k*h}')
    x3=$(awk -v c="${CENTRE_X3}" -v h="${HALF_X3}" -v k="${c3}" \
              'BEGIN{printf "%.6f", c + k*h}')

    # A3: physical space (the Sec 2.1 convention, and nothing else).
    diameter=$(awk -v x="${x1}" 'BEGIN{printf "%.6f", 2.0*x}')
    nose=$(awk -v x="${x1}" -v n="${NOSE_NUM}" -v d="${NOSE_DEN}" \
               'BEGIN{printf "%.6f", (n/d)*x}')
    torus="${x2}"
    angle="${x3}"

    results_dir="${OUT_REL}/ccd_${id}"
    csv="${results_dir}/validation_timeseries.csv"
    log="${results_dir}/dsmc.log"
    hb="${results_dir}/heartbeat.txt"

    point_command "${nose}" "${diameter}" "${torus}" "${angle}" "${results_dir}"

    rows=$(csv_data_rows "${csv}")

    if [ "${DRY_RUN}" -eq 1 ]; then
      echo "[${id}] code=(${c1},${c2},${c3})  X=(${x1}, ${x2}, ${x3})  " \
           "D=${diameter} nose=${nose} tradius=${torus} angle=${angle}"
      print_command "${CMD[@]}"
      if [ "${rows}" -ge "${EXPECTED_ROWS}" ] && [ "${rows}" -gt 0 ]; then
        echo "      -> would be SKIPPED (${rows}/${EXPECTED_ROWS} rows already on disk)"
      else
        echo "      -> would be FLYED"
      fi
      continue
    fi

    if [ "${FORCE}" -eq 0 ] && [ "${rows}" -gt 0 ] \
       && [ "${rows}" -ge "${EXPECTED_ROWS}" ]; then
      status="SKIPPED"
      echo "[${id}] SKIP (already flown: ${rows}/${EXPECTED_ROWS} rows in ${csv})"
    else
      mkdir -p "${results_dir}"
      rm -f "${csv}"
      echo "[${id}] FLYING  D=${diameter} nose=${nose} tradius=${torus} angle=${angle}"
      print_command "${CMD[@]}"
      set +e
      "${TIMEOUT_BIN}" "${RUN_TIMEOUT_S}" "${CMD[@]}" > "${log}" 2>&1 &
      CHILD_PID=$!
      start_heartbeat "${hb}" "${CHILD_PID}" "${id}"
      wait "${CHILD_PID}"
      rc=$?
      CHILD_PID=""
      stop_heartbeat
      set -e
      rows=$(csv_data_rows "${csv}")
      if [ "${rc}" -eq 0 ] && [ "${rows}" -ge "${EXPECTED_ROWS}" ] \
         && [ "${rows}" -gt 0 ]; then
        status="OK"
        echo "[${id}] OK (${rows}/${EXPECTED_ROWS} rows in ${csv})"
      else
        status="FAILED"
        FAILED_POINTS=$(( FAILED_POINTS + 1 ))
        if [ "${rc}" -eq 124 ]; then
          echo "[${id}] FAILED rc=124 (TIMEOUT after ${RUN_TIMEOUT_S}s; see ${log})" >&2
          docker ps --filter "name=hiad-runner" --format \
            '       leftover container: {{.ID}} {{.Image}} {{.Status}}' >&2 || true
        else
          echo "[${id}] FAILED rc=${rc} (${rows}/${EXPECTED_ROWS} rows; see ${log})" >&2
        fi
      fi
    fi

    # The point's row is stored in its own state file and the manifest is
    # regenerated from the state files (idempotent, resumable).
    manifest_row "${id}" "${idx}" "${c1}" "${c2}" "${c3}" "${x1}" "${x2}" "${x3}" \
      "${diameter}" "${nose}" "${torus}" "${angle}" "${results_dir}" "${status}" \
      > "${STATE_REL}/ccd_${id}.row"
    write_manifest
  done < <(design_points)

  if [ "${DRY_RUN}" -eq 1 ]; then
    echo ""
    echo "--- PLANNED MANIFEST (CSV; written to ${MANIFEST_REL} by a real run) ---"
    printf '%s\n' "${MANIFEST_HEADER}"
    local mid mc1 mc2 mc3 mx1 mx2 mx3 mdia mnose mtor mang mrdir
    while read -r mid mc1 mc2 mc3; do
      [ -z "${mid}" ] && continue
      mx1=$(awk -v c="${CENTRE_X1}" -v h="${HALF_X1}" -v k="${mc1}" \
                'BEGIN{printf "%.6f", c + k*h}')
      mx2=$(awk -v c="${CENTRE_X2}" -v h="${HALF_X2}" -v k="${mc2}" \
                'BEGIN{printf "%.6f", c + k*h}')
      mx3=$(awk -v c="${CENTRE_X3}" -v h="${HALF_X3}" -v k="${mc3}" \
                'BEGIN{printf "%.6f", c + k*h}')
      mdia=$(awk -v x="${mx1}" 'BEGIN{printf "%.6f", 2.0*x}')
      mnose=$(awk -v x="${mx1}" -v n="${NOSE_NUM}" -v d="${NOSE_DEN}" \
                  'BEGIN{printf "%.6f", (n/d)*x}')
      mtor="${mx2}"
      mang="${mx3}"
      mrdir="${OUT_REL}/ccd_${mid}"
      manifest_row "${mid}" "$(( mid - 1 ))" "${mc1}" "${mc2}" "${mc3}" \
        "${mx1}" "${mx2}" "${mx3}" "${mdia}" "${mnose}" "${mtor}" "${mang}" \
        "${mrdir}" "PLANNED"
    done < <(design_points)
    return 0
  fi

  echo ""
  echo "== campaign complete: ${FAILED_POINTS} failed point(s); manifest ${MANIFEST_REL} =="
  return "${FAILED_POINTS}"
}

main() {
  preflight || exit 3
  if [ "${DRY_RUN}" -eq 0 ]; then
    mkdir -p "${OUT_REL}" "${STATE_REL}"
    write_manifest
  fi
  campaign
}

main "$@"
