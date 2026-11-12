# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Construction controls (CON-04, CON-05, CON-06; SRS v2.0 §3.1; docs/CONSTRUCTION-CONTROLS_v0.1.md).

Pure rules with no Frappe import, so they run in the plain unit tests (`test_engine_*.py`).
Money is Decimal rounded to cents. Nothing here creates an invoice or posts to the ledger.
"""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

VARIATION_TYPES = ("Addition", "Omission")
INSPECTION_RESULTS = ("Pass", "Pass with defects", "Fail")
CHECK_RESULTS = ("Pass", "Fail", "Not Applicable")

# Job statuses in which a contract exists and work can be varied, inspected or revised.
VARIATION_STATUSES = ("Contracted", "In Progress", "On Hold", "Completed", "Defects Period")
CLOSED_STATUSES = ("Closed", "Cancelled")


class ConstructionRuleError(ValueError):
	"""A construction control was broken; the message is shown to the user."""


def money(value) -> Decimal:
	return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def boq_key(rows) -> tuple:
	"""What a BOQ says, for comparing two BOQs: lines in order, money in cents.

	`rows` are mappings (or objects with .get) holding cost_code, description, uom, qty, rate.
	"""
	return tuple(
		(
			(row.get("cost_code") or "").strip(),
			(row.get("description") or "").strip(),
			row.get("uom") or "",
			Decimal(str(row.get("qty") or 0)).normalize(),
			money(row.get("rate")),
		)
		for row in rows
	)


def signed_variation(variation_type: str, amount) -> Decimal:
	"""CON-06: an addition raises the contract value, an omission lowers it. Amounts are entered positive."""
	if variation_type not in VARIATION_TYPES:
		raise ConstructionRuleError(f"Unknown variation type {variation_type!r}")
	value = money(amount)
	if value <= 0:
		raise ConstructionRuleError("The variation amount must be greater than zero")
	return value if variation_type == "Addition" else -value


def contract_value_after(contract_value, approved_signed_amounts, change=0) -> Decimal:
	"""Original contract value plus approved variations plus `change`; never below zero.

	SRS v2.0 §3.1: "schedule values and latest approved variations must reconcile to contract total".
	"""
	base = money(contract_value)
	if base <= 0:
		raise ConstructionRuleError("Enter the job's contract value before recording a variation")
	total = base + sum((money(a) for a in approved_signed_amounts), Decimal("0")) + money(change)
	if total < 0:
		raise ConstructionRuleError(
			f"This would take the contract value below zero ({total}); an omission cannot exceed the current value"
		)
	return total


def inspection_problems(result: str, checks, defects_found: str = "", next_action: str = "") -> list[str]:
	"""CON-05: the checklist, overall result, defects and next action must agree.

	`checks` are mappings with item, result and remarks. Returns messages; empty means consistent.
	"""
	problems = []
	if result not in INSPECTION_RESULTS:
		problems.append(f"Choose the overall result ({', '.join(INSPECTION_RESULTS)})")
	failed = []
	for idx, check in enumerate(checks, start=1):
		if check.get("result") not in CHECK_RESULTS:
			problems.append(f"Checklist row {idx}: choose Pass, Fail or Not Applicable")
		elif check.get("result") == "Fail":
			failed.append(idx)
			if not (check.get("remarks") or "").strip():
				problems.append(f"Checklist row {idx}: say what failed in Remarks")
	if result == "Pass" and failed:
		problems.append(
			"The overall result cannot be Pass when checklist row(s) {} failed".format(
				", ".join(str(i) for i in failed)
			)
		)
	if result in ("Pass with defects", "Fail"):
		if not (defects_found or "").strip():
			problems.append("Describe the defects found")
		if not (next_action or "").strip():
			problems.append("Give the next action")
	return problems
