"""Read-only presentation rules for existing operational records (SRS §3.6).

Definitions match the reviewed Insights starter. No receipts, allocation, accounting,
approved baseline, target or forecast is inferred from these operational records.
"""

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo


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


def site_period_bounds(start, end, site_timezone):
	"""Convert business-day boundaries for Frappe's site-local naive Datetime storage."""
	zone = ZoneInfo(site_timezone)
	mogadishu = ZoneInfo("Africa/Mogadishu")
	lower = datetime.combine(start, time.min, mogadishu).astimezone(zone).replace(tzinfo=None)
	upper = (
		datetime.combine(end + timedelta(days=1), time.min, mogadishu).astimezone(zone).replace(tzinfo=None)
	)
	return lower, upper - timedelta(microseconds=1)


def registration_day(value, site_timezone):
	dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=ZoneInfo(site_timezone))
	return dt.astimezone(ZoneInfo("Africa/Mogadishu")).date()


def stage_overdue(row, today):
	"""Incomplete after its recorded planned end: no actual end and completion below 100.

	The one overdue rule for both the staff jobs view and the executive exceptions.
	"""
	planned = row.get("planned_end")
	if not planned or row.get("actual_end"):
		return False
	completion = row.get("completion_pct")
	return date.fromisoformat(str(planned)[:10]) < today and (
		completion is None or decimal_amount(completion) < 100
	)


def stage_date_exception(row, today):
	"""Recorded dates only; missing dates never imply an approved/on-time baseline.

	An exception is a stage that is overdue now or that recorded an actual end after its planned end.
	"""
	planned = row.get("planned_end")
	if not planned:
		return False
	actual = row.get("actual_end")
	if actual:
		return date.fromisoformat(str(actual)[:10]) > date.fromisoformat(str(planned)[:10])
	return stage_overdue(row, today)
