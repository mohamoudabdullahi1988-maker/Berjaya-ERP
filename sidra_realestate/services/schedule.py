"""Installment schedule generator (SRS v2.0 §3.3 and §6 "Preview schedule"; INS-02, INS-13, INS-14).

Pure Python: no Frappe imports, no database. Amounts are Decimal, USD to the cent.

	balance = agreed sale price - contractual down payment
	n - 1 installments of round(balance / n) in whole dollars (half up); the last absorbs the remainder

First due date: the due day in (contract month + grace months); if that date is on or
before the contract date, one month later. This matches handover AT-01 and AT-03. SRS
v2.0 §3.3 words it differently and asks for Sidra sign-off: see issue #1. Due days are
limited to 1-28, so a month never needs a rollover.

Markup (SRS v1.6 §5.1, INS-01) is outside P0; callers refuse a non-zero markup.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
DOLLAR = Decimal("1")

DOWN_PAYMENT_TYPES = ("None", "Fixed", "Percent")


class ScheduleError(ValueError):
	"""Invalid schedule parameters (SRS v2.0 §6 error semantics)."""


@dataclass(frozen=True)
class InstallmentLine:
	seq: int
	due_date: date
	amount: Decimal


def money(value) -> Decimal:
	"""Decimal rounded to the cent. Floats are converted through their shortest repr."""
	if isinstance(value, bool) or value is None:
		raise ScheduleError(f"Not a money amount: {value!r}")
	if isinstance(value, float):
		value = repr(value)
	try:
		return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
	except ArithmeticError as e:
		raise ScheduleError(f"Not a money amount: {value!r}") from e


def down_payment_amount(price, down_payment_type: str, value=0) -> Decimal:
	price = money(price)
	if down_payment_type not in DOWN_PAYMENT_TYPES:
		raise ScheduleError(f"Down payment type must be one of {DOWN_PAYMENT_TYPES}")
	if down_payment_type == "None":
		return money(0)
	value = money(value)
	if value <= 0:
		raise ScheduleError("A fixed or percentage down payment must be greater than zero")
	if down_payment_type == "Fixed":
		down = value
	else:
		if value > 100:
			raise ScheduleError("A down payment percentage cannot exceed 100")
		down = money(price * value / Decimal(100))
	if down > price:
		raise ScheduleError("The down payment cannot exceed the agreed price")
	return down


def _add_months(year: int, month: int, months: int) -> tuple[int, int]:
	index = year * 12 + (month - 1) + months
	return index // 12, index % 12 + 1


def _check_int(name, value, low, high):
	if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
		raise ScheduleError(f"{name} must be a whole number from {low} to {high}, got {value!r}")


def first_due_date(signed_on: date, grace_months: int, due_day: int) -> date:
	_check_int("grace_months", grace_months, 0, 12)
	_check_int("due_day", due_day, 1, 28)
	if not isinstance(signed_on, date):
		raise ScheduleError("signed_on must be a date")
	year, month = _add_months(signed_on.year, signed_on.month, grace_months)
	first = date(year, month, due_day)
	if first <= signed_on:
		year, month = _add_months(year, month, 1)
		first = date(year, month, due_day)
	return first


def generate_installments(
	price, down_payment, installments: int, signed_on: date, grace_months: int, due_day: int
) -> list[InstallmentLine]:
	price = money(price)
	down_payment = money(down_payment)
	_check_int("installments", installments, 1, 60)
	if price <= 0:
		raise ScheduleError("The agreed price must be greater than zero")
	if down_payment < 0 or down_payment > price:
		raise ScheduleError("The down payment must be between zero and the agreed price")

	balance = price - down_payment
	if balance <= 0:
		raise ScheduleError("Nothing left to pay in installments; use a cash contract")

	regular = (balance / installments).quantize(DOLLAR, rounding=ROUND_HALF_UP).quantize(CENT)
	last = balance - regular * (installments - 1)
	if regular <= 0 or last <= 0:
		raise ScheduleError(
			f"{balance} cannot be split into {installments} whole-dollar installments with a positive last one"
		)

	first = first_due_date(signed_on, grace_months, due_day)
	lines = []
	for i in range(installments):
		year, month = _add_months(first.year, first.month, i)
		lines.append(
			InstallmentLine(
				seq=i + 1,
				due_date=date(year, month, due_day),
				amount=last if i == installments - 1 else regular,
			)
		)
	return lines
