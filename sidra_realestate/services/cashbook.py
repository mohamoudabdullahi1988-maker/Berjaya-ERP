"""Validate the pilot statement format without depending on a provider's export layout."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

COLUMNS = ("Date", "Reference", "Currency", "Deposit", "Withdrawal")
MAX_ROWS = 1000
MAX_AMOUNT = Decimal("1000000000000")


def amount(value, precision):
	try:
		number = Decimal(str(value))
		if number.is_finite() and abs(number) < MAX_AMOUNT and number == round(number, precision):
			return round(number, precision) if number else Decimal(0)
	except InvalidOperation, ValueError:
		pass
	raise ValueError(f"Enter an amount below 1 trillion with at most {precision} decimal places.")


def statement_line(day, reference, currency, deposit, withdrawal, description, precision):
	if isinstance(day, datetime):
		day = day.date()
	if not isinstance(day, date):
		original = str(day)
		day = date.fromisoformat(original)
		if day.isoformat() != original:
			raise ValueError("Use YYYY-MM-DD for the statement date.")
	if not isinstance(reference, str) or not (0 < len(reference.strip()) <= 140):
		raise ValueError("Use the statement transaction reference as text (1 to 140 characters).")
	deposit, withdrawal = (
		amount(0 if value in ("", None) else value, precision) for value in (deposit, withdrawal)
	)
	if min(deposit, withdrawal) < 0 or (deposit > 0) == (withdrawal > 0):
		raise ValueError("Enter a positive deposit or withdrawal, with the other amount blank or zero.")
	return {
		"date": day,
		"reference_number": reference.strip(),
		"currency": currency,
		"deposit": deposit,
		"withdrawal": withdrawal,
		"description": str(description or ""),
	}


def statement_rows(rows, currency, precision):
	header = [str(cell or "").strip() for cell in next(rows, ())]
	while header and not header[-1]:
		header.pop()
	if header not in (list(COLUMNS), [*COLUMNS, "Description"]):
		raise ValueError(
			"Use the template headers Date, Reference, Currency, Deposit, Withdrawal, with optional Description."
		)
	lines = []
	for index, row in enumerate(rows, start=2):
		if index > MAX_ROWS + 1:
			raise ValueError(f"Use at most {MAX_ROWS} data rows per statement.")
		if all(cell in (None, "") for cell in row):
			continue
		try:
			if any(cell not in (None, "") for cell in row[len(header) :]):
				raise ValueError("Unexpected columns.")
			values = dict(zip(header, row))
			if values.get("Currency") != currency:
				raise ValueError(f"The statement currency must be {currency}.")
			lines.append(
				statement_line(
					values.get("Date"),
					values.get("Reference"),
					currency,
					values.get("Deposit"),
					values.get("Withdrawal"),
					values.get("Description"),
					precision,
				)
			)
		except ValueError as exc:
			raise ValueError(f"Row {index} — {exc}") from exc
	if not lines:
		raise ValueError("The statement has no transaction lines.")
	return lines
