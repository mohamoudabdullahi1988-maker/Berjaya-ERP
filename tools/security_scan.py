"""Offline source checks; never print source lines, candidate secrets or credential values."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
	hook = shutil.which("detect-secrets-hook")
	if not hook:
		raise SystemExit("Install tools/security-requirements.txt in the active Python environment.")
	files = (
		subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
		.stdout.decode()
		.split("\0")
	)
	secrets = subprocess.run(
		[
			hook,
			"--no-verify",
			"--exclude-files",
			r"^\.secrets\.baseline$",
			"--baseline",
			str(ROOT / ".secrets.baseline"),
			*[name for name in files if name],
		],
		cwd=ROOT,
		capture_output=True,
		text=True,
	)
	# The baseline contains only three reviewed, hashed CI fixtures. Network validation
	# is disabled: scanners must not transmit candidate credentials to providers.
	print(
		"Secret scan:",
		"PASS" if secrets.returncode == 0 else "FAIL (review with detect-secrets-hook locally)",
	)
	bandit = subprocess.run(
		[
			sys.executable,
			"-m",
			"bandit",
			"-q",
			"-r",
			"sidra_realestate",
			"integrations/insights/build_workbook.py",
			"-x",
			"*/test_*.py,*/tests/*",
			"-f",
			"json",
		],
		cwd=ROOT,
		capture_output=True,
		text=True,
	)
	if bandit.returncode not in (0, 1):
		raise SystemExit("Bandit could not run; source checks are incomplete.")
	try:
		report = json.loads(bandit.stdout)
	except json.JSONDecodeError:
		raise SystemExit("Bandit did not return a valid report; source checks are incomplete.") from None
	for error in report["errors"]:
		print("Unscanned file:", error["filename"])
	blocking = []
	for issue in report["results"]:
		print(
			"Bandit:",
			issue["test_id"],
			issue["issue_severity"],
			issue["issue_confidence"],
			issue["filename"],
			"line",
			issue["line_number"],
		)
		if issue["issue_severity"] in ("MEDIUM", "HIGH") and issue["issue_confidence"] in ("MEDIUM", "HIGH"):
			blocking.append(issue)
	print("Bandit gate: medium/high severity AND confidence; all findings above remain visible for review.")
	return int(bool(secrets.returncode or report["errors"] or blocking))


if __name__ == "__main__":
	raise SystemExit(main())
