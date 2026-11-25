"""Deterministic plan for the pilot demonstration dataset (decision G16). No Frappe needed.

This module decides *what* records the pilot dataset contains: how many, on which dates, for
which amounts. `sidra_realestate.pilot_demo` turns the plan into documents inside one guarded
transaction. Keeping the plan pure makes the counts, dates and money testable without a bench,
and makes a rerun provably identical: every value here comes from `SEED` and the anchor date.

Every name produced here is fictional. Nothing in this module reads or writes a database.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

# Changing SEED changes every generated record. It is fixed so that two runs of the same
# version produce the same dataset, which is what makes the ownership manifest meaningful.
SEED = 20261113
MONTHS = 12
# A notary reference is unique across the site, and the suite already fixes 042, 077-081 and
# 901-903. The pilot takes its own block so a loaded demo cannot collide with those.
NOTARY_BLOCK = 300
PREFIX = "SHP"  # "Sidra Homes Pilot" — distinct from demo.py's DEMO- and finance_demo's SHD.

SCHEMES = (
	(f"{PREFIX}-HARGEISA-E", "Pilot Hargeisa East", "Hargeisa", "Ahmed Dhagah", "Plot"),
	(f"{PREFIX}-HARGEISA-N", "Pilot Hargeisa North Ridge", "Hargeisa", "Mohamoud Haybe", "House"),
	(f"{PREFIX}-BERBERA-C", "Pilot Berbera Coastal", "Berbera", "Shacabka", "Apartment"),
	(f"{PREFIX}-BURCO-W", "Pilot Burco West", "Burco", "Koosaar", "Plot"),
)

# Fictional given/family names; combined below. No real person is intended.
GIVEN = (
	"Amina",
	"Hodan",
	"Warsame",
	"Deqa",
	"Liibaan",
	"Sahra",
	"Guuleed",
	"Ifrah",
	"Cabdi",
	"Naima",
	"Faysal",
	"Ubah",
	"Khadar",
	"Ayaan",
	"Siciid",
	"Barwaaqo",
	"Jibril",
	"Hawa",
	"Maxamed",
	"Samira",
)
FAMILY = (
	"Pilot Jaamac",
	"Pilot Cali",
	"Pilot Nuur",
	"Pilot Faarax",
	"Pilot Diriye",
	"Pilot Xasan",
	"Pilot Yuusuf",
	"Pilot Ismaaciil",
)

SERVICE_TYPES = ("Full Construction", "Design Only", "Inspection Only", "Beacon / Foundation")
JOB_STATUSES = ("Enquiry", "Quoted", "Contracted", "In Progress", "On Hold", "Completed")
STAGE_NAMES = ("Site clearing", "Foundation", "Superstructure", "Roofing", "Finishes")
BOQ_ITEMS = (
	("01", "Site clearing and setting out", "Nos", 1, 350),
	("02", "Excavation to reduced level", "Nos", 42.5, 8),
	("03", "Mass concrete foundation", "Nos", 18, 145.5),
	("04", "Blockwork to superstructure", "Nos", 260, 11.25),
	("05", "Roof structure and covering", "Nos", 1, 4200),
	("06", "Internal finishes and painting", "Nos", 1, 2750),
)


def money(value) -> Decimal:
	"""Two-decimal currency, half up. Every amount in a plan passes through here."""
	return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def add_months(day: date, count: int) -> date:
	"""`day` shifted by whole months, clamped to the last day of the target month."""
	index = day.year * 12 + day.month - 1 + count
	year, month = divmod(index, 12)
	month += 1
	last = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
	return date(year, month, min(day.day, last))


@dataclass
class Plan:
	"""Everything the loader creates, already dated and priced."""

	as_of: date
	from_date: date
	schemes: list[dict] = field(default_factory=list)
	units: list[dict] = field(default_factory=list)
	price_history: list[dict] = field(default_factory=list)
	customers: list[dict] = field(default_factory=list)
	quotations: list[dict] = field(default_factory=list)
	reservations: list[dict] = field(default_factory=list)
	contracts: list[dict] = field(default_factory=list)
	titles: list[dict] = field(default_factory=list)
	jobs: list[dict] = field(default_factory=list)
	invoices: list[dict] = field(default_factory=list)

	def counts(self) -> dict[str, int]:
		return {
			"schemes": len(self.schemes),
			"units": len(self.units),
			"price_history": len(self.price_history),
			"customers": len(self.customers),
			"quotations": len(self.quotations),
			"reservations": len(self.reservations),
			"contracts": len(self.contracts),
			"titles": len(self.titles),
			"jobs": len(self.jobs),
			"invoices": len(self.invoices),
		}


def _customers(rng: random.Random) -> list[dict]:
	names, seen = [], set()
	while len(names) < 40:
		name = f"{rng.choice(GIVEN)} {rng.choice(FAMILY)}"
		if name in seen:
			continue
		seen.add(name)
		index = len(names) + 1
		names.append(
			{
				"name": name,
				"id_type": "National ID" if index % 5 else "Passport",
				"id_number": f"{PREFIX}-ID-{3000 + index}",
				"phone": f"+252 63 000 3{index:03d}",
				"address": f"Pilot address {index}, Hargeisa",
				# Four in forty stay unverified, so the KYC gate has something to show.
				"verified": index % 10 != 0,
			}
		)
	return names


def _units(rng: random.Random, as_of: date) -> tuple[list[dict], list[dict]]:
	units, history = [], []
	for scheme_code, _, district, neighbourhood, unit_type in SCHEMES:
		for index in range(1, 31):
			code = f"{scheme_code}-{index:03d}"
			base = {"Plot": 5500, "House": 28000, "Apartment": 19000}[unit_type]
			price = money(base + rng.randrange(0, 9) * 250)
			units.append(
				{
					"unit_code": code,
					"scheme": scheme_code,
					"unit_type": unit_type,
					"district": district,
					"neighbourhood": neighbourhood,
					"plot_fraction": "Half" if unit_type == "Plot" and index % 2 else "Full",
					"dimensions": "9×24 m" if unit_type == "Plot" else "12×18 m",
					"area_sqm": 216.0 if unit_type == "Plot" else 216.0 + index,
					"land_parcel": f"Pilot Parcel {scheme_code[-1]}{index:03d}",
					"bedrooms": 0 if unit_type == "Plot" else 2 + index % 3,
					"floors": 0 if unit_type == "Plot" else 1 + index % 2,
					"offplan_status": "Off-plan" if index % 7 == 0 else "Ready",
					"cash_price": price,
				}
			)
			# A scheduled price review on roughly one unit in six, so Unit Price History is not
			# empty. Creating a unit with a price already records one entry dated today, and the
			# DocType requires each new price to take effect strictly after the latest one, so
			# these are dated ahead: upcoming reviews, not back-dated history.
			if index % 6 == 0:
				history.append(
					{
						"unit": code,
						"effective_from": as_of + timedelta(days=15 + rng.randrange(0, 166)),
						"price": money(price * Decimal("1.08")),
						"reason": "Pilot scheduled price review",
					}
				)
	return units, history


def _schedule(total: Decimal, down: Decimal, count: int, start: date, due_day: int) -> list[dict]:
	"""`count` monthly rows that add up exactly to `total - down`; the last row takes the rounding."""
	balance = money(total - down)
	each = money(balance / count)
	rows = []
	for i in range(count):
		due = add_months(start.replace(day=min(due_day, 28)), i + 1)
		amount = each if i < count - 1 else money(balance - each * (count - 1))
		rows.append({"due_date": due, "amount": amount})
	return rows


def build(as_of: date) -> Plan:
	"""The whole dataset, twelve months back from `as_of`. Deterministic for a given date."""
	rng = random.Random(SEED)
	plan = Plan(as_of=as_of, from_date=add_months(as_of, -MONTHS))
	plan.schemes = [
		{"scheme_code": code, "scheme_name": name, "district": district, "neighbourhood": hood}
		for code, name, district, hood, _ in SCHEMES
	]
	plan.customers = _customers(rng)
	plan.units, plan.price_history = _units(rng, as_of)

	verified = [c["name"] for c in plan.customers if c["verified"]]
	free = [u["unit_code"] for u in plan.units]
	by_code = {u["unit_code"]: u for u in plan.units}
	rng.shuffle(free)
	pool = iter(free)

	# ---------------------------------------------------------------- sales (SAL-05, SAL-08)
	for index in range(60):
		month = -(index % MONTHS) - 1
		quoted = add_months(as_of, month)
		unit = by_code[free[index % len(free)]]
		listed = unit["cash_price"]
		# One quotation in four carries a discount; one of those needs the General Manager.
		discount_pct = 0 if index % 4 else (Decimal("7.5") if index % 8 == 0 else Decimal("3.0"))
		cash = money(listed * (Decimal(100) - discount_pct) / 100)
		status = ("Draft", "Issued", "Expired")[index % 3]
		plan.quotations.append(
			{
				"reference": f"{PREFIX}-QUO-{index + 1:03d}",
				"customer": plan.customers[index % len(plan.customers)]["name"],
				"quotation_date": quoted,
				"valid_until": quoted + timedelta(days=7),
				"status": status,
				"unit": unit["unit_code"],
				"listed_price": listed,
				"cash_price": cash,
				"installment_price": money(listed * Decimal("1.15")),
				"discount_amount": money(listed - cash),
				"installments": (12, 18, 24, 36)[index % 4],
			}
		)

	# Reservations exist only through the Reserve Unit service, which dates them today and opens
	# them Active; the loader then closes some through the same service. So the plan carries the
	# hold length and the state to end in, never dates of its own.
	for index in range(25):
		plan.reservations.append(
			{
				"reference": f"{PREFIX}-RES-{index + 1:03d}",
				"unit": next(pool),
				"customer": verified[index % len(verified)],
				"days": (7, 14, 7)[index % 3],
				"status": ("Active", "Expired", "Cancelled")[index % 3],
			}
		)

	for index in range(45):
		month = -(index % MONTHS) - 1
		signed = add_months(as_of, month)
		codes = [next(pool)]
		if index % 5 == 0:
			codes.append(next(pool))
		price = money(sum(by_code[c]["cash_price"] for c in codes))
		installment = index % 3 != 0
		# Only an installment contract can be externally registered; a cash contract has no
		# source, no profile and no external reference at all.
		external = installment and index % 7 == 0
		count = (12, 18, 24, 36)[index % 4]
		down = money(price * Decimal("0.20")) if installment else money(0)
		contract = {
			"reference": f"{PREFIX}-CON-{index + 1:03d}",
			"customer": verified[index % len(verified)],
			"signed_on": signed,
			"contract_type": "Installment" if installment else "Cash",
			"source": "External (registered)" if external else "Generated from profile",
			"external_reference": f"{PREFIX}-EXT-{index + 1:04d}" if external else None,
			"units": [{"unit": c, "allocated_price": by_code[c]["cash_price"]} for c in codes],
			"agreed_price": price,
			"down_payment": down,
			"installments": count if installment else 0,
			"due_day": 5,
			"notary_reference": f"IPN/HL/{NOTARY_BLOCK + index:03d}/{signed.year}",
			# Three in forty-five stay draft so the pipeline is not uniformly submitted.
			"submit": index % 15 != 0,
			"schedule": _schedule(price, down, count, signed, 5) if installment else [],
		}
		plan.contracts.append(contract)

	submitted = [c for c in plan.contracts if c["submit"]]
	for index, contract in enumerate(submitted[:20]):
		unit = contract["units"][0]["unit"]
		# Spread the tracker across its states: in progress, due soon, overdue, handed over.
		stage = index % 4
		# The tracker refuses a final payment in the future or before the contract, and a
		# handover before the final payment, so both are clamped to the load date.
		final_payment = min(add_months(contract["signed_on"], 2), as_of)
		handover = min(add_months(final_payment, 1), as_of)
		plan.titles.append(
			{
				"reference": f"{PREFIX}-TTL-{index + 1:03d}",
				"contract": contract["reference"],
				"unit": unit,
				"final_payment_date": final_payment,
				"deed_number": f"{PREFIX}-DEED-{4000 + index}" if stage == 3 else None,
				"handed_over_on": handover if stage == 3 else None,
				"land_office_reference": f"{PREFIX}-LO-{5000 + index}",
				"documents": ["Title deed copy", "Sale agreement", "Buyer ID copy"],
			}
		)

	# ---------------------------------------------------------------- construction (CON-02, CON-03)
	for index in range(25):
		started = add_months(as_of, -(index % MONTHS) - 1)
		status = JOB_STATUSES[index % len(JOB_STATUSES)]
		boq = [
			{
				"cost_code": code,
				"description": f"{text} (pilot)",
				"uom": uom,
				"qty": qty,
				"rate": money(rate),
			}
			for code, text, uom, qty, rate in BOQ_ITEMS[: 3 + index % 4]
		]
		total = money(sum(Decimal(str(r["qty"])) * r["rate"] for r in boq))
		done = {"Enquiry": 0, "Quoted": 0, "Contracted": 1, "In Progress": 3, "On Hold": 2}.get(
			status, len(STAGE_NAMES)
		)
		billing = [money(Decimal(100) / len(STAGE_NAMES))] * len(STAGE_NAMES)
		billing[-1] = money(Decimal(100) - sum(billing[:-1]))
		plan.jobs.append(
			{
				"reference": f"{PREFIX}-JOB-{index + 1:03d}",
				"customer": plan.customers[(index * 3) % len(plan.customers)]["name"],
				"service_type": SERVICE_TYPES[index % len(SERVICE_TYPES)],
				"status": status,
				"site_location": f"Pilot site {index + 1}, {SCHEMES[index % 4][2]}",
				"plot_number": f"{SCHEMES[index % 4][0]}-{index % 30 + 1:03d}",
				"started_on": started,
				"boq": boq,
				"boq_total": total,
				"stages": [
					{
						"stage_name": name,
						"status": ("Completed" if i < done else "In Progress" if i == done else "Planned"),
						"planned_start": add_months(started, i),
						"planned_end": add_months(started, i + 1),
						"completion_pct": money(100 if i < done else 40 if i == done else 0),
						"billing_pct": billing[i],
						"certified": i < done,
					}
					for i, name in enumerate(STAGE_NAMES)
				],
				# A quotation for anything past Enquiry; a contract value once Contracted.
				"quotation": status != "Enquiry",
				"contracted": status in ("Contracted", "In Progress", "On Hold", "Completed"),
				"variation": money(1200 + index * 150) if index % 3 == 0 else None,
				"inspection": index % 2 == 0,
				"retention_pct": money(5),
				"retention_period_months": 6,
				"duration_days": 90 + (index % 5) * 30,
			}
		)

	# ---------------------------------------------------------------- finance (G14 guard applies)
	# Service revenue and running costs only: no contract-to-ledger mapping, no land-sale
	# recognition. Amounts are fictional and settle to the receipts recorded below.
	for index in range(60):
		month = -(index % MONTHS) - 1
		posted = add_months(as_of, month) + timedelta(days=index % 20)
		if posted > as_of:
			posted = as_of
		amount = money(2500 + (index % 9) * 1750)
		# Paid in full, part paid, or open — so AR shows a real ageing profile.
		share = (Decimal(1), Decimal("0.4"), Decimal(0))[index % 3]
		plan.invoices.append(
			{
				"kind": "Sales Invoice",
				"reference": f"{PREFIX}-SI-{index + 1:03d}",
				"posting_date": posted,
				"due_date": posted + timedelta(days=30),
				"amount": amount,
				"paid": money(amount * share),
				"description": "Pilot professional services",
			}
		)
	for index in range(35):
		month = -(index % MONTHS) - 1
		posted = add_months(as_of, month) + timedelta(days=index % 15)
		if posted > as_of:
			posted = as_of
		amount = money(900 + (index % 7) * 650)
		share = (Decimal(1), Decimal("0.5"), Decimal(0))[index % 3]
		plan.invoices.append(
			{
				"kind": "Purchase Invoice",
				"reference": f"{PREFIX}-PI-{index + 1:03d}",
				"posting_date": posted,
				"due_date": posted + timedelta(days=30),
				"amount": amount,
				"paid": money(amount * share),
				"description": "Pilot subcontract and running costs",
			}
		)
	return plan


def totals(plan: Plan) -> dict[str, Decimal]:
	"""The figures the verification sweep checks against the posted ledger."""
	revenue = money(sum(i["amount"] for i in plan.invoices if i["kind"] == "Sales Invoice"))
	expenses = money(sum(i["amount"] for i in plan.invoices if i["kind"] == "Purchase Invoice"))
	receipts = money(sum(i["paid"] for i in plan.invoices if i["kind"] == "Sales Invoice"))
	payments = money(sum(i["paid"] for i in plan.invoices if i["kind"] == "Purchase Invoice"))
	return {
		"capital": money(500000),
		"revenue": revenue,
		"expenses": expenses,
		"receipts": receipts,
		"supplier_payments": payments,
		"receivables": money(revenue - receipts),
		"payables": money(expenses - payments),
		"bank": money(Decimal(500000) + receipts - payments),
	}
