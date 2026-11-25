"""ERPNext Projects and Tasks for the pilot's fictional construction jobs (decision G37, 25 Nov 2026).

The pilot dataset (`pilot_demo.py`, G16) creates construction jobs but no ERPNext Project, so the
Desk Projects module was empty on the test site. This loader once gives every pilot job its
Project and one Task per stage, with the same link as "Create → Project" on a job
(`services/construction_projects.create_project`). Only jobs listed in the pilot's own manifest are
touched; a job already linked to a Project, closed, cancelled or without stages is skipped and
listed. Nothing is posted, approved or changed on a contract.
The guards are the pilot's: Administrator only, the three staging flags, the pilot's manifest must
exist, one transaction with full rollback, a private manifest of its own, and a rerun that changes
nothing.

	bench --site <staging> execute sidra_realestate.pilot_projects.create_pilot_projects
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import frappe

from sidra_realestate.finance_demo import COMPANY
from sidra_realestate.pilot_demo import MANIFEST as PILOT_MANIFEST
from sidra_realestate.pilot_demo import SCHEMA as PILOT_SCHEMA
from sidra_realestate.pilot_demo import _guard, _read_manifest
from sidra_realestate.services.construction import CLOSED_STATUSES
from sidra_realestate.services.construction_projects import create_project

MANIFEST = "sidra-pilot-projects-v1.json"
SCHEMA = 1
JOB = "Sidra Construction Job"


def create_pilot_projects():
	"""Create once and commit; a rerun returns the manifest and changes nothing."""
	_guard()
	pilot = _read_manifest(PILOT_MANIFEST, PILOT_SCHEMA, required=False)
	if not pilot:
		frappe.throw("Refusing: load the pilot dataset first (pilot_demo.create_pilot_demo_data).")
	existing = _read_manifest(MANIFEST, SCHEMA, required=False)
	if existing:
		return {**existing, "created": False}
	try:
		data = _create(pilot)
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": MANIFEST,
				"content": json.dumps(data, indent=2, default=str),
				"is_private": 1,
				"attached_to_doctype": "Company",
				"attached_to_name": COMPANY,
			}
		).insert()
	except Exception:
		frappe.db.rollback()
		raise
	frappe.db.commit()
	return {**data, "created": True}


def _create(pilot):
	today = datetime.now(ZoneInfo("Africa/Mogadishu")).date()
	projects, skipped = {}, {}
	for name in pilot.get("jobs", {}).get("jobs", []):
		job = frappe.db.get_value(JOB, name, ["company", "status", "project"], as_dict=True)
		if not job:
			skipped[name] = "missing"
		elif job.company != COMPANY:
			skipped[name] = "other Company"
		elif job.project:
			skipped[name] = f"already linked to {job.project}"
		elif job.status in CLOSED_STATUSES:
			skipped[name] = job.status
		elif not frappe.db.exists("Sidra Project Stage", {"parent": name, "parenttype": JOB}):
			skipped[name] = "no stages"
		else:
			projects[name] = create_project(name)["project"]
	tasks = frappe.db.count("Task", {"project": ["in", list(projects.values())]}) if projects else 0
	return {
		"schema": SCHEMA,
		"company": COMPANY,
		"as_of": str(today),
		"projects": projects,
		"tasks": tasks,
		"skipped": skipped,
	}
