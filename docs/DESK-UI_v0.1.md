# Sidra Desk usability fixes v0.1

12 November 2026. User walkthrough items 1–17 plus the follow-up price correction.

Apply through the normal reviewed deployment: backup, update app, migrate and
build assets, then restart. Migration backfills only the scheme display code and
refreshes cached prices from existing submitted effective Price History entries.
No guessed price, financial posting, signed-term edit or legal text is introduced.

Navigation uses explicit ownership of Sidra links in the Real Estate Sidebar.
Construction remains available through its existing sidebar as well; Claude's
construction-controls PR must retain its new destinations when this branch syncs.
The collections destination is the existing staff dashboard, not a nonexistent
standalone installments list or a claim that collection posting is implemented.

Existing known Sidra charts are repaired as Count charts and their currency is
cleared. Workspace chart captions drop the Sidra prefix; chart IDs remain stable.
Scheme grouping uses a fetched scheme_code instead of Link-title expansion.
New/custom charts outside the known names are preserved.

Scheme list counts are calculated on demand under the user's record permissions;
unknown/unreadable values display a dash. They are not stored global counters.
Unit district/neighbourhood are read-only fetched Scheme values. Populated Scheme
values become canonical on unit save; existing values with no Scheme equivalent
remain intact. No bulk location rewrite occurs.

Maps are opt-in on Unit/Construction Job forms. A tile-load failure hides the map
and explains the failure, retaining all saved geometry. This does not assert that
HTTP causes the provider failure. Test actual provider reachability on the VPS.

Follow-up review: imports already explicitly parse ISO and DD/MM/YYYY dates rather
than site-dependent guessing; the form now explains this and offers a download
button. Existing imported records are registered installment contracts. Profile
association/import extensions are separate from relabelling the template.

Outstanding business/data decisions from the follow-up:

- Markup conflicts with G3 (no markup); replacement formula/down-payment policy
  must be explicitly supplied before changing it.
- Sidra must supply approved Somali/English clause wording. Existing submission
  gates must remain; empty text must not be invented or marked approved.
- Contract cancellation currently intentionally protects allocations. Adding a
  role permission alone is insufficient: release, reversal and amendment rules
  need an approved workflow, including checks on native financial links.
- Profile IDs remain stable to protect links and frozen terms. Meaningful display
  names can be introduced without renaming historical legal identities.
- Consolidating settings and buyer KYC fields needs scoped permissions/data rules;
  these are not silently bundled into the presentation migration.

Validation: metadata, permission-filtered scheme counts and repeated repair run in
the repository bench CI. Browser acceptance still requires an authenticated VPS
session: navigation from each Sales form, count formatting, schemes with restricted
unit permissions, schedule width, map failure and existing saved list layouts.
