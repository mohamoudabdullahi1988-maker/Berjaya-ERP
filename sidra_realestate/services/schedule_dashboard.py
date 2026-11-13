"""Read-only calendar presentation of agreed schedule rows; no payment allocation."""

import re
from datetime import date, timedelta
from decimal import Decimal

from sidra_realestate.services.executive_metrics import decimal_amount, money


def month_bounds(month):
	if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
		raise ValueError("Choose a month in YYYY-MM format")
	start = date.fromisoformat(month + "-01")
	if not 1900 <= start.year <= 2200:
		raise ValueError("Choose a month between 1900 and 2200")
	next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
	return start, next_month - timedelta(days=1)


def calendar_snapshot(rows, month, today):
	"""Dates are authoritative; a past date does not establish an unpaid balance."""
	start, end = month_bounds(month)
	events, amounts, days = [], {key: [] for key in ("month", "past_due", "today", "upcoming")}, {}
	for row in rows:
		due = date.fromisoformat(str(row["due_date"])[:10])
		if not start <= due <= end:
			continue
		state = "past_due" if due < today else "today" if due == today else "upcoming"
		try:
			value = decimal_amount(row["amount"])
			if value < 0:
				raise ValueError("Negative schedule amount")
		except ValueError:
			value = None
		amounts["month"].append(value)
		amounts[state].append(value)
		days.setdefault(due.isoformat(), []).append(value)
		events.append(
			{
				**row,
				"due_date": due.isoformat(),
				"amount": money(value) if value is not None else None,
				"date_state": state,
			}
		)

	def total(values):
		return None if any(value is None for value in values) else money(sum(values, Decimal(0)))

	return {
		"available": True,
		"month": month,
		"today": today.isoformat(),
		"basis": "gross_schedule",
		"allocation_available": False,
		"notice": "Agreed schedule before payment reconciliation. Past due dates are not verified unpaid balances. Invoice receipts below are separate from contract installments.",
		"summary": {key: {"amount": total(values), "count": len(values)} for key, values in amounts.items()},
		"days": [
			{"date": day, "amount": total(values), "count": len(values)}
			for day, values in sorted(days.items())
		],
		"events": sorted(events, key=lambda row: (row["due_date"], row["contract_id"], row["id"])),
	}
