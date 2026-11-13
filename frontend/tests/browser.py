"""Isolated browser component tests; all synthetic responses are confined to tests."""
import json
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width in (1440, 390):
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.add_init_script('window.berjaya_boot = ' + json.dumps({"user": {"name": "synthetic@example.test", "full_name": "Synthetic Reviewer"}, "company": "Synthetic Company", "nav": [{"key": "contracts", "label": "Contracts"}]}))
        doc = {"name": "SYNTHETIC-001", "customer": "Synthetic Buyer", "docstatus": 0, "currency": "USD", "agreed_price": 1000, "down_payment": 100, "amount_due": 900, "schedule_total": 875, "units": [{"name": "row-1", "unit": "TEST-UNIT", "scheme": "Test Scheme"}], "schedule": [{"name": "schedule-1", "seq": 1, "due_date": "2026-12-01", "amount": 875}]}
        stages = [{"key": "buyer", "label": "Buyer checked", "state": "completed"}, {"key": "schedule", "label": "Schedule validation", "state": "blocked", "blocker": {"reason": "Synthetic schedule difference: 25.00"}}, {"key": "approval", "label": "Approval", "state": "pending"}]
        def respond(route):
            if '/api/method/' in route.request.url:
                body = {"message": {"transaction": {"name": doc['name']}, "supported": True, "stages": stages}}
            else:
                body = {"data": doc}
            route.fulfill(json=body)
        page.route('**/api/**', respond)
        page.goto('http://127.0.0.1:8080/berjaya/contracts/SYNTHETIC-001')
        expect(page.get_by_role('heading', name='SYNTHETIC-001')).to_be_visible()
        page.get_by_role('button', name='Open workflow', exact=True).click()
        expect(page.get_by_text('1 of 3 stages complete')).to_be_visible()
        expect(page.get_by_text('Synthetic schedule difference: 25.00')).to_be_visible()
        page.get_by_role('button', name='Refresh workflow').click()
        expect(page.get_by_text('1 of 3 stages complete')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows viewport'
        assert not errors, errors
        page.screenshot(path=f'frontend/.verify/contract-{width}.png', full_page=True)
        page.close()
        print(f'PASS: {width}px contract, workflow, refresh, no horizontal overflow or browser errors')
    browser.close()
