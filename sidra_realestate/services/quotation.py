# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sale quotation rules (SAL-05; decision G13; docs/SALE-QUOTATION_v0.1.md).

Pure rules with no Frappe import, so they run in the plain unit tests (`test_engine_*.py`).
A quotation is an offer on paper: nothing here reserves a plot, creates a contract or posts.
"""

from decimal import Decimal

from sidra_realestate.services.schedule import money

# Decision G13 (Mohamoud, 12 Nov 2026). Change only with an approved spec version (CLAUDE.md rule 2).
SM_DISCOUNT_LIMIT_PCT = Decimal("5")  # of the unit's listed price; above it the General Manager approves
MIN_MONTHS, MAX_MONTHS = 12, 36  # G1, G13: the months a quotation may show
VALID_DAYS = 7

SALES_MANAGER = "Sidra Sales Manager"
GENERAL_MANAGER = "Sidra General Manager"
NO_APPROVAL = "Not Needed"


class QuotationRuleError(ValueError):
	"""A sale quotation rule was broken; the message is shown to the user."""


def check_unit_prices(listed, cash, installment) -> Decimal:
	"""One unit's prices. Returns its cash discount (0 when quoted at the listed price).

	- the unit must have a listed price;
	- the cash price is the listed price or lower (a discount), and above zero;
	- the installment price is typed per quotation and is never below the listed price.
	"""
	listed, cash, installment = money(listed or 0), money(cash or 0), money(installment or 0)
	if listed <= 0:
		raise QuotationRuleError("The unit has no listed price; enter its price first")
	if cash <= 0 or cash > listed:
		raise QuotationRuleError(
			f"The cash price must be above zero and not above the listed price ({listed})"
		)
	if installment < listed:
		raise QuotationRuleError(f"The installment price cannot be below the listed price ({listed})")
	return listed - cash


def approval_level(units) -> str:
	"""Who must approve the discounts: per unit, up to 5 % of its listed price the Sales Manager,
	above 5 % the General Manager. `units` are (listed, cash) pairs."""
	level = NO_APPROVAL
	for listed, cash in units:
		listed, cash = money(listed), money(cash)
		discount = listed - cash
		if discount <= 0:
			continue
		if discount * 100 > SM_DISCOUNT_LIMIT_PCT * listed:
			return GENERAL_MANAGER
		level = SALES_MANAGER
	return level


def approval_problem(level: str, approver: str, approver_roles, prepared_by: str) -> str | None:
	"""SRS v1.6 §2: discounts need a second person; the General Manager may approve any discount."""
	if level == NO_APPROVAL:
		return "This quotation has no discount to approve"
	if approver == prepared_by:
		return f"A discount is approved by a second person: {prepared_by} prepared the quotation"
	roles = set(approver_roles)
	if level == GENERAL_MANAGER and GENERAL_MANAGER not in roles:
		return f"A discount above {SM_DISCOUNT_LIMIT_PCT} % of the listed price is approved by the General Manager"
	if not roles & {SALES_MANAGER, GENERAL_MANAGER}:
		return "A discount is approved by a Sales Manager or the General Manager"
	return None


def months_problem(months) -> str | None:
	if months is None or int(months) != months or not MIN_MONTHS <= months <= MAX_MONTHS:
		return f"The number of installments must be a whole number from {MIN_MONTHS} to {MAX_MONTHS}"
	return None
