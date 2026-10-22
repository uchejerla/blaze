#!/usr/bin/env bash
# ═══════════════════════════════════════════════════
#  push.sh — Blaze repo update script
#  Usage:  ./push.sh "feat: add CSV support"
#          ./push.sh                    (prompts for message)
#          ./push.sh --dry-run          (show diff, don't push)
#          ./push.sh --tag v0.2.0       (tag + push)
# ═══════════════════════════════════════════════════

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

# ── Color helpers ────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
AMB='\033[0;33m'; CYN='\033[0;36m'; RST='\033[0m'
blaze() { echo -e "${AMB}🔥 Blaze${RST} $*"; }
ok()    { echo -e "${GRN}✅${RST} $*"; }
warn()  { echo -e "${YLW}⚠️  $*${RST}"; }
err()   { echo -e "${RED}❌ $*${RST}"; exit 1; }

# ── Parse args ───────────────────────────────────
DRY_RUN=false
TAG=""
MSG=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --tag)     TAG="$2"; shift 2 ;;
    *)         MSG="$1"; shift ;;
  esac
done

# ── Verify git repo ──────────────────────────────
git rev-parse --is-inside-work-tree &>/dev/null || err "Not a git repo. Run: git init"

# ── Check for changes ────────────────────────────
blaze "Checking for changes..."
if git diff --quiet && git diff --cached --quiet; then
  UNTRACKED=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
  [[ "$UNTRACKED" -eq 0 ]] && { warn "Nothing to commit. Working tree clean."; exit 0; }
fi

echo ""
echo -e "${CYN}── Changed files ──────────────────────────────${RST}"
git status --short
echo ""

if [[ "$DRY_RUN" == true ]]; then
  blaze "Dry run — no changes committed."
  exit 0
fi

# ── Commit message ───────────────────────────────
if [[ -z "$MSG" ]]; then
  echo -e "${AMB}Commit message${RST} (leave blank for auto-timestamp):"
  read -r MSG
  [[ -z "$MSG" ]] && MSG="chore: update $(date '+%Y-%m-%d %H:%M')"
fi

# ── Stage & commit ───────────────────────────────
git add -A

echo ""
echo -e "${CYN}── Staged changes ─────────────────────────────${RST}"
git diff --cached --stat
echo ""

read -rp "$(echo -e "${YLW}Commit as:${RST} \"$MSG\" ? [y/N] ")" CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { warn "Aborted."; git reset HEAD; exit 0; }

git commit -m "$MSG"
ok "Committed: $MSG"

# ── Optional tag ─────────────────────────────────
if [[ -n "$TAG" ]]; then
  git tag -a "$TAG" -m "Release $TAG"
  ok "Tagged: $TAG"
fi

# ── Push ─────────────────────────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE=$(git remote 2>/dev/null | head -1)

if [[ -z "$REMOTE" ]]; then
  warn "No remote set. Add one with:"
  echo "  git remote add origin https://github.com/uchejerla/blaze.git"
  exit 1
fi

blaze "Pushing to $REMOTE/$BRANCH..."
git push "$REMOTE" "$BRANCH" ${TAG:+refs/tags/"$TAG"}

echo ""
ok "Pushed to GitHub → https://github.com/uchejerla/blaze"
echo -e "  ${CYN}Branch:${RST} $BRANCH"
echo -e "  ${CYN}Commit:${RST} $(git rev-parse --short HEAD) — $MSG"
[[ -n "$TAG" ]] && echo -e "  ${CYN}Tag:${RST}    $TAG"
echo ""
