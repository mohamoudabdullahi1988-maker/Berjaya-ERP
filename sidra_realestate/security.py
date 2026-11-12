"""Read-only bench audit. Intentionally NOT whitelisted or installed as a web/debug route.

Reports effective configuration without serializing site_config, secrets, users or records.
Transport enforcement, deployed dependencies and external audit retention need operator evidence.
"""

import re

import frappe


def _enabled(value):
	return value not in (None, False, 0, "", "0")


def audit_site():
	"""Run through `bench --site <site> execute sidra_realestate.security.audit_site`."""
	frappe.only_for("System Manager")
	checks = []

	def add(control, status):
		checks.append({"control": control, "status": status})

	for flag in (
		"developer_mode",
		"ignore_csrf",
		"allow_tests",
		"server_script_enabled",
		"sidra_allow_demo_data",
		"sidra_finance_demo_site",
		"sidra_allow_finance_demo_vouchers",
	):
		add(flag + "_disabled", "fail" if _enabled(frappe.conf.get(flag)) else "pass")

	host = frappe.conf.get("host_name")
	add(
		"declared_https_origin", "pass" if isinstance(host, str) and host.startswith("https://") else "review"
	)
	cors = frappe.conf.get("allow_cors")
	if not cors:
		add("cors", "pass")  # Same-origin application: no cross-origin grants needed.
	elif (
		isinstance(cors, str)
		and "*" in cors
		or isinstance(cors, (list, tuple))
		and any("*" in str(origin) for origin in cors)
	):
		add("cors", "fail")
	else:
		add("cors", "review")  # Verify every configured origin with the site owner.

	limit = frappe.conf.get("rate_limit")
	configured = isinstance(limit, dict) and all(
		isinstance(limit.get(key), (int, float)) and not isinstance(limit[key], bool) and limit[key] > 0
		for key in ("limit", "window")
	)
	add("frappe_request_time_budget", "pass" if configured else "review")
	settings = frappe.get_single("System Settings")
	add("two_factor_authentication", "pass" if settings.get("enable_two_factor_auth") else "review")
	add("password_policy", "pass" if settings.get("enable_password_policy") else "review")
	expiry = str(settings.get("session_expiry") or "")
	valid_expiry = bool(re.fullmatch(r"\d+:[0-5]\d", expiry)) and any(int(part) for part in expiry.split(":"))
	add("finite_session_expiry", "pass" if valid_expiry else "review")
	for doctype in ("Sidra Sale Contract", "Sidra Unit", "Sidra Reservation", "Sidra Contract Import"):
		add(doctype + "_change_tracking", "pass" if frappe.get_meta(doctype).track_changes else "review")

	return {
		"checks": checks,
		"limitations": [
			"Configuration inspection is not proof of external HTTPS, cookie, CORS or rate-limit behavior.",
			"Pass means the named setting is present, not that role assignments or deployed versions were certified.",
			"Frappe change tracking is not tamper-proof; external restricted/immutable audit retention needs verification.",
			"No model vendor, training policy, container, firewall, backup or installed-app assurance is inferred.",
		],
	}
