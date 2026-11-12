"""Read a spreadsheet of contracts and schedules into contract records (decision G5; D8).

Pure Python: no Frappe imports, no database. The Sidra Contract Import DocType turns the result
into draft registered (External) contracts.

One row per schedule line. Contract columns may be repeated on every row of a contract or given
only on its first row; a later row that gives a different value is an error.

Required columns: external_reference, customer, signed_on, agreed_price, unit, due_date, amount.
Optional columns: unit_price, down_payment_mode, down_payment, row_type, description, terms_summary.

Dates: YYYY-MM-DD, DD/MM/YYYY or DD-MM-YYYY (NFR-10), or spreadsheet date cells.
Amounts are dollars and cents. Payments made to date are not imported (D8: a later phase).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

REQUIRED = ("external_reference", "customer", "signed_on", "agreed_price", "unit", "due_date", "amount")
OPTIONAL = ("unit_price", "down_payment_mode", "down_payment", "row_type", "description", "terms_summary")
CONTRACT_FIELDS = (
	"customer",
	"signed_on",
	"agreed_price",
	"down_payment_mode",
	"down_payment",
	"terms_summary",
)
ROW_TYPES = ("Installment", "Down payment", "Fee")
DOWN_PAYMENT_MODES = ("None", "Included in schedule", "Recorded separately")
CENT = Decimal("0.01")


@dataclass
class ImportedContract:
	external_reference: str
	first_row: int
	customer: str = ""
	signed_on: date | None = None
	agreed_price: Decimal | None = None
	down_payment_mode: str = "None"
	down_payment: Decimal = Decimal("0.00")
	terms_summary: str = ""
	units: list[tuple[str, Decimal | None]] = field(default_factory=list)
	schedule: list[tuple[str, date, Decimal, str]] = field(default_factory=list)


def normalize_reference(value) -> str:
	"""Same rule as the contract form: trim, collapse inner spaces, upper-case."""
	return re.sub(r"\s+", " ", str(value or "").strip()).upper()


def _header(value) -> str:
	return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _text(value) -> str:
	if value is None:
		return ""
	if isinstance(value, float) and value.is_integer():
		value = int(value)
	return str(value).strip()


def parse_date(value) -> date:
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	text = _text(value)
	for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
		try:
			return datetime.strptime(text, pattern).date()
		except ValueError:
			continue
	raise ValueError(f"'{text}' is not a date (use YYYY-MM-DD or DD/MM/YYYY)")


def parse_money(value) -> Decimal:
	text = _text(value).replace(",", "").replace("$", "")
	try:
		amount = Decimal(text)
		if not amount.is_finite():
			raise ValueError("Amounts must be finite numbers")
		rounded = amount.quantize(CENT, rounding=ROUND_HALF_UP)
	except InvalidOperation:
		raise ValueError(f"'{_text(value)}' is not an amount") from None
	if amount != rounded:
		raise ValueError(f"'{text}' has more than two decimals")
	return rounded


def parse_rows(rows) -> tuple[list[ImportedContract], list[str]]:
	"""Rows as read from a CSV or XLSX file, the first being the header.

	Returns the contracts in file order and a list of errors naming spreadsheet row numbers.
	"""
	rows = [list(r) for r in rows or []]
	if not rows:
		return [], ["The file is empty"]
	header = [_header(c) for c in rows[0]]
	missing = [c for c in REQUIRED if c not in header]
	if missing:
		return [], [f"Missing column(s): {', '.join(missing)}"]
	index = {name: header.index(name) for name in REQUIRED + OPTIONAL if name in header}

	contracts: dict[str, ImportedContract] = {}
	errors: list[str] = []
	for number, raw in enumerate(rows[1:], start=2):
		cells = {name: (raw[i] if i < len(raw) else None) for name, i in index.items()}
		if all(_text(v) == "" for v in cells.values()):
			continue
		try:
			_read_row(number, cells, contracts)
		except ValueError as e:
			errors.append(f"Row {number}: {e}")

	for contract in contracts.values():
		errors.extend(_check_contract(contract))
	return list(contracts.values()), errors


def _read_row(number, cells, contracts):
	reference = normalize_reference(cells.get("external_reference"))
	if not reference:
		raise ValueError("external_reference is empty")
	contract = contracts.get(reference)
	if contract is None:
		contract = contracts[reference] = ImportedContract(reference, number)

	values = {}
	if _text(cells.get("customer")):
		values["customer"] = _text(cells["customer"])
	if _text(cells.get("signed_on")):
		values["signed_on"] = parse_date(cells["signed_on"])
	if _text(cells.get("agreed_price")):
		values["agreed_price"] = parse_money(cells["agreed_price"])
	if _text(cells.get("down_payment_mode")):
		mode = _text(cells["down_payment_mode"])
		match = [m for m in DOWN_PAYMENT_MODES if m.lower() == mode.lower()]
		if not match:
			raise ValueError(f"down_payment_mode must be one of {', '.join(DOWN_PAYMENT_MODES)}")
		values["down_payment_mode"] = match[0]
	if _text(cells.get("down_payment")):
		values["down_payment"] = parse_money(cells["down_payment"])
	if _text(cells.get("terms_summary")):
		values["terms_summary"] = _text(cells["terms_summary"])
	first = number == contract.first_row
	for name, value in values.items():
		current = getattr(contract, name)
		if first or current in (None, "", Decimal("0.00"), "None"):
			setattr(contract, name, value)
		elif current != value:
			raise ValueError(
				f"{name} '{value}' differs from '{current}' given earlier for {contract.external_reference}"
			)

	unit = _text(cells.get("unit"))
	if not unit:
		raise ValueError("unit is empty")
	unit_price = parse_money(cells["unit_price"]) if _text(cells.get("unit_price")) else None
	known = dict(contract.units)
	if unit in known:
		if unit_price is not None and known[unit] not in (None, unit_price):
			raise ValueError(f"unit {unit} has two prices")
		if unit_price is not None and known[unit] is None:
			contract.units[[u for u, _ in contract.units].index(unit)] = (unit, unit_price)
	else:
		contract.units.append((unit, unit_price))

	row_type = _text(cells.get("row_type")) or "Installment"
	match = [t for t in ROW_TYPES if t.lower() == row_type.lower()]
	if not match:
		raise ValueError(f"row_type must be one of {', '.join(ROW_TYPES)}")
	if not _text(cells.get("due_date")):
		raise ValueError("due_date is empty")
	if not _text(cells.get("amount")):
		raise ValueError("amount is empty")
	amount = parse_money(cells["amount"])
	if amount <= 0:
		raise ValueError("amount must be greater than zero")
	contract.schedule.append(
		(match[0], parse_date(cells["due_date"]), amount, _text(cells.get("description")))
	)


def _check_contract(contract) -> list[str]:
	where = f"{contract.external_reference} (row {contract.first_row})"
	errors = []
	if not contract.customer:
		errors.append(f"{where}: customer is empty")
	if contract.signed_on is None:
		errors.append(f"{where}: signed_on is empty")
	if contract.agreed_price is None or contract.agreed_price <= 0:
		errors.append(f"{where}: agreed_price must be greater than zero")
		return errors
	if len(contract.units) == 1 and contract.units[0][1] is None:
		contract.units[0] = (contract.units[0][0], contract.agreed_price)
	if any(price is None for _, price in contract.units):
		errors.append(f"{where}: give unit_price for every unit of a multi-unit contract")
	elif sum(price for _, price in contract.units) != contract.agreed_price:
		errors.append(
			f"{where}: unit prices add up to {sum(p for _, p in contract.units)}, not {contract.agreed_price}"
		)
	return errors
