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
# Fixtures: exported with `bench --site <site> export-fixtures`
# Filled in Phase 0-1 (roles, accounts, custom fields, print formats).
# ------------------------------------------------------------------
fixtures = [
	# {"dt": "Role", "filters": [["role_name", "like", "Sidra %"]]},
	# {"dt": "Custom Field", "filters": [["module", "like", "Sidra %"]]},
	# {"dt": "Property Setter", "filters": [["module", "like", "Sidra %"]]},
	# {"dt": "Print Format", "filters": [["module", "like", "Sidra %"]]},
	# {"dt": "Workflow", "filters": [["name", "like", "Sidra %"]]},
]

# ------------------------------------------------------------------
# Document events (added as features are built)
# ------------------------------------------------------------------
# doc_events = {
# 	"Customer": {"validate": "sidra_realestate.sidra_sales.customer.check_duplicates"},
# 	"Sidra Sale Contract": {"on_submit": "sidra_realestate.sidra_installments.schedule.create_invoice"},
# }

# ------------------------------------------------------------------
# Scheduled jobs (spec: reservation expiry, reminders, default check,
# title deadline alerts)
# ------------------------------------------------------------------
# scheduler_events = {
# 	"daily": [
# 		"sidra_realestate.sidra_property.tasks.expire_reservations",
# 		"sidra_realestate.sidra_installments.tasks.flag_defaults",
# 		"sidra_realestate.sidra_property.tasks.title_deadline_alerts",
# 	],
# }
