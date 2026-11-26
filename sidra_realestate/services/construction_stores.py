# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Decision G42: a store (ERPNext Warehouse) per house.

- Each construction job gets its own Warehouse under the Company's *Construction sites* group,
  made with its Project ("Create → Project") or on its own ("Create → Site store"), and linked
  both ways: the job's `warehouse` field and the Warehouse's `sidra_construction_job`.
- Material Requests for a house can be raised now; they post nothing.
- Stock moves into or out of a house store post to the ledger, and the finance posting gate is still
  open: until Finance approves the stock accounts, submitting a Stock Entry, Purchase Receipt,
  Delivery Note, Stock Reconciliation, or a Purchase / Sales Invoice that updates stock, with a
  house store on any line, is refused (`refuse_site_stock_move`).
"""

import frappe
from frappe import _

from sidra_realestate.services.construction import CLOSED_STATUSES
from sidra_realestate.services.construction_jobs import lock_job

JOB = "Sidra Construction Job"
GROUP = "Construction sites"
WAREHOUSE_FIELDS = (
	"warehouse",
	"s_warehouse",
	"t_warehouse",
	"set_warehouse",
	"set_from_warehouse",
	"set_target_warehouse",
	"from_warehouse",
	"target_warehouse",
	"rejected_warehouse",
)

CUSTOM_FIELDS = {
	"Warehouse": [
		{
			"fieldname": "sidra_construction_job",
			"label": "Construction Job",
			"fieldtype": "Link",
			"options": JOB,
			"insert_after": "warehouse_name",
			"read_only": 1,
			"search_index": 1,
		}
	]
}


def ensure_store_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)


def group_for(company):
	"""The Company's *Construction sites* group warehouse, made under its root on first use."""
	existing = frappe.db.get_value(
		"Warehouse", {"company": company, "warehouse_name": GROUP, "is_group": 1}, "name"
	)
	if existing:
		return existing
	root = frappe.db.get_value(
		"Warehouse",
		{"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]},
		"name",
	)
	doc = frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": GROUP,
			"company": company,
			"is_group": 1,
			"parent_warehouse": root,
		}
	)
	doc.flags.ignore_permissions = True
	return doc.insert().name


def make_store(doc):
	"""The house store for job `doc` (a Sidra Construction Job). Does not save the job."""
	place = doc.plot_number or doc.site_location or doc.customer
	store = frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": f"{doc.name} {place}"[:120],
			"company": doc.company,
			"is_group": 0,
			"parent_warehouse": group_for(doc.company),
			"sidra_construction_job": doc.name,
		}
	)
	store.flags.ignore_permissions = True  # the job's write permission was checked by the caller
	return store.insert().name


@frappe.whitelist(methods=["POST"])
def create_site_store(job: str):
	"""Create the house store for a job that has none (Project Managers)."""
	locked = lock_job(job)
	doc = frappe.get_doc(JOB, job)
	doc.check_permission("write")
	if locked.status in CLOSED_STATUSES:
		frappe.throw(_("Job {0} is {1}; no store can be created").format(job, locked.status))
	if doc.warehouse:
		frappe.throw(_("Job {0} already has store {1}").format(job, doc.warehouse))
	doc.warehouse = make_store(doc)
	doc.save()
	doc.add_comment("Info", _("Site store {0} created").format(doc.warehouse))
	return {"warehouse": doc.warehouse}


def backfill_site_stores(company=None):
	"""A store for every open job that has a Project but no store (System Manager, idempotent).

	For adopting G42 where jobs already have Projects:
		bench --site <site> execute sidra_realestate.services.construction_stores.backfill_site_stores
	"""
	frappe.only_for("System Manager")
	filters = {
		"project": ["is", "set"],
		"warehouse": ["is", "not set"],
		"status": ["not in", CLOSED_STATUSES],
	}
	if company:
		filters["company"] = company
	made = {}
	for job in frappe.get_all(JOB, filters=filters, pluck="name", order_by="creation asc"):
		made[job] = create_site_store(job)["warehouse"]
	frappe.db.commit()
	print(made)
	return made


def refuse_site_stock_move(doc, method=None):
	"""before_submit on stock vouchers: no ledger-posting move into or out of a house store yet."""
	if doc.doctype in ("Purchase Invoice", "Sales Invoice") and not doc.get("update_stock"):
		return
	stores = set()
	rows = [doc, *doc.get("items", [])]
	for row in rows:
		for field in WAREHOUSE_FIELDS:
			value = row.get(field)
			if value:
				stores.add(value)
	if not stores:
		return
	site = frappe.get_all(
		"Warehouse",
		filters={"name": ["in", list(stores)], "sidra_construction_job": ["is", "set"]},
		pluck="name",
	)
	if site:
		frappe.throw(
			_(
				"Stock moves for house stores ({0}) wait until Finance approves the stock accounts "
				"(decision G42). Raise a Material Request for now."
			).format(", ".join(sorted(site))),
			title=_("House store not open for stock moves yet"),
		)
