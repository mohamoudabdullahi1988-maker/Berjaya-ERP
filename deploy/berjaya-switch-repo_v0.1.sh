#!/usr/bin/env bash
# =====================================================================
# berjaya-switch-repo_v0.1.sh
# ONE TIME: move the test server's app code from the old sidra-erp
# repository to Berjaya-ERP `develop`, then deploy it.
# Version: v0.1   Date: 2026-11-25   Site: sidra.local
#
# Why: on 22 Nov 2026 sidra-erp develop (a9713f9) was copied into
# Berjaya-ERP as one commit, so the server's sidra-erp checkout cannot
# simply fast-forward to Berjaya-ERP. This script checks that the
# server's code is all inside that copy, then switches the checkout.
#
# Run as root on the test server, inside tmux:
#   tmux new -s deploy
#   bash /root/berjaya-switch-repo_v0.1.sh
#
# WHAT IT DOES, IN ORDER
#   1 checks      root, app folder, no uncommitted changes
#   2 safety      the server's commit must be part of sidra-erp develop
#                 up to a9713f9 (what Berjaya-ERP copied). Otherwise it
#                 stops and lists the commits that would be lost.
#   3 remote      adds a git remote `berjaya` for Berjaya-ERP if missing,
#                 fetches develop and shows what will be deployed
#   4 confirm     you type SWITCH
#   5 backup      bench backup --with-files. If it fails, it stops.
#   6 switch      keeps the old commit as branch `sidra-erp-before-switch`,
#                 points `develop` at Berjaya-ERP develop
#   7 deploy      runs deploy/berjaya-deploy_v0.3.sh from the new code:
#                 build, migrate, restart, checks
#
# It never deletes a remote, never applies or drops a stash, and never
# restores the database. To go back: bash /root/berjaya-deploy_v0.3.sh
# rollback <previous commit> (printed below and saved in $STATE).
# =====================================================================
set -uo pipefail

SITE=sidra.local
BENCH=/home/frappe/sidra/frappe-bench
APP=sidra_realestate
APPDIR=$BENCH/apps/$APP
FRAPPE_USER=frappe
BRANCH=develop
REPO=mohamoudabdullahi1988-maker/Berjaya-ERP
URL=https://github.com/$REPO.git
SYNC=a9713f90ab2ab8fcb056875f400f1270ebda31ce # last sidra-erp develop commit copied into Berjaya-ERP
DEPLOY=berjaya-deploy_v0.3.sh
LOG=/root/berjaya-switch.log
STATE=/root/berjaya-switch-last.txt

exec > >(tee -a "$LOG") 2>&1
echo "=== berjaya-switch-repo_v0.1.sh  $(date -Is) ==="

say(){ echo; echo "==== $* ===="; }
die(){ echo; echo "STOPPED: $*"; echo "Nothing after this point was run. Log: $LOG"; exit 1; }
asfrappe(){ sudo -u "$FRAPPE_USER" -H bash -lc "cd $(printf %q "$BENCH") && $(printf '%q ' "$@")"; }
inapp(){ sudo -u "$FRAPPE_USER" -H bash -lc "cd $(printf %q "$APPDIR") && $(printf '%q ' "$@")"; }
remote_matching(){ inapp git remote -v | awk -v want="$1" 'index(tolower($2), want) && /\(fetch\)/ {print $1; exit}'; }
version_of(){ inapp git show "$1:$APP/__init__.py" 2>/dev/null | sed -n 's/^__version__ = "\(.*\)"/\1/p'; }

# 1 checks ------------------------------------------------------------
say "Checks"
[ "$(id -u)" = 0 ] || die "run this as root"
[ -d "$APPDIR/.git" ] || die "no git checkout at $APPDIR"
dirty=$(inapp git status --porcelain --untracked-files=no)
[ -z "$dirty" ] || die "the app folder has uncommitted changes. Send these lines to the developer:
$dirty"
PREVIOUS=$(inapp git rev-parse HEAD) || die "could not read the current commit"
echo "Current code: $PREVIOUS  version $(version_of "$PREVIOUS")"
echo "Remotes:"; inapp git remote -v

NEW=$(remote_matching "$(echo "$REPO" | tr '[:upper:]' '[:lower:]')")
if [ -n "$NEW" ] && inapp git fetch -q "$NEW" "$BRANCH" \
  && inapp git merge-base --is-ancestor HEAD FETCH_HEAD; then
  echo "The code already comes from Berjaya-ERP. Nothing to switch: run  bash /root/$DEPLOY"
  exit 0
fi

# 2 safety ------------------------------------------------------------
say "Is the server's code all inside Berjaya-ERP?"
OLD=$(remote_matching "sidra-erp")
[ -n "$OLD" ] || die "no git remote points at sidra-erp, so the server's code cannot be checked"
inapp git fetch -q "$OLD" "$BRANCH" || die "could not fetch $BRANCH from $OLD (network or GitHub access)"
inapp git cat-file -e "$SYNC^{commit}" 2>/dev/null \
  || die "commit ${SYNC:0:7} is not in sidra-erp $BRANCH as fetched; send this log to the developer"
if ! inapp git merge-base --is-ancestor HEAD "$SYNC"; then
  die "the server runs sidra-erp commits that were NOT copied into Berjaya-ERP. Switching would drop them:
$(inapp git log --oneline --no-decorate "$SYNC..HEAD" | head -30)
Send this list to the developer."
fi
echo "PASS  ${PREVIOUS:0:7} is inside sidra-erp develop ${SYNC:0:7}, which Berjaya-ERP copied on 22 Nov"

# 3 remote ------------------------------------------------------------
say "Berjaya-ERP $BRANCH"
if [ -z "$NEW" ]; then
  inapp git remote get-url berjaya >/dev/null 2>&1 && die "a remote named berjaya exists but does not point at $REPO:
$(inapp git remote get-url berjaya)"
  inapp git remote add berjaya "$URL" || die "could not add the berjaya remote"
  NEW=berjaya
  echo "Added remote berjaya -> $URL"
fi
inapp git fetch "$NEW" "$BRANCH" || die "could not fetch $BRANCH from $URL (network or GitHub access)"
TARGET=$(inapp git rev-parse FETCH_HEAD)
echo "Will deploy: $(inapp git log -1 --format='%h %s' "$TARGET")"
echo "Version: $(version_of "$PREVIOUS") -> $(version_of "$TARGET")"
inapp git cat-file -e "$TARGET:deploy/$DEPLOY" 2>/dev/null || die "deploy/$DEPLOY is not in Berjaya-ERP $BRANCH yet"

# 4 confirm -----------------------------------------------------------
echo
read -r -p "Type SWITCH to move the code to Berjaya-ERP $BRANCH and deploy it: " answer
[ "$answer" = "SWITCH" ] || die "not confirmed"

# 5 backup ------------------------------------------------------------
say "Backup"
asfrappe bench --site "$SITE" backup --with-files || die "backup failed; nothing was changed"

# 6 switch ------------------------------------------------------------
say "Switch the code"
inapp git branch -f sidra-erp-before-switch "$PREVIOUS" || die "could not keep the old commit as a branch"
inapp git checkout -B "$BRANCH" "$TARGET" || die "checkout failed; the old code is unchanged on ${PREVIOUS:0:7}"
inapp git branch --set-upstream-to="$NEW/$BRANCH" "$BRANCH" >/dev/null 2>&1 || true
{
  echo "date=$(date -Is)"
  echo "previous_commit=$PREVIOUS"
  echo "switched_to=$TARGET"
} > "$STATE"
echo "Code is now $(inapp git log -1 --format='%h %s')"
echo "Old code kept as branch sidra-erp-before-switch ($PREVIOUS)."
echo "To go back:  bash /root/$DEPLOY rollback $PREVIOUS   (details in $STATE)"

# 7 deploy ------------------------------------------------------------
say "Deploy with $DEPLOY"
cp "$APPDIR/deploy/$DEPLOY" "/root/$DEPLOY" || die "could not copy the deploy script to /root"
exec bash "/root/$DEPLOY"
