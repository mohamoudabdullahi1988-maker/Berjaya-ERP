# Berjaya frontend v0.1

13 Nov 2026 · the Berjaya interface served at `/berjaya` (Vue 3, Vite, Frappe UI).

"Berjaya" is the software; "Sidra" is the client company and comes from the server.

## Build

```bash
bench build --app sidra_realestate      # on a bench: installs and builds this folder too
# or, from a clean checkout without a bench:
yarn install --frozen-lockfile && yarn build      # run at the repository root
```

The build writes `sidra_realestate/public/berjaya/` and `sidra_realestate/www/berjaya.html`.
Neither is committed. `sidra_realestate/www/berjaya.py` supplies the session boot data.

## Rules

- Sign-in is the existing Frappe session. No tokens, nothing in local storage.
- Colours and fonts are defined once, in `src/tokens.css`. Fonts are bundled, not fetched.
- The server says which sections and fields a user may see (`window.berjaya_boot`). The
  frontend shows that; it decides no permission and holds no business rule of its own.
- A value the user may not see reads "Unavailable": never zero, never a partial figure.
- No demo or in-memory data. A failed request shows the failure, not a fallback.
- `yarn dev` is not wired to a session yet: the boot data only exists on the built page.
