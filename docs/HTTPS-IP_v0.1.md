# Sidra ERP — HTTPS on the VPS IP address v0.1

12 Nov 2026 · test VPS `5.253.233.218` (Contabo, Ubuntu, site `sidra.local`, bench `/home/frappe/sidra/frappe-bench`). Companion to [DEPLOYMENT_v0.1.md](DEPLOYMENT_v0.1.md).

**Status: prepared, not yet run on the VPS.** The script was written from the bench nginx template (frappe-bench 5.31.1) and rehearsed in a container against a real nginx 1.24 with bench's generated config, fake Frappe / Socket.IO backends, a test CA and stubbed systemd / certbot. No command has been run on the server and nothing below is verified there until `apply` prints its PASS lines on the VPS.

There is no domain name, so the certificate is a Let's Encrypt **IP-address certificate** (profile `shortlived`, about six days). It is free and trusted by browsers. This changes transport security only: no DocType, posting rule, profile value or business gate is touched.

## 1. How to run it

On the VPS, as a user with sudo:

```bash
cd /home/frappe/sidra/frappe-bench/apps/sidra_realestate
git fetch "$(git remote | head -1)" develop && git show FETCH_HEAD:deploy/sidra-https-ip.sh > /tmp/sidra-https-ip.sh
sudo bash /tmp/sidra-https-ip.sh inspect     # read-only report
sudo bash /tmp/sidra-https-ip.sh apply       # full setup, stops at the first failed check
```

Until the script is merged into `develop`, fetch its branch name instead of `develop`. `apply` is safe to run again. Output is also written to `/var/log/sidra-https-ip.log`.

| Command | Effect |
| --- | --- |
| `inspect` | Prints what nginx loads, how the bench file is attached, listeners, logs, certificate, timers, firewall. Changes nothing. |
| `apply` | Sections 2 to 5 below, in order, each gated by checks. |
| `regen [passthrough\|redirect]` | Rebuilds the nginx file from the loaded bench config and re-checks. |
| `verify` | Re-runs all checks. |
| `rollback` | Removes everything the script added (section 7). |

After `apply` the script is installed as `/usr/local/sbin/sidra-https-ip`.

## 2. What it configures

| Item | Path | Notes |
| --- | --- | --- |
| nginx file | `/etc/nginx/conf.d/sidra-https.conf` | Generated. The only nginx file changed. |
| Certificate | `/etc/letsencrypt/live/sidra-ip/` | Existing certificate reused when it is valid for more than 24 hours; otherwise `certbot renew`, then the original `certonly` command as a fallback. |
| ACME webroot | `/var/www/letsencrypt` | Served at `/.well-known/acme-challenge/` on ports 80 and 443. |
| Deploy hook | `/etc/letsencrypt/renewal-hooks/deploy/sidra-nginx-reload.sh` | Runs only after a successful renewal; reloads nginx only if `nginx -t` passes. |
| Renewal | `sidra-certbot-renew.service` and `.timer` in `/etc/systemd/system` | `/opt/sidra-certbot/bin/certbot renew --cert-name sidra-ip`, every 6 hours, `Persistent=true` (catches up after the VPS was off). |
| Frappe | `host_name = https://5.253.233.218` in `sites/sidra.local/site_config.json` | Only when unset or the plain-HTTP IP. Skip with `SIDRA_SET_HOST_NAME=0`. |
| Firewall | `ufw allow 80/tcp`, `443/tcp` | Only if ufw is already active. ufw is never enabled or reset, and SSH rules are not touched. |

Bench's `config/nginx.conf` is **not edited**, and no `ssl_certificate` key is added to the site config. Bench's own SSL support names the server after the site (`sidra.local`), not the IP, and its HTTP block redirects everything, including the ACME challenge, so it does not fit an IP certificate.

Instead the HTTPS server is **derived from the server block nginx actually loads** (`nginx -T`): the port-80 block that sends `X-Frappe-Site-Name sidra.local` is copied, its `listen` lines become `443 ssl`, its `server_name` becomes the IP, and the certificate and ACME location are added. Assets, `/protected/` (private files through X-Accel-Redirect), `/files/` uploads, `/socket.io` with the WebSocket upgrade, error pages, timeouts and body-size limits are therefore identical to the HTTP site. `X-Forwarded-Proto` becomes `https` because the bench block uses `$scheme`.

Port 80 gets a separate `default_server` block for the IP: the ACME path from the webroot, and `301` to `https://5.253.233.218` for everything else. The bench's own port-80 block stays loaded and still answers `Host: sidra.local` on the server itself.

## 3. Order of work and gates

1. Inspect and back up (section 6).
2. HTTP still serves the site; the ACME path is added and tested with a real file through `http://5.253.233.218/`.
3. Certificate checked: dates, IP in the subject alternative name, key matches.
4. HTTPS on 443 added. Checks: trusted handshake with the IP as identity (curl and `openssl s_client -verify_ip`), login page, a CSS/JS asset from the page, `/api/method/ping`, `/protected/` not public, private file refused without login, a public upload if one exists, Socket.IO polling handshake and WebSocket `101`.
5. Renewal installed; `certbot renew --dry-run` (Let's Encrypt staging validates port 80 from the internet), deploy hook executed once, service started once, timer checked.
6. Only then HTTP is redirected; the redirect, the ACME path and all HTTPS checks run again.

A failed check stops the run before the next step. A rejected nginx file is replaced by the previous one and nginx is reloaded.

## 4. The earlier failed attempt (connection refused on 127.0.0.1:443)

Not yet diagnosed on the server; `inspect` prints the evidence (bench file linked or copied, leftover `443` lines, differences from `/var/backups/sidra/nginx.before-https.UPy4qPu7`, listeners, nginx errors). Known causes this script removes:

- `systemctl reload nginx` returns before the new listener exists. The script waits up to 30 seconds for port 443 and then one more second before testing.
- A reload with a configuration nginx rejects keeps the old configuration silently. The script runs `nginx -t` first and prints the journal and error log on failure.
- Editing a bench file that nginx does not load (a copy instead of the symlink) has no effect. The script derives from `nginx -T` and writes its own file under `/etc/nginx/conf.d`.

## 5. Renewal

The certificate lasts about six days. certbot renews it when Let's Encrypt's renewal information says so (roughly half-way), and the timer checks every 6 hours, so one missed day is harmless. Other certbot timers (`certbot.timer`, `snap.certbot.renew.timer`) and `/etc/cron.d/certbot` are disabled or moved into the backup folder so only one schedule exists; a certbot line in root's crontab is reported, not removed.

```bash
systemctl list-timers sidra-certbot-renew.timer
journalctl -u sidra-certbot-renew.service -n 20
journalctl -t sidra-certbot            # hook: reloaded, or refused because nginx -t failed
sudo /opt/sidra-certbot/bin/certbot certificates
```

If renewal fails for six days the browser shows an expired certificate. `sudo sidra-https-ip verify` shows which part fails.

## 6. After `bench setup nginx` or `bench setup production`

Those commands rewrite only `config/nginx.conf` and the `frappe-bench.conf` link; `sidra-https.conf` stays and HTTPS keeps working. Because the HTTPS server is a copy of the bench block, refresh it after bench changes that block (new timeout, new bench version):

```bash
sudo sidra-https-ip regen
```

Do not add `ssl_certificate` keys to the site config and do not turn on `dns_multitenant` without revisiting this document: both change the block the copy is made from.

## 7. Backups and rollback

Each `apply` creates `/var/backups/sidra/https-ip-<date>-<time>/` (root only): `etc-nginx.tar.gz`, `nginx-T.before.txt`, `bench-nginx.conf`, `site_config.json`, `renewal-sidra-ip.conf`, firewall and timer listings, and markers for what was changed. Private keys are never copied. The earlier backup `/var/backups/sidra/nginx.before-https.UPy4qPu7` is left as it is.

```bash
sudo sidra-https-ip rollback                 # back to plain HTTP
sudo sidra-https-ip regen passthrough        # keep HTTPS, stop redirecting HTTP
```

`rollback` removes the nginx file, hook, service and timer, reloads nginx, restores the previous `host_name` and re-enables timers it had disabled. The certificate is kept. ufw rules for 80/443 stay; remove them with `sudo ufw delete allow 443/tcp` if wanted. Last resort: `sudo tar -C / -xzf <backup>/etc-nginx.tar.gz && sudo nginx -t && sudo systemctl reload nginx`.

## 8. Open points

| Point | Owner |
| --- | --- |
| Run `apply` on the VPS and keep its output as evidence | Mohamoud |
| Check from outside the server: `curl -sSI https://5.253.233.218/login`. The script tests from the VPS itself; only the dry run proves port 80 from outside. | Mohamoud |
| If outside access times out: in the Contabo customer panel firewall, allow inbound TCP 80 and TCP 443 to `5.253.233.218` from any source (keep the SSH rule) | Mohamoud |
| Staff client and bookmarks: use `https://5.253.233.218` | Mohamoud |
| A DNS name later: issue a normal 90-day certificate for it and retire this setup (DEPLOYMENT section 6) | Sidra |
