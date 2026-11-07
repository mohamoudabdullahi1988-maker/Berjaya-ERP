"""Pure point geometry and Google URL helpers. No geocoding, keys or network calls."""

import json
import math
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring


def point(latitude, longitude):
	if any(
		v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip())
		for v in (latitude, longitude)
	):
		raise ValueError("Latitude and longitude are required")
	lat, lng = float(latitude), float(longitude)
	if not math.isfinite(lat) or not math.isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180:
		raise ValueError("Latitude must be -90 to 90 and longitude -180 to 180")
	return lat, lng


def feature_collection(latitude, longitude):
	lat, lng = point(latitude, longitude)
	return json.dumps(
		{
			"type": "FeatureCollection",
			"features": [
				{
					"type": "Feature",
					"properties": {},
					"geometry": {"type": "Point", "coordinates": [lng, lat]},
				}
			],
		},
		separators=(",", ":"),
	)


def extract_point(value):
	if not value:
		return None
	try:
		obj = json.loads(value) if isinstance(value, str) else value
		if obj.get("type") == "FeatureCollection":
			if len(obj.get("features", [])) != 1:
				return None
			obj = obj["features"][0]
		if obj.get("type") == "Feature":
			obj = obj["geometry"]
		if obj.get("type") != "Point":
			return None
		lng, lat = obj["coordinates"][:2]
		return point(lat, lng)
	except ValueError, TypeError, KeyError, IndexError, AttributeError:
		return None


def legacy_point(value):
	"""Strict legacy 'latitude, longitude' only; do not guess addresses or rewrite GPS text."""
	if not value or not isinstance(value, str) or len(value.split(",")) != 2:
		return None
	try:
		return point(*value.split(","))
	except ValueError, TypeError:
		return None


def links(latitude, longitude):
	lat, lng = point(latitude, longitude)
	query = quote(f"{lat},{lng}", safe="")
	return {
		"maps": f"https://www.google.com/maps/search/?api=1&query={query}",
		"earth": f"https://earth.google.com/web/search/{query}",
	}


def kml(name, latitude, longitude):
	lat, lng = point(latitude, longitude)
	root = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
	place = SubElement(root, "Placemark")
	SubElement(place, "name").text = str(name)
	SubElement(place, "description").text = "Recorded point only; not surveyed parcel boundaries."
	SubElement(SubElement(place, "Point"), "coordinates").text = f"{lng},{lat},0"
	return tostring(root, encoding="utf-8", xml_declaration=True)
