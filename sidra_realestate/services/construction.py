# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Construction controls (CON-03, CON-04, CON-05, CON-06; SRS v2.0 §3.1; docs/CONSTRUCTION-CONTROLS_v0.2.md).

Pure rules with no Frappe import, so they run in the plain unit tests (`test_engine_*.py`).
Money is Decimal rounded to cents. Nothing here creates an invoice or posts to the ledger.
"""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

INSPECTION_RESULTS = ("Pass", "Pass with defects", "Fail")
CHECK_RESULTS = ("Pass", "Fail", "Not Applicable")

# Job statuses in which a contract exists and work can be varied.
VARIATION_STATUSES = ("Contracted", "In Progress", "On Hold", "Completed", "Defects Period")
CLOSED_STATUSES = ("Closed", "Cancelled")

# Decision G11 (Mohamoud, 12 Nov 2026; issue #37). Change only with an approved spec version
# (CLAUDE.md rule 2).
VARIATION_GM_LIMIT = Decimal("1000.00")  # above this, only the General Manager approves
RETENTION_MAX_PCT = Decimal("10")
PROJECT_MANAGER = "Sidra Project Manager"
GENERAL_MANAGER = "Sidra General Manager"


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


def variation_amount(amount) -> Decimal:
	"""CON-06 / G11: variation orders are additions only; the amount raises the contract value."""
	value = money(amount)
	if value <= 0:
		raise ConstructionRuleError("The variation amount must be greater than zero")
	return value


def variation_approval_problem(amount, approver: str, approver_roles, raised_by: str) -> str | None:
	"""G11: a second person approves; up to the limit a Project Manager may, above it only the GM."""
	if approver == raised_by:
		return f"A variation order is approved by a second person: {raised_by} raised it and cannot approve it"
	roles = set(approver_roles)
	if money(amount) > VARIATION_GM_LIMIT:
		if GENERAL_MANAGER not in roles:
			return f"A variation order above {VARIATION_GM_LIMIT} is approved by the General Manager"
	elif not roles & {PROJECT_MANAGER, GENERAL_MANAGER}:
		return "A variation order is approved by a Project Manager or the General Manager"
	return None


def contract_value_after(contract_value, approved_amounts, change=0) -> Decimal:
	"""Original contract value plus approved variations plus `change`.

	SRS v2.0 §3.1: "schedule values and latest approved variations must reconcile to contract total".
	"""
	base = money(contract_value)
	if base <= 0:
		raise ConstructionRuleError("The job has no approved contract value; approve its contract first (CON-03)")
	return base + sum((money(a) for a in approved_amounts), Decimal("0")) + money(change)


def billing_pct_problem(percentages) -> str | None:
	"""CON-03 / G11: payment milestones are the stages' Billing %, which must add up to exactly 100."""
	total = sum((Decimal(str(p or 0)) for p in percentages), Decimal("0"))
	if total.quantize(Decimal("0.000001")) != Decimal("100"):
		return f"Stage billing percentages must add up to exactly 100 (they add up to {total.normalize()})"
	return None


def milestone_amounts(contract_value, percentages) -> list[Decimal]:
	"""Each milestone is contract value × Billing %, in cents; the last billed stage takes the rounding
	so the milestones add up to the contract value exactly (SRS v2.0 §3.1)."""
	value = money(contract_value)
	pcts = [Decimal(str(p or 0)) for p in percentages]
	amounts = [money(value * p / 100) for p in pcts]
	billed = [i for i, p in enumerate(pcts) if p]
	if billed and billing_pct_problem(pcts) is None:
		last = billed[-1]
		amounts[last] += value - sum(amounts, Decimal("0"))
	return amounts


def retention_problem(retention_pct, retention_period_months) -> str | None:
	"""G11: retention from 0 to 10 % of the contract, held for a whole number of months (0 allowed)."""
	pct = Decimal(str(retention_pct or 0))
	if not 0 <= pct <= RETENTION_MAX_PCT:
		return f"Retention must be from 0 to {RETENTION_MAX_PCT} %"
	months = retention_period_months or 0
	if int(months) != months or months < 0:
		return "The retention period is a whole number of months, 0 or more"
	return None


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
