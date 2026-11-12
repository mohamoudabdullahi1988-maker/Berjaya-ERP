#!/usr/bin/env bash
# =====================================================================
# sidra-homes-run_v0.1.sh
# One script for the test server: backup, update the app code to
# `develop`, rebuild, restart, then load and verify the Sidra Homes
# sample data (decision G13).
# Version: v0.1   Date: 2026-11-12   Site: sidra.local
#
# Run as root on the test server:
#   bash sidra-homes-run_v0.1.sh
#
# RULES ENFORCED
#   * Backup runs first. If it fails, nothing else runs.
#   * The git stash is never applied or dropped.
#   * The code is only fast-forwarded. Local changes or a diverged
#     branch stop the script; nothing is overwritten or discarded.
#   * No Company is deleted, merged or renamed. No GL table is edited.
#   * On any refusal or error it stops and prints the message.
# =====================================================================
set -uo pipefail

SITE=sidra.local
BENCH=/home/frappe/sidra/frappe-bench
APP=sidra_realestate
FRAPPE_USER=frappe
BRANCH=develop
VERIFY="$BENCH/apps/$APP/deploy/sidra-homes-verify_v0.2.sh"
LOG=/root/sidra-homes-run.log

exec > >(tee -a "$LOG") 2>&1
echo "=== sidra-homes-run_v0.1.sh  $(date -Is) ==="
[ "$(id -u)" -eq 0 ] || { echo "FATAL: run as root"; exit 1; }
say(){ echo; echo "==== $* ===="; }
die(){ echo; echo "STOPPED: $*"; echo "Nothing after this point was run. Log: $LOG"; exit 1; }
asfrappe(){ sudo -u "$FRAPPE_USER" -H bash -lc "cd $BENCH && $1"; }
inapp(){ asfrappe "cd apps/$APP && $1"; }

[ -d "$BENCH/apps/$APP/.git" ] || die "$BENCH/apps/$APP is not a git checkout"

# ---------------------------------------------------------------------
say "1/5 Backup with files (before anything else)"
out=$(asfrappe "bench --site $SITE backup --with-files" 2>&1); rc=$?
echo "$out"
{ [ $rc -eq 0 ] && ! echo "$out" | grep -qi "traceback"; } || die "backup failed"
echo "BACKUP FOLDER: $BENCH/sites/$SITE/private/backups"

# ---------------------------------------------------------------------
say "2/5 Update $APP to $BRANCH (fast-forward only)"
echo "Before: $(inapp 'git rev-parse HEAD')  $(inapp 'git status --short --branch | head -1')"
echo "Stash list (read only, never applied or dropped):"
inapp "git stash list" || true

[ -z "$(inapp 'git status --porcelain --untracked-files=no')" ] \
  || die "the app folder has uncommitted changes. Send the lines below to the developer:
$(inapp 'git status --short --untracked-files=no')"

REMOTE=$(inapp "git remote -v" | awk '/sidra-erp/ && /\(fetch\)/ {print $1; exit}')
[ -n "$REMOTE" ] || die "no git remote points at sidra-erp. Remotes are:
$(inapp 'git remote -v')"

inapp "git fetch $REMOTE $BRANCH" || die "could not fetch $BRANCH from $REMOTE (network or GitHub access)"
TARGET=$(inapp "git rev-parse FETCH_HEAD")
if [ "$(inapp 'git rev-parse HEAD')" = "$TARGET" ]; then
  echo "Already on the latest $BRANCH."
else
  inapp "git merge-base --is-ancestor HEAD $TARGET" \
    || die "the server's code has commits that are not in $BRANCH, so it cannot be fast-forwarded"
  inapp "git merge --ff-only $TARGET" || die "fast-forward failed"
fi
echo "After:  $(inapp 'git rev-parse HEAD')"
[ -f "$VERIFY" ] || die "this code does not contain the Sidra Homes change yet (PR #45 not merged into $BRANCH?)"

# ---------------------------------------------------------------------
say "3/5 Build the app's web files"
asfrappe "bench build --app $APP" || die "bench build failed"

# ---------------------------------------------------------------------
say "4/5 Restart so the server runs the new code"
if command -v supervisorctl >/dev/null 2>&1 && supervisorctl status >/dev/null 2>&1; then
  supervisorctl restart all || die "supervisor restart failed"
elif asfrappe "bench restart"; then
  :
else
  die "could not restart the bench processes. Restart them the way this server normally does, then run:
  bash $VERIFY all"
fi
sleep 5

# ---------------------------------------------------------------------
say "5/5 Migrate, load the sample data, list the old demo Companies, verify"
bash "$VERIFY" all; rc=$?

echo
if [ $rc -eq 0 ]; then
  echo "FINISHED. Read the PASS / FAIL / NOT VERIFIED lines above."
  echo "Then open /sidra-staff/, choose Sidra Homes and Last 90 days."
else
  echo "STOPPED inside the load/verify step. Send the message above as it is. Do not run again."
fi
echo "Logs: $LOG and /root/sidra-homes-verify.log"
exit $rc
