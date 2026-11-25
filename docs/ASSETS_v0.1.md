# Company assets in ERPNext Assets v0.1

25 Nov 2026 · Implements decision G40 (`docs/DECISIONS-AND-GATES_v0.3.md`). Recorded by Claude Code.

## Proposed for Finance's approval

| Category | Method | Useful life | Depreciation |
| --- | --- | --- | --- |
| Vehicles | Straight line | 5 years | yearly, 5 entries |
| Plant and equipment | Straight line | 8 years | yearly, 8 entries |
| Office equipment | Straight line | 5 years | yearly, 5 entries |
| IT equipment | Straight line | 3 years | yearly, 3 entries |

No residual value is assumed. Each category has a fixed-asset item of the same name, so staff record an Asset against *Vehicles*, *IT equipment* and so on. Plots and houses for sale remain Sidra Units, not assets.

## What is blocked until Finance approves

- Any Journal Entry of type **Depreciation Entry** is refused before submit (Desk, scheduler or API).
- Automatic depreciation booking (*Accounts Settings → Book Asset Depreciation Entry Automatically*) is switched off on every migrate.
- Recording and submitting an **existing asset** (no purchase invoice) posts nothing, so the register can be filled now.

When Finance approves the method, lives and accounts, an administrator adds `"sidra_depreciation_approved": 1` to the site config. After that, depreciation follows ERPNext's normal rules.

## Setting up the categories with Finance's accounts

The accounts are Finance's choice; nothing is invented. Give one ledger account of each type for the Company:

```bash
sudo -u frappe -H bash -lc "cd /home/frappe/sidra/frappe-bench && bench --site sidra.local execute sidra_realestate.services.assets.setup_asset_categories --kwargs \"{'company': 'Sidra Homes', 'fixed_asset_account': '<Fixed Asset account>', 'accumulated_depreciation_account': '<Accumulated Depreciation account>', 'depreciation_expense_account': '<Depreciation account>'}\""
```

The accounts must have the types *Fixed Asset*, *Accumulated Depreciation* and *Depreciation*.

## Test site

`pilot_assets.create_pilot_assets` adds clearly marked demo accounts under the pilot's demo account groups, sets up the categories with them and records eight fictional existing assets (two per category) at two demo locations. It has the pilot's guards and posts nothing:

```bash
sudo -u frappe -H bash -lc 'cd /home/frappe/sidra/frappe-bench && bench --site sidra.local execute sidra_realestate.pilot_assets.create_pilot_assets'
```
