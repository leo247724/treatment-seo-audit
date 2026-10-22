#!/usr/bin/env bash
# Runs audit.py for every site in schedule/sites.txt, snapshots each result
# into out/<host>/history/<YYYY-MM-DD>/ and diffs it against the previous run.
#
# Env:
#   AUDIT_EXTRA_ARGS  extra audit.py flags, e.g. "--skip openseo" (spends no
#                     DataForSEO credits) or "--psi-pages 2"
#   AUDIT_PSI=1       drop the default --no-psi so PageSpeed Insights runs
#   AUDIT_TIMEOUT     per-site timeout in seconds (default 1800)
#   SITES_FILE        alternative sites file (default schedule/sites.txt)
#   PYTHON            interpreter (default .venv/bin/python)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-.venv/bin/python}"
SITES_FILE="${SITES_FILE:-schedule/sites.txt}"
LOG_DIR="schedule/logs"
SUMMARY_LOG="$LOG_DIR/summary.log"
LOCK_DIR="$LOG_DIR/.run_sites.lock"
AUDIT_TIMEOUT="${AUDIT_TIMEOUT:-1800}"
mkdir -p "$LOG_DIR"

# Lock: mkdir is atomic on macOS and Linux (no flock on macOS). A lock left by
# a dead process is taken over; a live one makes this run skip.
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  old_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "$(date '+%F %T') another run (pid $old_pid) is still going, skipping" | tee -a "$SUMMARY_LOG"
    exit 0
  fi
  rm -rf "$LOCK_DIR"
  mkdir "$LOCK_DIR"
fi
echo $$ > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT

TIMEOUT_CMD=()
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD=(timeout "$AUDIT_TIMEOUT")
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD=(gtimeout "$AUDIT_TIMEOUT")
fi

EXTRA=()
if [ -n "${AUDIT_EXTRA_ARGS:-}" ]; then
  read -r -a EXTRA <<< "$AUDIT_EXTRA_ARGS"
fi
PSI_FLAG=(--no-psi)
if [ "${AUDIT_PSI:-0}" = "1" ]; then
  PSI_FLAG=()
fi

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

host_of() {
  local h="${1#*://}"
  h="${h%%/*}"; h="${h%%:*}"
  h="$(printf '%s' "$h" | tr '[:upper:]' '[:lower:]')"
  printf '%s' "${h#www.}"
}

snapshot() {
  # Copy out/<host>/ into out/<host>/history/<date>/, minus crawl.pkl,
  # the openseo/ cache and history/ itself.
  local src="$1" dest="$2"
  mkdir -p "$dest"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude 'crawl.pkl' --exclude 'openseo/' --exclude 'history/' "$src/" "$dest/"
  else
    local entry name
    for entry in "$src"/* "$src"/.[!.]*; do
      [ -e "$entry" ] || continue
      name="$(basename "$entry")"
      case "$name" in crawl.pkl|openseo|history) continue ;; esac
      cp -R "$entry" "$dest/"
    done
  fi
}

echo "$(date '+%F %T') run started" >> "$SUMMARY_LOG"
n_ok=0; n_fail=0

while IFS= read -r raw <&3 || [ -n "$raw" ]; do
  line="$(trim "$raw")"
  case "$line" in ''|'#'*) continue ;; esac
  IFS='|' read -r url brand city <<< "$line"
  url="$(trim "${url:-}")"; brand="$(trim "${brand:-}")"; city="$(trim "${city:-}")"
  [ -n "$url" ] || continue

  host="$(host_of "$url")"
  stamp="$(date '+%Y%m%d-%H%M')"
  log="$LOG_DIR/$host-$stamp.log"
  echo "$(date '+%F %T') auditing $url -> $log"

  rc=0
  {
    echo "== $(date '+%F %T') $url brand='$brand' city='$city'"
    ${TIMEOUT_CMD[@]+"${TIMEOUT_CMD[@]}"} "$PYTHON" audit.py "$url" --brand "$brand" --city "$city" \
      ${PSI_FLAG[@]+"${PSI_FLAG[@]}"} ${EXTRA[@]+"${EXTRA[@]}"} </dev/null
  } > "$log" 2>&1 || rc=$?

  if [ "$rc" -ne 0 ]; then
    n_fail=$((n_fail + 1))
    [ "$rc" -eq 124 ] && why="timed out after ${AUDIT_TIMEOUT}s" || why="exit $rc"
    echo "$(date '+%F %T') $host: audit failed ($why), see $log" >> "$SUMMARY_LOG"
    continue
  fi

  out_dir="out/$host"
  if [ ! -f "$out_dir/findings.json" ]; then
    n_fail=$((n_fail + 1))
    echo "$(date '+%F %T') $host: no $out_dir/findings.json after run, see $log" >> "$SUMMARY_LOG"
    continue
  fi

  if ! snapshot "$out_dir" "$out_dir/history/$(date '+%F')" >> "$log" 2>&1; then
    echo "$(date '+%F %T') $host: snapshot copy failed, see $log" >> "$SUMMARY_LOG"
  fi

  summary="$("$PYTHON" diff_runs.py "$host" 2>>"$log" | tee -a "$log" | tail -n 1 || true)"
  echo "$(date '+%F %T') ${summary:-$host: diff produced no output}" >> "$SUMMARY_LOG"
  n_ok=$((n_ok + 1))
done 3< "$SITES_FILE"

echo "$(date '+%F %T') run finished: $n_ok ok, $n_fail failed" >> "$SUMMARY_LOG"
exit 0
