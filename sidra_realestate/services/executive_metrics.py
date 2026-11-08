"""Read-only presentation rules for existing operational records (SRS §3.6).

Definitions match the reviewed Insights starter. No receipts, allocation, accounting,
approved baseline, target or forecast is inferred from these operational records.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def period_window(period, today):
	if period == "this_month":
		return today.replace(day=1), today
	if period in ("last_30_days", "last_90_days"):
		return today - timedelta(days=(30 if period == "last_30_days" else 90) - 1), today
	raise ValueError("Unsupported reporting period")


def decimal_amount(value):
	if value is None or isinstance(value, bool) or str(value).strip() == "":
		raise ValueError("A numeric source amount is required")
	try:
		amount = Decimal(str(value))
	except (InvalidOperation, TypeError, ValueError) as exc:
		raise ValueError("A numeric source amount is required") from exc
	if not amount.is_finite():
		raise ValueError("Source amount must be finite")
	return amount


def money(value):
	return str(decimal_amount(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def month_starts(today, count=6):
	end = today.year * 12 + today.month - 1
	return [date(index // 12, index % 12 + 1, 1) for index in range(end - count + 1, end + 1)]


def stage_date_exception(row, today):
	"""Recorded dates only; missing dates never imply an approved/on-time baseline."""
	planned = row.get("planned_end")
	if not planned:
		return False
	planned = date.fromisoformat(str(planned)[:10])
	actual = row.get("actual_end")
	if actual:
		return date.fromisoformat(str(actual)[:10]) > planned
	completion = row.get("completion_pct")
	return planned < today and (completion is None or decimal_amount(completion) < 100)
