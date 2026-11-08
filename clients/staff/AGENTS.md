# Sidra staff clients

Current allocation (7 Nov 2026): Claude owns backend/test-server implementation. Codex owns the shared staff web UI, Android/macOS shells and their tests. The user separately authorized a plot/site location API; its isolated Frappe adapter is for integration with Claude's backend.

Keep business calculations, permissions, contract validation and authoritative data on the ERPNext/Frappe server. Do not copy backend business logic into clients. Staff only. Use fictional preview data explicitly; never silently substitute it for a failed live request. No secrets or real customer data in source. Do not edit the concurrent backend checkout. Construction scope is limited to the requested site location and read-only KPIs for existing jobs/milestones; do not implement construction workflows. No postings, payment collection, penalties, refunds or title transfer. Preserve existing records.
