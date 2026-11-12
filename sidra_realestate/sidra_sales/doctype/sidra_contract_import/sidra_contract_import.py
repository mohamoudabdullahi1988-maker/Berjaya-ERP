# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Import live contracts and their schedules from a spreadsheet (decision G5; D8; CC-01, CC-05).

Each contract in the file becomes a draft registered (External) Sidra Sale Contract with its
own schedule. Nothing is confirmed: confirmation still needs the original signed document and a
Sales Manager (D5, D7). Payments made to date are not imported (D8).

Validate runs the whole import, with every contract check, and then rolls it back. Import does
the same and keeps the result only if every contract is valid (all or nothing). A reference
that already exists for the Company is skipped, so a file can be imported again safely.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from sidra_realestate.services.contract_import import parse_rows

SAVEPOINT = "sidra_contract_import"


class SidraContractImport(Document):
	def read_file(self):
		self.check_permission("write")
		if not self.import_file:
			frappe.throw(_("Attach the spreadsheet first"))
		# get_doc/get_content do not check read permissions themselves. A guessed File URL
		# must never turn this importer into a reader for another record's attachment.
		file_name = frappe.db.get_value(
			"File",
			{
				"file_url": self.import_file,
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"attached_to_field": "import_file",
			},
			"name",
		)
		if not file_name:
			frappe.throw(
				_("Upload the spreadsheet to this import's Spreadsheet field first"), frappe.PermissionError
			)
		file_doc = frappe.get_doc("File", file_name)
		file_doc.check_permission("read")
		if not file_doc.is_private or not (file_doc.file_url or "").startswith("/private/files/"):
			frappe.throw(_("The import spreadsheet must be a private local file"), frappe.PermissionError)
		name = (file_doc.file_name or self.import_file).lower()
		if not name.endswith((".csv", ".xlsx")):
			frappe.throw(_("Use a .csv or .xlsx file"))
		content = file_doc.get_content()
		if name.endswith(".xlsx"):
			from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

			return read_xlsx_file_from_attached_file(fcontent=content)
		if name.endswith(".csv"):
			from frappe.utils.csvutils import read_csv_content

			return read_csv_content(content)
		frappe.throw(_("Use a .csv or .xlsx file"))

	def process(self, commit: bool) -> dict:
		contracts, errors = parse_rows(self.read_file())
		created, skipped = [], []
		if not errors:
			frappe.db.savepoint(SAVEPOINT)
			for c in contracts:
				if frappe.db.exists(
					"Sidra Sale Contract",
					{"external_reference": c.external_reference, "company": self.company},
				):
					skipped.append(c.external_reference)
					continue
				try:
					created.append(self.create_contract(c))
				except Exception as e:  # report every contract, not only the first failure
					frappe.clear_messages()
					errors.append(
						f"{c.external_reference} (row {c.first_row}): {frappe.utils.strip_html(str(e))}"
					)
			if errors or not commit:
				frappe.db.rollback(save_point=SAVEPOINT)
				created_names = []
			else:
				created_names = created

		ok = not errors
		self.contracts_found = len(contracts)
		self.contracts_created = len(created) if (ok and commit) else 0
		self.status = ("Imported" if commit else "Validated") if ok else "Failed"
		lines = []
		if ok:
			lines.append(
				(
					_("Created {0} draft contract(s).") if commit else _("{0} contract(s) can be imported.")
				).format(len(created))
			)
		if skipped:
			lines.append(_("Skipped, already registered: {0}").format(", ".join(skipped)))
		lines += errors
		if ok and commit:
			lines += [_("Created: {0}").format(", ".join(created_names))] if created_names else []
		self.log = "\n".join(lines)
		self.save()
		return {"status": self.status, "log": self.log}

	def create_contract(self, c) -> str:
		if not frappe.db.exists("Customer", c.customer):
			if not self.create_missing_customers:
				raise frappe.ValidationError(_("Customer {0} does not exist").format(c.customer))
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": c.customer,
					"customer_type": "Individual",
					"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group")
					or "Individual",
					"territory": frappe.db.get_single_value("Selling Settings", "territory")
					or "All Territories",
				}
			).insert()
		for unit, _price in c.units:
			if not frappe.db.exists("Sidra Unit", unit):
				raise frappe.ValidationError(_("Unit {0} does not exist").format(unit))
		doc = frappe.get_doc(
			{
				"doctype": "Sidra Sale Contract",
				"contract_type": "Installment",
				"source": "External (registered)",
				"external_reference": c.external_reference,
				"customer": frappe.db.get_value("Customer", {"customer_name": c.customer}, "name")
				or c.customer,
				"company": self.company,
				"signed_on": c.signed_on,
				"agreed_price": flt(c.agreed_price, 2),
				"down_payment_mode": c.down_payment_mode,
				"down_payment": flt(c.down_payment, 2),
				"terms_summary": c.terms_summary or None,
				"units": [{"unit": unit, "allocated_price": flt(price, 2)} for unit, price in c.units],
				"schedule": [
					{"row_type": t, "due_date": d, "amount": flt(a, 2), "description": desc or None}
					for t, d, a, desc in c.schedule
				],
			}
		)
		doc.flags.from_import = True
		doc.insert()
		return doc.name


@frappe.whitelist(methods=["POST"])
def validate_import(name: str) -> dict:
	doc = frappe.get_doc("Sidra Contract Import", name)
	doc.check_permission("write")
	return doc.process(commit=False)


@frappe.whitelist(methods=["POST"])
def run_import(name: str) -> dict:
	doc = frappe.get_doc("Sidra Contract Import", name)
	doc.check_permission("write")
	return doc.process(commit=True)
