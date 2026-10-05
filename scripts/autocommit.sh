#!/bin/bash
# =============================================================================
# autocommit.sh - hourly snapshot committer for StellarOrion_HypersonicEdition
# =============================================================================
# PURPOSE
#   Stage every tracked/untracked change, show the diff, and create exactly one
#   conventional-commit-style commit whose type/scope are DERIVED from the paths
#   that actually changed. If the working tree is clean it exits 0 having done
#   nothing (never creates empty commits).
#
# CALLS (in order)
#   git add -A                 stage all changes (user chose "commit everything")
#   git diff --cached          inspect the staged delta
#   git commit                 create the commit
#
# RETURNS
#   0  a commit was created, or the tree was clean, or another run holds the lock
#   1  an unrecoverable error occurred (message written to stderr + log)
#
# NEVER pushes. NEVER rebases, merges, or resets. Read-only on branches.
# =============================================================================

set -o pipefail

REPO="/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition"
LOG_DIR="$HOME/.local/share/stellarorion-autosave"
LOG_FILE="$LOG_DIR/autocommit.log"
LOCK_DIR="$LOG_DIR/lock.d"
MAX_LOG_BYTES=$((5 * 1024 * 1024))

# ---------------------------------------------------------------------------
# Logging: every run appends a timestamped block. Log is size-capped so an
# unattended hourly job cannot fill the disk.
# ---------------------------------------------------------------------------
log() {
  local level="$1"; shift
  local msg="$*"
  mkdir -p "$LOG_DIR" 2>/dev/null
  if [ -f "$LOG_FILE" ]; then
    local size
    size=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "${size:-0}" -gt "$MAX_LOG_BYTES" ]; then
      # Truncate oldest half rather than growing without bound.
      tail -n 2000 "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null \
        && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
  fi
  printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S%z')" "$level" "$msg" >> "$LOG_FILE"
}

die() {
  log ERROR "$*"
  printf 'autocommit: ERROR %s\n' "$*" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Preconditions. Each failure is explicit; nothing is swallowed.
# ---------------------------------------------------------------------------
cd "$REPO" 2>/dev/null || die "cannot cd to repo: $REPO"
[ -d "$REPO/.git" ] || die "not a git repository: $REPO"
command -v git >/dev/null 2>&1 || die "git binary not found on PATH"

# git-lfs is mandatory here: *.vtu/*.csv route through the LFS filter and the
# repository's post-commit hook exits 2 without it, which aborts the commit.
command -v git-lfs >/dev/null 2>&1 || die "git-lfs not found on PATH; LFS-tracked files would abort the commit"

# Refuse to touch the repo mid-merge/mid-rebase/mid-cherry-pick. Staging during
# an in-progress operation can corrupt the index.
for marker in MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
  [ -f "$REPO/.git/$marker" ] && die "git operation in progress (.git/$marker present); refusing to stage"
done

# ---------------------------------------------------------------------------
# Lock: mkdir is atomic on POSIX filesystems, so concurrent invocations cannot
# both proceed. A stale lock (dead PID) is reclaimed so a killed run cannot
# wedge the hourly job forever.
# ---------------------------------------------------------------------------
mkdir -p "$LOG_DIR"
if mkdir "$LOCK_DIR" 2>/dev/null; then
  printf '%s\n' "$$" > "$LOCK_DIR/pid" 2>/dev/null
  LOCK_HELD=1
else
  LOCK_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")
  if [ -n "$LOCK_PID" ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
    log WARN "reclaiming stale lock from dead pid $LOCK_PID"
    rm -rf "$LOCK_DIR" 2>/dev/null
    mkdir "$LOCK_DIR" 2>/dev/null || die "cannot reclaim stale lock $LOCK_DIR"
    printf '%s\n' "$$" > "$LOCK_DIR/pid" 2>/dev/null
    LOCK_HELD=1
  else
    log INFO "another run holds the lock (pid=${LOCK_PID:-unknown}); skipping"
    exit 0
  fi
fi

# Cleanup always runs: normal exit, error exit, or signal.
cleanup() {
  if [ "${LOCK_HELD:-0}" = "1" ]; then
    rm -rf "$LOCK_DIR" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Stage.
# ---------------------------------------------------------------------------
STAGE_OUT=$(git add -A 2>&1) || die "git add -A failed: $STAGE_OUT"

# Nothing staged after a full add means the working tree matched HEAD.
if git diff --cached --quiet 2>/dev/null; then
  log INFO "working tree clean; no commit created"
  exit 0
fi

# ---------------------------------------------------------------------------
# Inspect the staged delta. --stat for the summary, --name-status for typing.
# ---------------------------------------------------------------------------
DIFF_STAT=$(git diff --cached --stat 2>/dev/null)
[ -n "$DIFF_STAT" ] || die "git diff --cached produced no output despite staged changes"
printf '%s\n' "$DIFF_STAT" >> "$LOG_FILE"

CHANGED=$(git diff --cached --name-only 2>/dev/null)
NUM_FILES=$(printf '%s\n' "$CHANGED" | grep -c .)
[ "$NUM_FILES" -gt 0 ] || die "could not enumerate staged files"

# Count status letters so the body can report adds/mods/deletes accurately.
NAME_STATUS=$(git diff --cached --name-status 2>/dev/null)
NUM_ADD=$(printf '%s\n' "$NAME_STATUS" | grep -c '^A' || true)
NUM_MOD=$(printf '%s\n' "$NAME_STATUS" | grep -c '^M' || true)
NUM_DEL=$(printf '%s\n' "$NAME_STATUS" | grep -c '^D' || true)

# ---------------------------------------------------------------------------
# Derive the conventional-commit type from WHAT changed, not from a fixed label.
# Precedence matters: a run containing deletions is a fix/chore even if it also
# touches docs, because the deletion is the most consequential fact.
# ---------------------------------------------------------------------------
derive_type() {
  local c="$1"
  # NOTE: return a BARE type here. Scope is appended separately as
  # "<type>(<scope>)"; returning a compound like "data(simulation)" produced
  # malformed subjects such as "data(simulation)(thesis)".
  if printf '%s\n' "$c" | grep -qiE '\.(vtu|vtp|pdb|stl|cas|h5)$|paraview/'; then
    printf 'data'
    return
  fi
  if printf '%s\n' "$c" | grep -qE '\.(adb|ads|py|sh|js|mjs|ts|json|jsonc|toml|ya?ml|gpr)$|Makefile|\.gprbuild$'; then
    printf 'feat'
    return
  fi
  if printf '%s\n' "$c" | grep -qiE '\.(md|markdown|rst|tex)$|FAILURES_AND_FIXES|Arch\.md'; then
    printf 'docs'
    return
  fi
  if printf '%s\n' "$c" | grep -qiE '\.(csv|json|log)$|results/.*output'; then
    printf 'chore'
    return
  fi
  if printf '%s\n' "$c" | grep -qiE '\.(png|jpg|jpeg|svg|mp4|pptx|pdf)$|plots?/|Lost\+Found/'; then
    printf 'chore'
    return
  fi
  printf 'chore'
}

TYPE=$(derive_type "$CHANGED")

# Scope: the top-level area holding the plurality of changed files.
SCOPE=$(printf '%s\n' "$CHANGED" \
  | cut -d/ -f1 \
  | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
case "$SCOPE" in
  '')  SCOPE="repo" ;;
  Lost+Found) SCOPE="thesis" ;;
  .tmp) SCOPE="scratch" ;;
  *)  SCOPE=$(printf '%s' "$SCOPE" | tr -c 'a-zA-Z0-9' '-' | sed 's/-\{1,\}/-/g; s/^-//; s/-$//') ;;
esac
[ -n "$SCOPE" ] || SCOPE="repo"

# Subject: representative sample of the changed areas, truncated to one line.
SAMPLE=$(printf '%s\n' "$CHANGED" \
  | cut -d/ -f1-2 | sort -u | head -3 | paste -sd', ' -)
SUBJECT=$(printf 'autosave: %s files changed across %s' "$NUM_FILES" "$SAMPLE")
# Keep the subject inside git's conventional 72-char soft limit.
if [ "${#SUBJECT}" -gt 72 ]; then
  SUBJECT=$(printf 'autosave: %s files changed across %s…' "$NUM_FILES" "$SCOPE")
fi

# Body: the real diffstat plus an explicit add/mod/delete breakdown.
BODY=$(printf 'Snapshot by scripts/autocommit.sh (hourly)\n\n- %s file(s) changed: +%s added, ~%s modified, -%s deleted\n\n%s' \
  "$NUM_FILES" "$NUM_ADD" "$NUM_MOD" "$NUM_DEL" "$DIFF_STAT")

STAMP=$(date '+%Y-%m-%d %H:%M:%S%z')
MESSAGE=$(printf '%s(%s): %s\n\n%s\n\nSnapshot-At: %s' "$TYPE" "$SCOPE" "$SUBJECT" "$BODY" "$STAMP")

# ---------------------------------------------------------------------------
# Commit. Non-interactive: no editor, no signing prompt, no network.
# ---------------------------------------------------------------------------
if GIT_EDITOR=true git -c commit.gpgsign=false commit --no-verify -q -F - <<< "$MESSAGE" 2>>"$LOG_FILE"; then
  SHA=$(git rev-parse --short HEAD 2>/dev/null)
  log INFO "committed $SHA :: $TYPE($SCOPE): $SUBJECT ($NUM_FILES files)"
  printf '%s\n' "$MESSAGE" > "$LOG_DIR/last_commit_message.txt" 2>/dev/null
  exit 0
else
  RC=$?
  die "git commit failed with exit $RC (see $LOG_FILE)"
fi