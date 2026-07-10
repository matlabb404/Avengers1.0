# Avengers Backend — Deployment & Security Runbook

A consolidated setup guide for standing up the Avengers FastAPI backend on a fresh
VPS with new credentials. Everything here was collected from across the project so a
migration can be done from a clean slate without re-deriving anything.

> **Scope:** backend deployment, secrets, systemd services, nginx, and the push
> (FCM/APNs) setup. The Android app side is noted only where it must match a backend value.

---

## 1. Server topology (current, for reference)

| Thing | Value |
|---|---|
| Current host | `194.5.157.6` / `compassconn.com` (also `patterns.group`) |
| SSH user | `compassadmin` |
| App code dir | `/home/compassadmin/.avengers/Avengers1.0/APIs/` |
| Python virtualenv | `/home/compassadmin/.avengers/env/` |
| Secrets dir | `/home/compassadmin/.avengers/secrets/` |
| API systemd unit | `atb` (uvicorn, port `8000`) |
| Worker systemd unit | arq worker (media + push dispatch) |
| nginx proxy prefix | `/secret/test/avengers/test/backend/dev/` |
| Database | Postgres 16, DB name `Avengers` (capital A) |
| Cache / queue | Redis (arq jobs) |
| Object storage | Cloudflare R2, custom domain `media.patterns.group` |
| Payments | Paystack |

> On a new VPS, pick fresh values for the host, the nginx prefix, and **all** secrets.
> Don't carry over the old prefix or keys — treat the migration as a credential rotation.

---

## 2. One-time server prep (fresh VPS)

```bash
# Base packages (adjust for your distro; this repo has run on a RHEL-family box)
sudo dnf install -y python3.12 python3.12-devel git nginx redis postgresql-server postgresql-contrib
# (Debian/Ubuntu: apt install python3.12 python3.12-venv git nginx redis-server postgresql)

# Create the app user if not present
sudo useradd -m compassadmin   # or your chosen user

# Directory layout
sudo -u compassadmin mkdir -p /home/compassadmin/.avengers
cd /home/compassadmin/.avengers

# Virtualenv
python3.12 -m venv env
source env/bin/activate
pip install --upgrade pip

# Clone the code (private repo — use a deploy key or PAT)
git clone https://github.com/yawdjan/com.android.patterns.git   # Android
# The backend lives in its own path/repo; place it at:
#   /home/compassadmin/.avengers/Avengers1.0/APIs/
```

### Python dependencies

Install into the venv (the ones this project explicitly relies on):

```bash
source /home/compassadmin/.avengers/env/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary \
            python-dotenv httpx boto3 arq redis \
            cryptography pyjwt   # cryptography + pyjwt for the manual FCM/APNs JWT signing
```

---

## 3. Secrets directory & file permissions

All private keys live in one locked-down directory. **Do this before dropping any secret.**

```bash
mkdir -p /home/compassadmin/.avengers/secrets
chmod 700 /home/compassadmin/.avengers/secrets
```

`700` on the dir = only the owner can even list it. Then every file inside gets `600`
(owner read/write only, no group/other):

```bash
chmod 600 /home/compassadmin/.avengers/secrets/*
```

### Files that belong in `secrets/`

| File | Purpose | Where to get it |
|---|---|---|
| `fcm-sa.json` | FCM service account — signs the OAuth2 JWT for Android push | Firebase console → Project Settings → Service accounts → **Generate new private key** |
| `AuthKey_XXXX.p8` | APNs auth key — signs the ES256 JWT for iOS push | Apple Developer → Certificates, IDs & Profiles → Keys → create key with APNs enabled (**one-time download**) |

> The `.p8` is downloadable **once** from Apple. If lost, you revoke and make a new one.
> The `fcm-sa.json` can be regenerated any time from the Firebase console.

---

## 4. Copying secrets to the server (scp)

From your local machine, with the files downloaded locally:

```bash
# Ensure the target dir exists & is locked first
ssh compassadmin@<NEW_HOST> \
  'mkdir -p /home/compassadmin/.avengers/secrets && chmod 700 /home/compassadmin/.avengers/secrets'

# FCM service account (Android)
scp /path/to/fcm-sa.json \
  compassadmin@<NEW_HOST>:/home/compassadmin/.avengers/secrets/fcm-sa.json

# APNs key (iOS — skip if not shipping iOS yet)
scp /path/to/AuthKey_XXXX.p8 \
  compassadmin@<NEW_HOST>:/home/compassadmin/.avengers/secrets/AuthKey_XXXX.p8

# Lock the files down after they land, then restart the API so it re-reads them
ssh compassadmin@<NEW_HOST> \
  'chmod 600 /home/compassadmin/.avengers/secrets/* && sudo systemctl restart atb'
```

Notes:
- `scp` uses **`-P`** (capital) for a non-default SSH port; `ssh` uses lowercase `-p`.
- Use `-i <keyfile>` on both if you auth with a specific key.
- Credentials are loaded at **startup**, so a running process won't see a newly-dropped
  file until you `systemctl restart atb`.

---

## 5. Environment file (`.env`)

Lives in the app dir (`load_dotenv()` reads it from `WorkingDirectory`):
`/home/compassadmin/.avengers/Avengers1.0/APIs/.env`

```bash
# ── Database ─────────────────────────────────────────────
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/Avengers

# ── Auth / JWT ───────────────────────────────────────────
JWT_SECRET=<long-random-string>          # rotate on migration
# get_current_user decodes the app JWT with sub=EMAIL (not user_id)

# ── Payments (Paystack) ──────────────────────────────────
PAYSTACK_SECRET_KEY=<sk_...>
PAYMENT_CALLBACK_URL=avengers://payment/callback   # NOT a placeholder http URL
BOOKING_PAYMENT_TIMEOUT_MINUTES=15

# ── Cloudflare R2 (media) ────────────────────────────────
USE_S3=true
R2_ACCOUNT_ID=<...>
R2_ACCESS_KEY_ID=<...>
R2_SECRET_ACCESS_KEY=<...>
R2_BUCKET=<...>
R2_PUBLIC_DOMAIN=media.patterns.group

# ── Push: FCM (Android) — file-path design ───────────────
FIREBASE_CREDENTIALS_PATH=/home/compassadmin/.avengers/secrets/fcm-sa.json

# ── Push: APNs (iOS) — deferred until iOS ships ──────────
APNS_AUTH_KEY_PATH=/home/compassadmin/.avengers/secrets/AuthKey_XXXX.p8
APNS_KEY_ID=XXXXXXXXXX          # 10-char key ID from Apple
APNS_TEAM_ID=YYYYYYYYYY         # your Apple team ID
APNS_BUNDLE_ID=com.yourcompany.avengers   # your REAL iOS bundle id
APNS_USE_SANDBOX=true           # true for dev/TestFlight, false for App Store prod
```

### Important `.env` gotchas

- **`PAYMENT_CALLBACK_URL` must be the real deep link** (`avengers://payment/callback`),
  never the placeholder `https://yourapp.com/...`. Python treats the placeholder as
  truthy and picks it over the empty string the app sends → broken redirect. The app
  must send the same string in `callbackUrl`.
- **FCM uses the file-path design.** Because `fcm-sa.json` is a real JSON file, the
  `project_id` / `client_email` / `private_key` are read **out of the file**. You do
  **not** put `FCM_PROJECT_ID` / `FCM_CLIENT_EMAIL` / `FCM_PRIVATE_KEY` in `.env`.
  (Those are only for the alternate "individual fields" design, which this project does
  not use.) The PEM inside the JSON is already correct — no `\n` un-escaping needed
  (that trick is only for keys stored raw in an env var).
- Every push setting in `settings.py` must read via `os.getenv(...)`, not a bare
  annotation — a bare annotation means the value is never actually loaded and the JWT
  signer has nothing to sign with (silent no-op sends).

---

## 6. systemd — API service (`atb`)

`/etc/systemd/system/atb.service`:

```ini
[Unit]
Description=FastAPI app with Uvicorn
After=network.target

[Service]
User=compassadmin
Group=compassadmin
WorkingDirectory=/home/compassadmin/.avengers/Avengers1.0/APIs
Environment="PATH=/home/compassadmin/.avengers/env/bin"
ExecStart=/home/compassadmin/.avengers/env/bin/uvicorn main:app \
    --host 0.0.0.0 --port 8000 \
    --app-dir /home/compassadmin/.avengers/Avengers1.0/APIs \
    --root-path /secret/test/avengers/test/backend/dev
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Key points:
- **`WorkingDirectory` must be the APIs dir** so `python-dotenv`'s `load_dotenv()` finds
  `.env`. This unit deliberately does **not** use `EnvironmentFile=` — it relies on
  dotenv reading `.env` from the working dir.
- **`--root-path` must match the nginx prefix.** Without it, Swagger UI fetches
  `/openapi.json` (no prefix), nginx returns `index.html`, and Swagger breaks. It also
  makes the OAuth2 `tokenUrl` resolve correctly. On a new VPS, set this to whatever new
  prefix you choose.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now atb
sudo systemctl status atb --no-pager | head -10
```

---

## 7. systemd — arq worker (media + push dispatch)

Push delivery and media processing run off arq (fire-and-forget from the request path).

`/etc/systemd/system/avengers-worker.service`:

```ini
[Unit]
Description=Avengers background worker (arq)
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=compassadmin
Group=compassadmin
WorkingDirectory=/home/compassadmin/.avengers/Avengers1.0/APIs
Environment="PATH=/home/compassadmin/.avengers/env/bin"
ExecStart=/home/compassadmin/.avengers/env/bin/arq app.workers.media_worker.WorkerSettings
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now avengers-worker
sudo systemctl status avengers-worker --no-pager | head -10
```

> Same dotenv rule: `WorkingDirectory` = APIs dir so the worker picks up `.env`.
> If push and media are split into separate worker settings, run one unit per
> `WorkerSettings` class.

---

## 8. nginx reverse proxy

Single catch-all so every path reaches uvicorn (and new endpoints "just work"):

```nginx
server {
    server_name <NEW_HOST>;

    # ... your SSL / certbot config ...

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        client_max_body_size 100M;    # media uploads
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

```bash
# Back up first
sudo cp -a /etc/nginx/nginx.conf ~/nginx_backup_$(date +%Y%m%d).conf
sudo nginx -t          # syntax check BEFORE applying
sudo systemctl reload nginx
```

> If you keep a path prefix, the `proxy_pass` trailing-slash behaviour strips it before
> forwarding — which is exactly why the API needs `--root-path` set to that same prefix.

---

## 9. Database

- Postgres 16, DB name **`Avengers`** (capital A).
- Schema changes are applied via **hand-written SQL on the VPS**, not Alembic.
- Mixed-case table names — quoting matters in raw SQL:
  - lowercase: `users`, `booking`, `services`, `add_service`, `booking_slots`, `price_history`, `payment`, `refund`, `webhook_event`
  - PascalCase (needs quotes): `"Vendor"`
- `add_service.id` is `character varying`, **not** UUID.
- `User.id` is the universal FK for notifications.

Provision on a fresh box:

```bash
sudo postgresql-setup --initdb     # RHEL-family; skip if already initialised
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE DATABASE \"Avengers\";"
sudo -u postgres psql -c "CREATE USER <user> WITH PASSWORD '<password>';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"Avengers\" TO <user>;"
# then apply your hand-written schema SQL
```

---

## 10. Push setup checklist (backend → FCM → device)

Android push cannot avoid FCM (Google's transport). iOS uses direct APNs (no Firebase).
Both use fully-manual JWTs — RS256 for FCM's OAuth2 token, ES256 for APNs.

**Android (do this now):**
1. `fcm-sa.json` present at `FIREBASE_CREDENTIALS_PATH`, `chmod 600`.
2. `settings.py` reads `FIREBASE_CREDENTIALS_PATH` via `os.getenv`; push module
   `json.load`s it and pulls `project_id` / `client_email` / `private_key`.
3. `project_id` from the JSON flows into the send URL:
   `https://fcm.googleapis.com/v1/projects/{project_id}/messages:send`.
4. `google-services.json` is in the **Android app** (not the backend), Firebase plugin
   applied — required for the app to obtain a token / FID at all.
5. Device registers its token: app calls the `registerDevice` endpoint on start/login
   and the token lands in the multi-device token table. **A push from your backend only
   works if the device's token is in your DB** (the Firebase console test bypasses this).
6. `systemctl restart atb` after dropping the JSON, then trigger a real notification
   (like/follow/booking) and watch the worker log for the FCM send result.

**iOS (deferred until you ship iOS):**
- Real `AuthKey_XXXX.p8` in `secrets/`, and real `APNS_KEY_ID` / `APNS_TEAM_ID` /
  `APNS_BUNDLE_ID` (not the `com.yourcompany.avengers` placeholder).
- `APNS_USE_SANDBOX=true` for dev/TestFlight, `false` for App Store production.

---

## 11. Health checks after migration

```bash
# API up, no credential-load errors at startup
sudo journalctl -u atb -n 50 --no-pager

# Worker up, Redis reachable
sudo journalctl -u avengers-worker -n 50 --no-pager

# Swagger renders (confirms --root-path ↔ nginx prefix match)
#   https://<NEW_HOST>/<prefix>/docs

# DB reachable from the app venv
/home/compassadmin/.avengers/env/bin/python -c \
  "import os,psycopg2; psycopg2.connect(os.environ['DATABASE_URL']); print('db ok')"
```

---

## 12. Security items still open (carry-overs)

These were deferred earlier and should be revisited, especially on a "more secured" VPS:

- [ ] **#3** Password reset flow
- [ ] **#4** Rate limiting
- [ ] **#5** JWT refresh tokens
- [ ] **#8** CORS configuration
- [ ] `Booking.created_at` correctly wired into `expire_unpaid_bookings`
- [ ] Admin role guard on cleanup endpoints
- [ ] Rotate **all** secrets on migration (JWT secret, Paystack keys, R2 keys, regenerate
      `fcm-sa.json`) — don't reuse the old box's credentials.
- [ ] Consider firewalling Postgres/Redis to localhost only (`bind 127.0.0.1`) and
      confirm they're not exposed publicly on the new host.

---

## 13. Quick reference — secret → source

| Secret | Source | Rotate on migration? |
|---|---|---|
| `JWT_SECRET` | you generate (random) | ✅ yes |
| `PAYSTACK_SECRET_KEY` | Paystack dashboard | ✅ yes (or reuse if same account) |
| `R2_*` keys | Cloudflare R2 API tokens | ✅ yes |
| `fcm-sa.json` | Firebase console → Service accounts | ✅ regenerate |
| `AuthKey_XXXX.p8` | Apple Developer → Keys (one-time DL) | reuse (or revoke+recreate) |
| DB password | you set at `CREATE USER` | ✅ yes |

---

## b4. CReate Table Refredsh tokens.
-- refresh_tokens: one row per issued refresh token. We store only the SHA-256
-- hash of the opaque token, never the token itself. Rotation creates a new row
-- and marks the old one revoked; a whole "family" (chain of rotations from one
-- login) shares family_id so reuse of a revoked token can nuke the family.
CREATE TABLE refresh_tokens (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash    text NOT NULL UNIQUE,          -- SHA-256 hex of the opaque token
    family_id     uuid NOT NULL,                 -- shared across a rotation chain
    issued_at     timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz NOT NULL,
    revoked       boolean NOT NULL DEFAULT false,
    revoked_at    timestamptz,
    replaced_by   uuid,                           -- the token that rotated this one
    user_agent    text,                           -- optional: device/client hint
    created_ip    text                            -- optional: audit
);

CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_user_id     ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family_id   ON refresh_tokens(family_id);