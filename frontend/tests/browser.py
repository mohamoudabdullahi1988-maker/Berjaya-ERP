"""Browser checks of the Berjaya screens against synthetic server answers.

Run from the repository root with the Vite dev server on 127.0.0.1:8080:
    (cd frontend && yarn dev --port 8080 --host 127.0.0.1) &
    python3 frontend/tests/browser.py

Every response below is synthetic and lives only in this test: the app itself has no demo or
in-memory data. Screenshots are written to frontend/.verify/ (not committed).
"""

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8080/berjaya"
OUT = Path(__file__).resolve().parent.parent / ".verify"
COMPANY = "Synthetic Homes"
BOOT = {
	"product_name": "Berjaya",
	"user": {"name": "synthetic@example.test", "full_name": "Synthetic Reviewer"},
	"company": COMPANY,
	"nav": [
		{"key": key, "label": key.title()}
		for key in ("dashboard", "properties", "contracts", "collections", "construction", "finance")
	],
	"properties": {"readable_fields": []},
	"currencies": {COMPANY: "USD"},
}

CONTRACTS = {
	"SYN-2026-00055": {
		"name": "SYN-2026-00055",
		"customer": "Synthetic Buyer One",
		"docstatus": 1,
		"currency": "USD",
		"company": COMPANY,
		"source": "External (registered)",
		"contract_type": "Installment",
		"external_reference": "SYN-EXT-0036",
		"signed_on": "2026-01-15",
		"signed_copy": "/private/files/synthetic-agreement.pdf",
		"agreed_price": 10000,
		"down_payment": 800,
		"amount_due": 9200,
		"schedule_total": 9200,
		"units": [{"name": "u1", "unit": "SYN-A-014", "scheme": "Synthetic Gardens"}],
		"schedule": [
			{
				"name": f"s{i}",
				"seq": i,
				"row_type": "Installment",
				"due_date": f"2026-{i:02d}-10",
				"amount": 2300,
			}
			for i in range(2, 6)
		],
	},
	"SYN-2026-00061": {
		"name": "SYN-2026-00061",
		"customer": "Synthetic Buyer Two",
		"docstatus": 0,
		"currency": "USD",
		"company": COMPANY,
		"source": "External (registered)",
		"contract_type": "Installment",
		"external_reference": "SYN-EXT-0041",
		"signed_on": "2026-03-02",
		"signed_copy": "/private/files/synthetic-agreement-2.pdf",
		"agreed_price": 10000,
		"down_payment": 0,
		"amount_due": 10000,
		"schedule_total": 9000,
		"units": [{"name": "u2", "unit": "SYN-B-003", "scheme": "Synthetic Heights"}],
		"schedule": [
			{"name": "t1", "seq": 1, "row_type": "Installment", "due_date": "2026-04-10", "amount": 9000}
		],
	},
	"SYN-2026-00070": {
		"name": "SYN-2026-00070",
		"customer": "Synthetic Buyer Three",
		"docstatus": 1,
		"currency": "USD",
		"company": COMPANY,
		"source": "Generated from profile",
		"contract_type": "Installment",
		"external_reference": None,
		"signed_on": "2026-05-20",
		"signed_copy": None,
		"agreed_price": 24000,
		"down_payment": 4000,
		"amount_due": 20000,
		"schedule_total": 20000,
		"units": [{"name": "u3", "unit": "SYN-C-021", "scheme": "Synthetic Gardens"}],
		"schedule": [],
	},
}
LABELS = [
	("buyer_verified", "Buyer details verified"),
	("property_allocation", "Property allocation checked"),
	("agreement_attached", "External agreement attached"),
	("schedule_validated", "Installment schedule validated"),
	("terms_approval", "Terms approval (Sales Manager)"),
	("registration_finalized", "Registration finalized"),
]
BLOCK_REASON = (
	"The schedule total $ 9,000.00 differs from the amount due $ 10,000.00 by $ 1,000.00; the limit is $ 5.00"
)


def stage(key, label, state, **extra):
	base = {
		"key": key,
		"label": label,
		"state": state,
		"detail": None,
		"responsible": None,
		"timestamp": None,
		"record": None,
		"blocker": None,
		"next_action": None,
		"allowed_actions": [],
		"figures": None,
		"skipped": False,
		"unavailable": False,
	}
	return {**base, **extra}


def timeline(name):
	doc = CONTRACTS[name]
	transaction = {
		"doctype": "Sidra Sale Contract",
		"name": name,
		"status": "Confirmed" if doc["docstatus"] else "Draft",
	}
	if name == "SYN-2026-00070":
		reason = "No workflow is defined yet for this kind of contract."
		return {"transaction": transaction, "supported": False, "reason": reason, "stages": []}
	if name == "SYN-2026-00055":
		stages = [
			stage(k, label, "completed", responsible="Synthetic Manager", timestamp="2026-01-15 10:30:00")
			for k, label in LABELS
		]
	else:
		states = ["completed", "completed", "completed", "blocked", "pending", "pending"]
		stages = [stage(k, label, s) for (k, label), s in zip(LABELS, states, strict=True)]
		stages[0].update(
			skipped=True, detail="Not required for registered contracts. No buyer KYC is on record."
		)
		stages[3]["blocker"] = {"reason": BLOCK_REASON, "action_key": "edit_schedule"}
		stages[4]["detail"] = stages[5]["detail"] = "After: Installment schedule validated"
	return {"transaction": transaction, "supported": True, "reason": None, "stages": stages}


JOB = {
	"name": "SCJ-2026-00007",
	"customer": "Synthetic Client",
	"company": COMPANY,
	"currency": "USD",
	"service_type": "Full Construction",
	"status": "In Progress",
	"site_location": "Synthetic Road, Block 4",
	"plot_number": "SYN-88",
	"engineer": "engineer@example.test",
	"contract_quotation": "SCQ-2026-00003",
	"contract_value": 180000,
	"approved_variations": 6500,
	"current_contract_value": 186500,
	"boq_total": 186500,
	"boq_revision_no": 2,
	"boq": [{"name": "b1"}, {"name": "b2"}],
	"contract_start_date": "2026-02-01",
	"contract_end_date": "2026-12-20",
	"retention_pct": 5,
	"contract_approved_by": "manager@example.test",
	"contract_approved_on": "2026-01-28 14:05:00",
	"stages": [
		{
			"name": "g1",
			"stage_name": "Foundation",
			"status": "Completed",
			"planned_start": "2026-02-01",
			"planned_end": "2026-03-15",
			"actual_end": "2026-03-18",
			"completion_pct": 100,
			"certified": 1,
			"certified_by": "inspector@example.test",
			"certified_on": "2026-03-20 09:00:00",
		},
		{
			"name": "g2",
			"stage_name": "Structure",
			"status": "In Progress",
			"planned_start": "2026-03-16",
			"planned_end": "2026-08-30",
			"actual_end": None,
			"completion_pct": 62.5,
			"certified": 0,
		},
		{
			"name": "g3",
			"stage_name": "Finishes",
			"status": "Planned",
			"planned_start": "2026-09-01",
			"planned_end": "2026-12-20",
			"actual_end": None,
			"completion_pct": 0,
			"certified": 0,
		},
	],
}
CALENDAR = {
	"available": True,
	"month": "2026-11",
	"today": "2026-11-14",
	"currency": "USD",
	"company_id": COMPANY,
	"notice": "Agreed schedule before payment reconciliation. Past due dates are not verified unpaid balances.",
	"summary": {
		"month": {"amount": "6900.00", "count": 3},
		"past_due": {"amount": "2300.00", "count": 1},
		"today": {"amount": "2300.00", "count": 1},
		"upcoming": {"amount": "2300.00", "count": 1},
	},
	"days": [],
	"events": [
		{
			"id": f"e{i}",
			"contract_id": "SYN-2026-00055",
			"external_reference": "SYN-EXT-0036",
			"customer_display": "Synthetic Buyer One",
			"due_date": day,
			"amount": "2300.00",
			"row_type": "Installment",
			"currency": "USD",
			"date_state": state,
		}
		for i, (day, state) in enumerate(
			[("2026-11-05", "past_due"), ("2026-11-14", "today"), ("2026-11-25", "upcoming")]
		)
	],
}
DASHBOARD = {
	"as_of": "2026-11-14T09:15:00+03:00",
	"currency": "USD",
	"payments": {
		"available": True,
		"notice": "Fictional staging data from permitted native invoices and payments; not contract collections.",
		"received": "48250.00",
		"overdue": "7300.00",
		"collection_rate": 86.4,
		"overdue_invoices": 2,
		"aging": [
			{"label": "1–30 days", "amount": "4300.00"},
			{"label": "31–60 days", "amount": "3000.00"},
			{"label": "61–90 days", "amount": "0.00"},
			{"label": "90+ days", "amount": "0.00"},
		],
		"cash_drilldown": {"path": "/app/payment-entry?company=Synthetic"},
		"overdue_drilldown": {"path": "/app/query-report/Accounts%20Receivable?company=Synthetic"},
	},
}
INVOICES = [
	{
		"name": "SYN-SINV-0012",
		"customer": "Synthetic Client",
		"posting_date": "2026-11-02",
		"due_date": "2026-11-30",
		"grand_total": 12500,
		"outstanding_amount": 0,
		"currency": "USD",
		"status": "Paid",
	},
	{
		"name": "SYN-SINV-0009",
		"customer": "Synthetic Client Two",
		"posting_date": "2026-10-01",
		"due_date": "2026-10-20",
		"grand_total": 4300,
		"outstanding_amount": 4300,
		"currency": "USD",
		"status": "Overdue",
	},
]
RECEIPTS = [
	{
		"name": "SYN-PAY-0031",
		"party": "Synthetic Client",
		"posting_date": "2026-11-03",
		"paid_amount": 12500,
		"paid_from_account_currency": "USD",
		"mode_of_payment": "Bank Transfer",
		"reference_no": "SYN-REF-77",
	},
]
JOB_ROW = {
	k: JOB[k]
	for k in (
		"name",
		"customer",
		"service_type",
		"status",
		"site_location",
		"plot_number",
		"engineer",
		"current_contract_value",
		"currency",
		"contract_end_date",
	)
}


def answer(url):
	"""(status, body) for one request; an unknown path fails loudly."""
	parsed = urlparse(url)
	path, query = unquote(parsed.path), parse_qs(parsed.query)
	if path.endswith("frappe.auth.get_logged_user"):
		return 200, {"message": BOOT["user"]["name"]}
	if path.endswith("get_contract_timeline"):
		return 200, {"message": timeline(query["contract"][0])}
	if path.endswith("get_installment_calendar"):
		return 200, {"message": {**CALENDAR, "month": query["month"][0]}}
	if path.endswith("get_dashboard"):
		return 200, {"message": DASHBOARD}
	if path == "/api/resource/Sidra Sale Contract":
		rows = list(CONTRACTS.values())
		term = json.loads(query["or_filters"][0])[0][2].strip("%").lower() if "or_filters" in query else ""
		return 200, {"data": [r for r in rows if term in (r["name"] + r["customer"]).lower()]}
	if path == "/api/resource/Sidra Sale Contract/SYN-DENIED":
		return 403, {"exception": "frappe.exceptions.PermissionError: Not permitted"}
	if path.startswith("/api/resource/Sidra Sale Contract/"):
		return 200, {"data": CONTRACTS[path.rsplit("/", 1)[1]]}
	if path.startswith("/api/resource/Sidra Construction Job/"):
		return 200, {"data": JOB}
	listed = {"Sidra Construction Job": [JOB_ROW], "Sales Invoice": INVOICES, "Payment Entry": RECEIPTS}
	for doctype, rows in listed.items():
		if path == f"/api/v2/document/{doctype}":
			return 200, {"data": rows, "has_next_page": False}
		if path == f"/api/v2/doctype/{doctype}/count":
			return 200, {"data": len(rows)}
	raise AssertionError(f"Unexpected request: {path}")


def check(page, width, name, path, assertions):
	page.goto(BASE + path)
	assertions(page)
	overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
	assert overflow <= 0, f"{name} at {width}px overflows the viewport by {overflow}px"
	page.wait_for_timeout(300)  # let a drawer finish sliding before the picture
	page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
	print(f"PASS {width}px {name}")


def contracts(page):
	expect(page.get_by_role("link", name="SYN-2026-00055")).to_be_visible()
	expect(page.get_by_text("SYN-A-014")).to_be_visible()
	expect(page.get_by_text("Generated from profile")).to_be_visible()


def confirmed(page, width):
	expect(page.get_by_role("heading", name="SYN-2026-00055")).to_be_visible()
	if width < 1100:  # the panel is a drawer on a phone, opened from the Workflow button
		expect(page.get_by_text("stages complete")).not_to_be_visible()
		page.get_by_role("button", name="Open workflow").click()
	expect(page.get_by_text("6 of 6 stages complete")).to_be_visible()
	expect(page.locator(".stage--completed")).to_have_count(6)
	expect(page.get_by_text("USD 9,200.00").first).to_be_visible()
	page.get_by_role("button", name="Refresh").click()
	expect(page.get_by_text("6 of 6 stages complete")).to_be_visible()


def blocked(page, width):
	expect(page.get_by_role("heading", name="SYN-2026-00061")).to_be_visible()
	if width < 1100:
		page.get_by_role("button", name="Open workflow").click()
	expect(page.get_by_text("2 of 6 stages complete")).to_be_visible()  # the skipped stage is not counted
	expect(page.get_by_text("Not verified - informational")).to_be_visible()
	expect(page.locator(".stage--skipped .lucide-circle-minus")).to_have_count(1)
	expect(page.get_by_text(BLOCK_REASON)).to_be_visible()
	expect(page.locator(".flow__spin")).to_have_count(0)  # waiting on a person is not a spinner


def unsupported(page, width):
	expect(page.get_by_role("heading", name="SYN-2026-00070")).to_be_visible()
	if width < 1100:
		page.get_by_role("button", name="Open workflow").click()
	expect(page.get_by_text("No workflow is defined yet for this kind of contract.")).to_be_visible()
	expect(page.locator(".stage")).to_have_count(0)


def denied(page):
	expect(page.get_by_text("This contract is unavailable to you")).to_be_visible()
	expect(page.get_by_role("button", name=re.compile("workflow"))).to_have_count(0)


def collections(page):
	expect(page.get_by_role("heading", name="Collections")).to_be_visible()
	expect(page.get_by_text("USD 6,900.00")).to_be_visible()
	expect(page.get_by_text("Past due dates are not verified unpaid balances.")).to_be_visible()
	expect(page.locator("tbody tr")).to_have_count(3)
	expect(page.get_by_text("Overdue")).to_have_count(0)


def construction(page):
	expect(page.get_by_role("link", name="SCJ-2026-00007")).to_be_visible()
	expect(page.get_by_text("USD 186,500.00")).to_be_visible()


def job(page):
	expect(page.get_by_role("heading", name="SCJ-2026-00007")).to_be_visible()
	expect(page.get_by_text("1 of 3 stages recorded as completed.")).to_be_visible()
	expect(page.get_by_text("62.5%")).to_be_visible()
	expect(page.get_by_role("button", name=re.compile("workflow"))).to_have_count(
		0
	)  # no panel, no dead button


def finance(page):
	expect(page.get_by_text("USD 48,250.00")).to_be_visible()
	expect(page.get_by_text("86.4%")).to_be_visible()
	expect(page.get_by_role("link", name="SYN-SINV-0012")).to_be_visible()
	page.get_by_role("tab", name="Receipts").click()
	expect(page.get_by_role("link", name="SYN-PAY-0031")).to_be_visible()


def main():
	OUT.mkdir(exist_ok=True)
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True)
		for width in (1440, 390):
			page = browser.new_page(viewport={"width": width, "height": 900})
			errors = []
			page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
			page.add_init_script("window.berjaya_boot = " + json.dumps(BOOT))

			def respond(route):
				status, body = answer(route.request.url)
				route.fulfill(status=status, json=body)

			page.route("**/api/**", respond)
			check(page, width, "contracts", "/contracts", contracts)
			check(
				page,
				width,
				"contract-confirmed",
				"/contracts/SYN-2026-00055",
				lambda pg, w=width: confirmed(pg, w),
			)
			check(
				page,
				width,
				"contract-blocked",
				"/contracts/SYN-2026-00061",
				lambda pg, w=width: blocked(pg, w),
			)
			check(
				page,
				width,
				"contract-no-workflow",
				"/contracts/SYN-2026-00070",
				lambda pg, w=width: unsupported(pg, w),
			)
			check(page, width, "contract-denied", "/contracts/SYN-DENIED", denied)
			check(page, width, "collections", "/collections", collections)
			check(page, width, "construction", "/construction", construction)
			check(page, width, "construction-job", "/construction/SCJ-2026-00007", job)
			check(page, width, "finance", "/finance", finance)
			assert not errors, errors
			page.close()
		browser.close()
	print("All browser checks passed.")


if __name__ == "__main__":
	main()
