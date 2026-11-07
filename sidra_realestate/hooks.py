app_name = "sidra_realestate"
app_title = "Sidra Homes"
app_logo_url = "/assets/sidra_realestate/images/sidra-logo.png"
app_publisher = "Mohamoud Abdullahi Sheikh"
app_description = (
	"Sidra Real Estate on ERPNext: land and house sales, Murabaha / installment "
	"contracts, construction projects, brokerage"
)
app_email = "mohamoud.abdullahi1988@gmail.com"
app_license = "proprietary"

# ERPNext must be installed on the site before this app.
required_apps = ["erpnext"]

# ------------------------------------------------------------------
# Fixtures: roles from SRS v2.0 section 5. Contract profiles are created
# by install.py (only when missing), never overwritten on migrate.
# ------------------------------------------------------------------
fixtures = [
	{"dt": "Role", "filters": [["role_name", "like", "Sidra %"]]},
]

# White-label (sidra_realestate/branding.py): the Sidra Homes icon on the apps screen and rail,
# with the Real Estate and Construction sections from dock/ and sidebar/.
add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/sidra_realestate/images/sidra-icon.png",
		"title": "Sidra Homes",
		# Explicit landing page, as Frappe and ERPNext declare theirs (app_home "/desk/...").
		"route": "/desk/sidra-sale-contract",
		"has_permission": "sidra_realestate.branding.has_app_permission",
		"sequence_id": 0,
	}
]

website_context = {
	"favicon": "/assets/sidra_realestate/images/favicon.png",
	"splash_image": "/assets/sidra_realestate/images/sidra-logo.png",
}

after_install = "sidra_realestate.install.after_install"
after_migrate = "sidra_realestate.install.after_migrate"

# ------------------------------------------------------------------
# Scheduled jobs
# ------------------------------------------------------------------
scheduler_events = {
	"daily": [
		"sidra_realestate.services.reservations.expire_reservations",
		"sidra_realestate.services.prices.refresh_current_prices",
	],
}
