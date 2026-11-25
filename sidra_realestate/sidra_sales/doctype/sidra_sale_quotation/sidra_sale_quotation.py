# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Sidra Sale Quotation (SAL-05; decision G13; docs/SALE-QUOTATION_v0.1.md).

An offer for one or more units showing the cash option and the installment option side by side.
It reserves nothing, changes no unit, creates no contract and posts nothing.

- Listed price: each unit's price in force, re-read on every draft save and frozen at issue.
- Cash option: the listed price, or lower as a discount. A discount is approved by a second
  person before the quotation is issued: a Sales Manager up to 5 % of the unit's listed price,
  the General Manager above 5 % (`approve_discount`). Changing a price or unit clears the approval.
- Installment option: a price entered per unit, never below the listed price; terms from the
  chosen contract profile, with the number of installments adjustable from 12 to 36. The schedule
  is indicative, assuming the contract is signed on the quotation date.
- Valid for 7 days unless changed. Issued quotations turn Expired after that date (daily job).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, now_datetime, today

from sidra_realestate.services.quotation import (
	NO_APPROVAL,
	VALID_DAYS,
	QuotationRuleError,
	approval_level,
	approval_problem,
	check_unit_prices,
	months_problem,
)
from sidra_realestate.services.schedule import ScheduleError, down_payment_amount, generate_installments

DOCTYPE = "Sidra Sale Quotation"
QUOTABLE = ("Available", "Reserved")
APPROVAL_FIELDS = ("discount_approved_by", "discount_approved_on")


class SidraSaleQuotation(Document):
	def validate(self):
		if not frappe.db.exists("Customer", self.customer):
			frappe.throw(_("Unknown customer {0}").format(self.customer), frappe.DoesNotExistError)
		if not self.flags.ignore_permissions:
			frappe.get_doc("Customer", self.customer).check_permission("read")
		self.status = "Draft"
		self.validate_dates()
		self.set_units()
		self.set_cash_option()
		self.set_installment_option()
		self.protect_approval()

	def validate_dates(self):
		if getdate(self.quotation_date) > getdate(today()):
			frappe.throw(_("The quotation date cannot be in the future"))
		if not self.valid_until:
			self.valid_until = add_days(self.quotation_date, VALID_DAYS)
		if getdate(self.valid_until) < getdate(self.quotation_date):
			frappe.throw(_("Valid Until cannot be before the quotation date"))

	def set_units(self):
		seen, companies = set(), set()
		for row in self.units:
			if row.unit in seen:
				frappe.throw(_("Unit {0} is listed twice").format(row.unit))
			seen.add(row.unit)
			unit = frappe.get_doc("Sidra Unit", row.unit)
			if not self.flags.ignore_permissions:
				unit.check_permission("read")
			self.check_unit_quotable(unit)
			companies.add(unit.company)
			row.scheme = unit.scheme
			row.listed_price = flt(unit.cash_price, 2)
			if not flt(row.cash_price):
				row.cash_price = row.listed_price
			try:
				check_unit_prices(row.listed_price, row.cash_price, row.installment_price)
			except QuotationRuleError as e:
				frappe.throw(_("Unit {0}: {1}").format(row.unit, _(str(e))))
		if len(companies) != 1:
			frappe.throw(_("All units on a quotation must belong to one Company"))
		self.company = companies.pop()
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")

	def check_unit_quotable(self, unit):
		if unit.status not in QUOTABLE:
			frappe.throw(_("Unit {0} is {1} and cannot be quoted").format(unit.name, unit.status))
		if unit.status == "Reserved":
			reserved_for = frappe.db.get_value("Sidra Reservation", unit.current_reservation, "customer")
			if reserved_for != self.customer:
				frappe.throw(_("Unit {0} is reserved for another customer").format(unit.name))

	def set_cash_option(self):
		self.listed_total = flt(sum(flt(row.listed_price, 2) for row in self.units), 2)
		self.cash_total = flt(sum(flt(row.cash_price, 2) for row in self.units), 2)
		self.discount_amount = flt(self.listed_total - self.cash_total, 2)
		self.discount_approval = approval_level((row.listed_price, row.cash_price) for row in self.units)

	def set_installment_option(self):
		profile = frappe.db.get_value(
			"Sidra Contract Profile",
			self.contract_profile,
			[
				"active",
				"legal_hold",
				"installments",
				"due_day",
				"grace_months",
				"down_payment_type",
				"down_payment_value",
			],
			as_dict=True,
		)
		if not profile or not profile.active:
			frappe.throw(_("Contract profile {0} is not active").format(self.contract_profile))
		if profile.legal_hold:
			frappe.throw(
				_("Contract profile {0} is on legal hold and cannot be quoted").format(self.contract_profile)
			)
		if not cint(self.installments):
			self.installments = profile.installments
		problem = months_problem(self.installments)
		if problem:
			frappe.throw(_(problem))
		self.due_day = profile.due_day
		self.grace_months = profile.grace_months
		self.installment_total = flt(sum(flt(row.installment_price, 2) for row in self.units), 2)
		try:
			down = down_payment_amount(
				self.installment_total, profile.down_payment_type, flt(profile.down_payment_value, 2)
			)
			lines = generate_installments(
				self.installment_total,
				down,
				cint(self.installments),
				getdate(self.quotation_date),
				cint(self.grace_months),
				cint(self.due_day),
			)
		except ScheduleError as e:
			frappe.throw(str(e))
		self.down_payment = flt(down, 2)
		self.balance = flt(self.installment_total - self.down_payment, 2)
		self.set("schedule", [])
		for line in lines:
			self.append(
				"schedule",
				{
					"seq": line.seq,
					"row_type": "Installment",
					"due_date": line.due_date,
					"amount": flt(line.amount, 2),
				},
			)

	def priced_key(self):
		return tuple((row.unit, flt(row.listed_price, 2), flt(row.cash_price, 2)) for row in self.units)

	def protect_approval(self):
		"""Only `approve_discount` records an approval, and it covers exactly the prices approved."""
		if self.flags.approving_discount:
			return
		before = None if self.is_new() else (self.get_doc_before_save() or frappe.get_doc(DOCTYPE, self.name))
		for field in APPROVAL_FIELDS:
			self.set(field, before.get(field) if before else None)
		if self.discount_approval == NO_APPROVAL or (before and before.priced_key() != self.priced_key()):
			self.discount_approved_by = self.discount_approved_on = None

	def before_submit(self):
		if getdate(self.valid_until) < getdate(today()):
			frappe.throw(_("This quotation has already expired; change Valid Until"))
		if self.discount_approval != NO_APPROVAL and not self.discount_approved_on:
			frappe.throw(
				_("The discount of {0} needs approval by the {1} before the quotation is issued").format(
					frappe.format(
						self.discount_amount, {"fieldtype": "Currency", "options": "currency"}, doc=self
					),
					_(self.discount_approval.replace("Sidra ", "")),
				),
				title=_("Discount not approved"),
			)
		self.status = "Issued"

	def on_cancel(self):
		self.db_set("status", "Cancelled")


@frappe.whitelist()
def approve_discount(quotation: str):
	"""SAL-05 / G13: a second person approves the quotation's discount before it is issued."""
	doc = frappe.get_doc(DOCTYPE, quotation)
	doc.check_permission("read")
	if doc.docstatus != 0:
		frappe.throw(_("Only a draft quotation's discount can be approved"))
	doc.flags.approving_discount = True
	doc.flags.ignore_permissions = True  # the approval below is the authority; prices are re-read first
	doc.run_method("validate")
	problem = approval_problem(doc.discount_approval, frappe.session.user, frappe.get_roles(), doc.owner)
	if problem:
		frappe.throw(_(problem), frappe.PermissionError, title=_("Approval not allowed"))
	doc.discount_approved_by = frappe.session.user
	doc.discount_approved_on = now_datetime()
	doc.save(ignore_permissions=True)
	return {"discount_approval": doc.discount_approval, "discount_approved_by": doc.discount_approved_by}


def expire_quotations():
	"""Daily: an issued quotation past its Valid Until date shows as Expired."""
	for name in frappe.get_all(
		DOCTYPE, filters={"docstatus": 1, "status": "Issued", "valid_until": ("<", today())}, pluck="name"
	):
		frappe.db.set_value(DOCTYPE, name, "status", "Expired", update_modified=False)
