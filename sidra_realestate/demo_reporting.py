"""Manual staging demo population and read-only verification for staff reports."""

import frappe

from sidra_realestate.api.staff_dashboard import get_dashboard
from sidra_realestate.finance_demo import COMPANY, create_finance_demo_data, verify_finance_demo


def populate_and_verify():
	"""Use the existing guarded loader; never create a second accounting dataset."""
	data = create_finance_demo_data()
	ledger = verify_finance_demo()
	dashboard = get_dashboard(company=COMPANY, period="last_90_days")
	payments = dashboard["payments"]
	if not payments.get("available"):
		frappe.throw(
			"Posted demo vouchers exist but payment data is unavailable: " + payments.get("reason", "unknown")
		)
	return {
		"company_to_select": COMPANY,
		"report_from_date": data["from_date"],
		"report_to_date": data["as_of"],
		"created": data["created"],
		"ledger_verification": ledger,
		"contracts": dashboard["contracts"],
		"sales_activity": dashboard["sales"],
		"payments": payments,
		"construction": dashboard["jobs"],
		"summary": dashboard["summary"],
		"reports": data["reports"],
		"note": "Test site only (decision G13): the fictional entries are in this Company. "
		"Choose it in every report. Reruns retain original dates; use the returned report date range.",
	}
