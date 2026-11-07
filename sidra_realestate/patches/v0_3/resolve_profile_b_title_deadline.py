"""Decision D4: set Profile B's title deadline to 20 days and lift its legal hold.

Mohamoud, 6 Nov 2026, issue #13; docs/CONTRACT-CAPTURE_v0.3.md §6.3. The 14 days in Contract B's
clause 6 is a typo. The profile is changed only while it still has the values the install seeded
(legal hold on, title deadline 0). If management has already edited it, it is left alone.

Contracts already saved keep their own frozen terms (INS-20): a draft saved while Profile B was on
hold still carries the hold in its snapshot and needs Revise Draft to pick up the new terms.
"""

import frappe
from frappe.utils import cint

from sidra_realestate.install import PROFILE_B_TITLE_DEADLINE_DAYS, PROFILE_B_TITLE_DEADLINE_NOTE

PROFILE = "Profile B"


def execute():
	if not frappe.db.exists("Sidra Contract Profile", PROFILE):
		return

	current = frappe.db.get_value(
		"Sidra Contract Profile", PROFILE, ["legal_hold", "title_deadline_days"], as_dict=True
	)
	if not (cint(current.legal_hold) == 1 and cint(current.title_deadline_days) == 0):
		print(
			f"{PROFILE} was already changed by management (legal hold {current.legal_hold}, "
			f"title deadline {current.title_deadline_days} days); D4 patch left it unchanged."
		)
		return

	frappe.db.set_value(
		"Sidra Contract Profile",
		PROFILE,
		{
			"title_deadline_days": PROFILE_B_TITLE_DEADLINE_DAYS,
			"title_deadline_note": PROFILE_B_TITLE_DEADLINE_NOTE,
			"legal_hold": 0,
			"legal_hold_reason": None,
		},
	)
	frappe.get_doc("Sidra Contract Profile", PROFILE).add_comment(
		"Comment",
		"Decision D4 (Mohamoud, 6 Nov 2026, issue #13): title deadline set to 20 days and legal hold "
		"lifted. The 14 days in Contract B is a typo. Saved contracts keep their frozen terms.",
	)
