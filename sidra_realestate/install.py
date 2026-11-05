"""Install and migrate hooks.

Creates Profile A and Profile B (handover v1.0 §4.1; SRS v1.6 §5.5; SRS v2.0 §3.3) when
they are missing. Existing profiles are never overwritten: management edits them, and a
signed contract keeps its own frozen copy (INS-20).
"""

import frappe

PROFILE_B_HOLD_REASON = (
	"SRS v2.0 §1.4 and §9.1: Contract B gives the title deadline as 20 days in clause 4 and "
	"14 days in clause 6. Contracts on this profile can be drafted but not submitted until "
	"Sidra resolves the conflict and sets the deadline."
)

PROFILES = [
	{
		"profile_name": "Profile A",
		"is_default": 1,
		"active": 1,
		"legal_hold": 0,
		"installments": 14,
		"due_day": 5,
		"grace_months": 0,
		"down_payment_type": "None",
		"down_payment_value": 0,
		"markup_rate": 0,
		"early_payment": "Reduce Last Installments",
		"penalty_type": "Per Day Capped",
		"penalty_per_day": 5,
		"penalty_monthly_cap": 150,
		"notice_days": 0,
		"default_trigger_missed": 2,
		"refund_retention_type": "One Installment",
		"title_deadline_days": 20,
		"title_penalty_type": "Per Day",
		"title_penalty_amount": 5,
		"title_refund_after_days": 0,
	},
	{
		"profile_name": "Profile B",
		"is_default": 0,
		"active": 1,
		"legal_hold": 1,
		"legal_hold_reason": PROFILE_B_HOLD_REASON,
		"installments": 24,
		"due_day": 10,
		"grace_months": 3,
		"down_payment_type": "Fixed",
		"down_payment_value": 3000,
		"markup_rate": 0,
		"early_payment": "Reduce Last Installments",
		"penalty_type": "Fixed After Notice",
		"penalty_fixed_amount": 100,
		"notice_days": 15,
		"default_trigger_missed": 0,
		"refund_retention_type": "None",
		"title_deadline_days": 0,
		"title_deadline_note": "Unresolved: 20 days (clause 4) or 14 days (clause 6).",
		"title_penalty_type": "Per Month",
		"title_penalty_amount": 220,
		"title_refund_after_days": 90,
		"title_refund_compensation_pct": 10,
	},
]


# SAL-20 and SRS v1.6 §5.5. Wording is supplied and approved by Sidra (issue #8); none is invented here.
CLAUSES = [
	("RESTRICTIONS", "Neighbourhood restrictions"),
	("INSOLVENCY", "Insolvency protection for the buyer"),
	("TITLE-COSTS", "Title costs paid by the buyer"),
	("BEACON", "Beacon / foundation at the lowest of three quotes"),
	("FIRST-RIGHT", "Sidra's first right to design and build"),
]


def after_install():
	ensure_contract_profiles()
	ensure_contract_clauses()


def after_migrate():
	ensure_contract_profiles()
	ensure_contract_clauses()


def ensure_contract_clauses():
	"""Create the clause records (no wording, not approved) when missing. Never overwrites."""
	for code, title in CLAUSES:
		if not frappe.db.exists("Sidra Contract Clause", code):
			frappe.get_doc(
				{"doctype": "Sidra Contract Clause", "clause_code": code, "title": title, "active": 1}
			).insert(ignore_permissions=True)


def ensure_contract_profiles():
	for values in PROFILES:
		if frappe.db.exists("Sidra Contract Profile", values["profile_name"]):
			continue
		doc = frappe.new_doc("Sidra Contract Profile")
		doc.update(values)
		doc.flags.seeding = True
		doc.insert(ignore_permissions=True)
