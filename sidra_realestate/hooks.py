app_name = "sidra_realestate"
app_title = "Sidra Real Estate"
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
