# Tōtika Compliance & Audit Tool

Enterprise-grade compliance auditing and risk management platform. Built with Flask, SQLAlchemy, and SQLite — designed to run on a Raspberry Pi in a Docker container.

## Features

- **Multi-Framework Compliance Auditing** — Tōtika Category 2, PCI-DSS v4, ISO 27001, ISO 9001, ISO 14001, ISO 45001, NIST CSF 2.0, GDPR, SOC 2
- **Criterion Scoring** — 0–4 scale with scoring anchors, evidence checklists, auditor tips, N/A and info-only support
- **Scoping Engine** — Framework-specific scoping questions that auto-determine criterion applicability
- **Gap Analysis** — Corrective actions with assignment, priority, due dates, evidence uploads, and rich gap-item fields
- **Enterprise Risk Management** — ISO 31000 aligned, 5×5 risk matrix heatmap, risk register with mitigations, reviews, and 10 seeded business area categories
- **Compliance Matrix** — Cross-framework compliance dashboard with trend tracking and control area breakdowns
- **Sign-Off Workflow** — Auditor finalisation and auditee acknowledgement with typed name and comments
- **PDF Reports** — Downloadable audit reports via WeasyPrint
- **RBAC** — Role-based access control (Admin, Auditor, Auditee, Viewer)
- **Branding** — Customisable company name, logo, header/footer colours (app-wide)
- **SMTP & Email** — Configurable email notifications with branded templates, welcome emails on account creation
- **Password Management** — Self-service password change, password reset via email with domain auto-detection
- **Activity Logging** — Audit trail of user actions
- **Legacy Import** — Import audits from the standalone v3 HTML/JSON format

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, Flask, SQLAlchemy |
| Database | SQLite (WAL mode) |
| Migrations | Alembic |
| PDF | WeasyPrint |
| Frontend | Jinja2 templates, vanilla JS, CSS |
| Fonts | Barlow / Barlow Condensed (Google Fonts) |
| Container | Docker, Docker Compose |

## Quick Start (Development)

```bash
git clone https://github.com/arshdeepromy/Compliance-Audit-Tool.git
cd Compliance-Audit-Tool
docker compose up -d --build
```

App runs at **http://localhost:5000**

Default login: `admin` / `admin`

## Data Persistence & Storage

All user data is stored on the host filesystem via Docker bind mounts. This means your data lives outside the container and survives rebuilds, restarts, and updates.

### What gets persisted

| Data | Host Path | Container Path | Description |
|------|-----------|----------------|-------------|
| SQLite Database | `./instance/totika.db` | `/app/instance/totika.db` | All audits, users, scores, settings, risk data |
| File Uploads | `./uploads/` | `/app/uploads/` | Evidence attachments, branding logos |
| Backups | `./backups/` | `/app/backups/` | Automatic DB + upload backups from deploy script |

### Important rules

- **NEVER run `docker compose down -v`** — the `-v` flag deletes volumes and can wipe your data
- **NEVER run `docker system prune --volumes`** on the Pi without checking what it will remove
- **NEVER delete the `instance/` or `uploads/` directories** on the host
- The deploy script uses `docker compose up -d --build --force-recreate` (not `down`) to avoid data loss
- The `.dockerignore` file prevents `instance/`, `uploads/`, and `backups/` from being copied into the Docker image

### Manual backup

```bash
# Backup database
cp instance/totika.db backups/manual_backup_$(date +%Y%m%d).db

# Backup uploads
tar -czf backups/uploads_manual_$(date +%Y%m%d).tar.gz uploads/
```

### Manual restore

```bash
# Stop the container first
sudo docker compose stop web

# Restore database from a backup
sudo cp backups/<backup_filename>.db instance/totika.db

# Restart
sudo docker compose start web
```

## Raspberry Pi Deployment

### Prerequisites

```bash
# Install Docker (one-time)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, then:
sudo apt install docker-compose-plugin
```

### First Deploy

```bash
git clone https://github.com/arshdeepromy/Compliance-Audit-Tool.git
cd Compliance-Audit-Tool
sudo bash deploy.sh update
```

App runs at **http://\<pi-ip\>:5000**

### Production Configuration

Edit `docker-compose.yml` environment variables before first deploy:

```yaml
environment:
  - FLASK_DEBUG=0
  - SECRET_KEY=your-random-secret-key-here
  - DEFAULT_ADMIN_PASSWORD=a-strong-password
  - BEHIND_PROXY=true          # if behind Nginx/reverse proxy
  - APP_BASE_URL=https://audit.example.com  # optional: explicit base URL
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Reverse Proxy Setup

The app supports running behind Nginx Proxy Manager or any reverse proxy. Set `BEHIND_PROXY=true` in docker-compose.yml (already enabled by default). The app auto-detects the domain from `X-Forwarded-Host` and `X-Forwarded-Proto` headers for correct URL generation in emails and password reset links.

If auto-detection doesn't work, set `APP_BASE_URL` explicitly:
```yaml
- APP_BASE_URL=https://audit.yourdomain.com
```

## Deploy Script

The included `deploy.sh` handles updates, rollbacks, and monitoring. Always run with `sudo bash`:

```bash
sudo bash deploy.sh update     # Pull latest code, backup, rebuild
sudo bash deploy.sh rollback   # Revert to previous version + restore DB
sudo bash deploy.sh status     # Show current deployment state
sudo bash deploy.sh logs       # Tail container logs (Ctrl+C to stop)
```

### How `update` works

1. Saves the current git commit hash for rollback
2. Backs up the SQLite database (with timestamp + commit tag)
3. Backs up the uploads directory (as .tar.gz)
4. Pulls latest code from GitHub (auto-stashes local changes)
5. Re-launches itself with the updated script (so new deploy logic takes effect)
6. Rebuilds the Docker container in-place (no `docker compose down`)
7. Waits 30 seconds + retries for the container to be healthy
8. Verifies the database file wasn't corrupted or lost
9. If the DB shrunk by more than 50%, auto-restores from backup

### How `rollback` works

1. Stops the container (does NOT remove it)
2. Restores the database from the most recent backup
3. Restores uploads from the most recent backup
4. Reverts the code to the previous commit
5. Rebuilds and restarts the container

### Backup management

- DB backups: `backups/totika_YYYYMMDD_HHMMSS_<commit>.db` — last 10 kept
- Upload backups: `backups/uploads_YYYYMMDD_HHMMSS_<commit>.tar.gz` — last 5 kept
- Uses `sqlite3 .backup` command when available (safe even while DB is in use)
- All backups are gitignored and stay local on the Pi

### Troubleshooting

If the container fails to start after an update:

```bash
# Check container logs
docker logs compliance-audit-tool-web-1 --tail 50

# Check if the container is running
sudo docker compose ps

# Manual rollback
sudo bash deploy.sh rollback

# If rollback fails, restore manually:
sudo docker compose stop web
sudo cp backups/<latest_backup>.db instance/totika.db
sudo docker compose start web
```

## Project Structure

```
├── app/
│   ├── blueprints/        # Flask route handlers
│   │   ├── admin.py       # Admin panel (branding, users, SMTP, templates)
│   │   ├── api.py         # JSON API (scoring, actions, imports, scoping)
│   │   ├── audits.py      # Audit lifecycle (CRUD, state machine, PDF)
│   │   ├── auth.py        # Authentication (login, MFA, password reset/change)
│   │   ├── risks.py       # Enterprise risk management
│   │   └── templates.py   # Template management
│   ├── models/            # SQLAlchemy models
│   ├── seed_data/         # Built-in compliance framework definitions
│   ├── services/          # Business logic (importer, PDF, mailer, compliance)
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/            # CSS, JS
│   └── utils/             # RBAC, auth, logging, proxy helpers
├── migrations/versions/   # Alembic migration scripts (001–008)
├── instance/              # SQLite database (gitignored, persisted via bind mount)
├── uploads/               # User uploads (gitignored, persisted via bind mount)
├── backups/               # Automatic backups (gitignored, local to Pi)
├── tests/                 # Unit and property-based tests
├── deploy.sh              # Pi deployment script
├── docker-compose.yml
├── Dockerfile
├── .dockerignore          # Prevents data dirs from being copied into image
└── requirements.txt
```

## Database Migrations

Migrations run automatically on container startup via Alembic. The current migration chain:

| Migration | Description |
|-----------|-------------|
| 001 | Initial schema (users, templates, audits, scores, sign-off) |
| 002 | Passkey and dual MFA support |
| 003 | Compliance framework (scoping questions, rules, applicability) |
| 004 | Action tracking (corrective actions, action evidence) |
| 005 | Branding header/footer fields |
| 006 | Corrective action rich fields (gap items from v3) |
| 007 | Info-only criteria and info_answer |
| 008 | Enterprise risk management (categories, risks, mitigations, reviews) |

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin | Admin |

**Change the admin password immediately after first login in production.**

Users can change their own password via the 🔒 icon in the navigation bar, or at `/password/change`.

## Email & Notifications

Configure SMTP in Admin → SMTP Settings. Once configured:

- Welcome emails are sent automatically when new user accounts are created
- Password reset emails use the detected domain (or `APP_BASE_URL` if set)
- All emails use branded HTML templates with your company name and colours

## Risk Management

The risk module follows ISO 31000 principles:

- **Likelihood scale**: 1 (Rare) → 5 (Almost Certain)
- **Impact scale**: 1 (Insignificant) → 5 (Catastrophic)
- **Risk score**: Likelihood × Impact
- **Risk levels**: Low (1–4), Medium (5–9), High (10–15), Critical (16–25)
- **Treatment types**: Avoid, Reduce, Transfer, Accept
- **Statuses**: Open, Mitigating, Monitoring, Closed, Accepted

Seeded business area categories: Health & Safety, IT Security, Privacy & Data Protection, Environmental, Financial, Operational, Legal & Compliance, Strategic, Reputational, Human Resources.

## License

Private repository. All rights reserved.
