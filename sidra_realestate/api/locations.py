"""Staff plot/site location API (clients/staff/docs/API-CONTRACT.md, "Plot and site location API").

Integrated from Codex's adapter (clients/staff/integration/...). The `sidra_location` Geolocation
field is part of the Sidra Unit and Sidra Construction Job DocTypes, so `install_fields` finds it
and changes nothing. Only that field changes here; no reservation, price, BOQ, contract or
accounting logic runs.
"""

import re

import frappe
from frappe import _
from frappe.utils import get_datetime

from .location_geometry import extract_point, feature_collection, kml, legacy_point, links, point

ALLOWED = ("Sidra Unit", "Sidra Construction Job")
FIELD = "sidra_location"


def _document(doctype, name, permission="read", lock=False):
	if doctype not in ALLOWED:
		frappe.throw(
			_("Locations support Sidra Unit and Sidra Construction Job only"), frappe.PermissionError
		)
	if not isinstance(name, str) or not name.strip() or len(name) > 140:
		frappe.throw(_("A saved record name is required"))
	doc = frappe.get_doc(doctype, name, for_update=lock)
	doc.check_permission(permission)
	return doc


def _result(doc):
	configured = doc.meta.has_field(FIELD)
	raw = doc.get(FIELD) if configured else None
	saved = extract_point(raw)
	source = "geolocation" if saved else None
	if not raw and doc.doctype == "Sidra Construction Job":
		saved = legacy_point(doc.get("gps"))
		if saved:
			source = "legacy_gps"
	return dict(
		doctype=doc.doctype,
		name=doc.name,
		latitude=saved[0] if saved else None,
		longitude=saved[1] if saved else None,
		source=source,
		configured=configured,
		unsupported_geometry=bool(raw and not saved),
		modified=str(doc.modified),
		can_write=bool(configured and doc.docstatus == 0 and doc.has_permission("write")),
		links=links(*saved) if saved else None,
	)


@frappe.whitelist(methods=["GET"])
def get_location(doctype, name):
	return _result(_document(doctype, name))


@frappe.whitelist(methods=["POST"])
def set_location(doctype, name, latitude, longitude, expected_modified):
	# Permission and Company User Permissions are checked on the actual parent document.
	doc = _document(doctype, name, "write", lock=True)
	if doc.docstatus != 0:
		frappe.throw(_("Submitted or cancelled records cannot have their location changed"))
	if not doc.meta.has_field(FIELD):
		frappe.throw(_("The location field is not installed; ask the server administrator"))
	if not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified):
		frappe.throw(
			_("This record changed. Reload its location before saving."), frappe.TimestampMismatchError
		)
	if doc.get(FIELD) and not extract_point(doc.get(FIELD)):
		frappe.throw(
			_(
				"Existing non-point geometry was preserved. Ask the administrator to select a dedicated pin field."
			)
		)
	try:
		lat, lng = point(latitude, longitude)
	except ValueError, TypeError:
		frappe.throw(_("Enter valid latitude (-90 to 90) and longitude (-180 to 180)"))
	# Only this validated Custom Field changes. Avoid rerunning unrelated BOQ/price calculations.
	doc.db_set(FIELD, feature_collection(lat, lng))
	doc.add_comment("Info", _("Location pin updated"))
	doc.notify_update()
	return _result(doc)


@frappe.whitelist(methods=["GET"])
def export_kml(doctype, name):
	doc = _document(doctype, name)
	result = _result(doc)
	if result["latitude"] is None:
		frappe.throw(_("There is no recorded point to export"))
	frappe.response.update(
		type="download",
		filename=re.sub(r"[^A-Za-z0-9._-]", "_", doc.name)[:80] + ".kml",
		filecontent=kml(doc.name, result["latitude"], result["longitude"]),
		content_type="application/vnd.google-earth.kml+xml",
		display_content_as="attachment",
	)


def install_fields():
	"""Administrator-run once. No external app and no core or existing GPS-field changes."""
	frappe.only_for("System Manager")
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	missing = {}
	for doctype in ALLOWED:
		meta = frappe.get_meta(doctype)
		existing = meta.get_field(FIELD)
		if existing:
			if existing.fieldtype != "Geolocation":
				frappe.throw(_("Existing {0}.{1} has another type; no changes made").format(doctype, FIELD))
			continue
		missing[doctype] = [
			dict(
				fieldname=FIELD,
				label="Plot / Site Location",
				fieldtype="Geolocation",
				insert_after="title_deed_ref" if doctype == "Sidra Unit" else "gps",
				description="Shared location pin. Existing survey documents and GPS text are preserved.",
			)
		]
	if missing:
		create_custom_fields(missing)
