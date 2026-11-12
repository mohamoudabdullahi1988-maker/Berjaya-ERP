# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Title deadline rules (SAL-08, SAL-18; decision G12; docs/KYC-AND-TITLE_v0.1.md).

Pure rules with no Frappe import, so they run in the plain unit tests (`test_engine_*.py`).
Days only: no delay amount is calculated, applied or posted (CLAUDE.md rule 3; G12).
"""

from datetime import date, timedelta

# Decision G12 (Mohamoud, 12 Nov 2026). Change only with an approved spec version (CLAUDE.md rule 2).
ALERT_DAYS = 5  # a title is "Due Soon" from this many days before its deadline

AWAITING = "Awaiting Final Payment"
NO_DEADLINE = "No Deadline on Contract"
IN_PROGRESS = "In Progress"
DUE_SOON = "Due Soon"
OVERDUE = "Overdue"
HANDED_OVER = "Handed Over"
HANDED_OVER_LATE = "Handed Over Late"
STATES = (AWAITING, NO_DEADLINE, IN_PROGRESS, DUE_SOON, OVERDUE, HANDED_OVER, HANDED_OVER_LATE)


def deadline_date(final_payment_date: date | None, deadline_days) -> date | None:
	"""SAL-18: the deadline is the contract's title deadline days counted from the final payment."""
	days = int(deadline_days or 0)
	if not final_payment_date or days <= 0:
		return None
	return final_payment_date + timedelta(days=days)


def title_state(
	today: date,
	final_payment_confirmed: bool,
	deadline: date | None,
	handed_over_on: date | None = None,
) -> tuple[str, int]:
	"""The title record's state and the number of days past the deadline (0 when not late).

	`handed_over_on` counts only once the handover is confirmed.
	"""
	if handed_over_on:
		late = (handed_over_on - deadline).days if deadline else 0
		return (HANDED_OVER_LATE, late) if late > 0 else (HANDED_OVER, 0)
	if not final_payment_confirmed:
		return AWAITING, 0
	if not deadline:
		return NO_DEADLINE, 0
	remaining = (deadline - today).days
	if remaining < 0:
		return OVERDUE, -remaining
	if remaining <= ALERT_DAYS:
		return DUE_SOON, 0
	return IN_PROGRESS, 0
