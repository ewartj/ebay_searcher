#!/usr/bin/env bash
# Warhammer Scout AI code review
# Usage:
#   ./review.sh                        # review all staged changes
#   ./review.sh --commit <sha>         # review a specific commit
#   ./review.sh --branch <branch>      # review branch diff against main
#   ./review.sh --block-on-issues      # exit 1 if any BLOCK found (used by pre-commit hook)

set -uo pipefail

CLAUDE=$(find ~/.vscode/extensions -name "claude" -path "*/native-binary/claude" -type f 2>/dev/null | sort -V | tail -1)

if [ -z "$CLAUDE" ]; then
  echo "Claude Code binary not found. Is the Claude Code VS Code extension installed?"
  exit 0  # Degrade gracefully — don't block commits if Claude isn't available
fi

# --- Parse arguments ---
MODE="staged"
TARGET=""
BLOCK_ON_ISSUES=0

while [[ $# -gt 0 ]]; do
  case $1 in
    --commit)          MODE="commit"; TARGET="$2"; shift 2 ;;
    --branch)          MODE="branch"; TARGET="$2"; shift 2 ;;
    --block-on-issues) BLOCK_ON_ISSUES=1; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# --- Build content to review ---
case $MODE in
  staged)
    CONTENT=$(git diff --cached)
    LABEL="staged changes"
    if [ -z "$CONTENT" ]; then
      exit 0
    fi
    ;;
  commit)
    CONTENT=$(git show "$TARGET")
    LABEL="commit $TARGET"
    ;;
  branch)
    CONTENT=$(git diff "main...$TARGET")
    LABEL="branch $TARGET vs main"
    ;;
esac

echo ""
echo "Warhammer Scout AI Code Review — $LABEL"
echo "============================================================"
echo ""
echo "Running 3 agents in parallel..."
echo ""

TMP_SECURITY=$(mktemp)
TMP_CORRECTNESS=$(mktemp)
TMP_QUALITY=$(mktemp)
cleanup() { rm -f "$TMP_SECURITY" "$TMP_CORRECTNESS" "$TMP_QUALITY"; }
trap cleanup EXIT

run_agent() {
  local outfile="$1"
  local name="$2"
  local focus="$3"

  "$CLAUDE" -p \
    "You are a code reviewer for Warhammer Scout, a Python script that scrapes eBay and Vinted for Black Library books and flags bargains via Telegram.
Review the following diff for: $focus.
If you find a BLOCK-level issue (must fix before shipping) start that line with 'BLOCK:'.
If minor or advisory start with 'WARN:'. If clean start with 'OK:'.
Be concise — under 8 lines total.

$LABEL:
$CONTENT" \
    --allowedTools "" \
    --max-turns 3 \
    2>/dev/null | sed "s/^/[$name] /" | tee "$outfile"
}

run_agent "$TMP_SECURITY" "SECURITY" \
  "hardcoded API keys or tokens, credentials leaking into log output, .env values embedded in code, unsafe use of user-supplied data in shell or SQL" &
PID1=$!

run_agent "$TMP_CORRECTNESS" "CORRECTNESS" \
  "pricing logic bugs (wrong threshold direction, division by zero, off-by-one in price guide lookups), regex patterns that could false-positive or miss obvious cases, Claude response parsing that could crash on unexpected output" &
PID2=$!

run_agent "$TMP_QUALITY" "QUALITY" \
  "bare except clauses swallowing real errors, HTTP errors silently ignored, missing None checks before float conversion, test coverage gaps for changed logic" &
PID3=$!

wait $PID1; wait $PID2; wait $PID3

echo ""
echo "============================================================"

if [ "$BLOCK_ON_ISSUES" -eq 1 ]; then
  if grep -q "^\[.*\] BLOCK:" "$TMP_SECURITY" "$TMP_CORRECTNESS" "$TMP_QUALITY" 2>/dev/null; then
    echo "Commit BLOCKED by Claude review. Fix the issues above and try again."
    echo "To skip (not recommended): git commit --no-verify"
    exit 1
  else
    echo "Claude review passed. Proceeding with commit."
    exit 0
  fi
fi

echo "Review complete."
