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
- **SMTP** — Configurable email notifications
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

## Raspberry Pi Deployment

### Prerequisites

```bash
# Install Docker (one-time)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
sudo apt install docker-compose-plugin
```

### First Deploy

```bash
git clone https://github.com/arshdeepromy/Compliance-Audit-Tool.git
cd Compliance-Audit-Tool
chmod +x deploy.sh
./deploy.sh update
```

App runs at **http://\<pi-ip\>:5000**

### Production Configuration

Edit `docker-compose.yml` environment variables before first deploy:

```yaml
environment:
  - FLASK_DEBUG=0
  - SECRET_KEY=your-random-secret-key-here
  - DEFAULT_ADMIN_PASSWORD=a-strong-password
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Deploy Script

The included `deploy.sh` handles updates, rollbacks, and monitoring on the Pi.

### Update Production

After pushing new code to GitHub:

```bash
./deploy.sh update
```

What it does:
1. Saves the current git commit hash (for rollback)
2. Backs up the SQLite database with timestamp + commit tag
3. Pulls latest code from GitHub
4. Rebuilds the Docker container
5. Verifies the app starts successfully
6. Auto-rolls back if the container fails to start

### Rollback

If something goes wrong after an update:

```bash
./deploy.sh rollback
```

What it does:
1. Stops the running container
2. Restores the database from the most recent backup
3. Reverts the code to the previous commit
4. Rebuilds and restarts the container

### Check Status

```bash
./deploy.sh status
```

Shows current git commit, container state, database size, and backup count.

### Tail Logs

```bash
./deploy.sh logs
```

Live-tails the container logs. Press `Ctrl+C` to stop.

### Backup Management

- Database backups are stored in `backups/` with the naming format `totika_YYYYMMDD_HHMMSS_<commit>.db`
- The last 10 backups are kept automatically; older ones are pruned
- Backups are gitignored and stay local on the Pi

## Project Structure

```
├── app/
│   ├── blueprints/        # Flask route handlers
│   │   ├── admin.py       # Admin panel (branding, users, SMTP, templates)
│   │   ├── api.py         # JSON API (scoring, actions, imports, scoping)
│   │   ├── audits.py      # Audit lifecycle (CRUD, state machine, PDF)
│   │   ├── auth.py        # Authentication (login, MFA, password reset)
│   │   ├── risks.py       # Enterprise risk management
│   │   └── templates.py   # Template management
│   ├── models/            # SQLAlchemy models
│   │   ├── audit.py       # Audit, AuditScore, SignOff
│   │   ├── action.py      # CorrectiveAction, ActionEvidence
│   │   ├── risk.py        # Risk, RiskCategory, RiskMitigation, RiskReview
│   │   ├── template.py    # AuditTemplate, Section, Criterion, Anchors
│   │   ├── scoping.py     # ScopingQuestion, ScopingRule, Applicability
│   │   ├── user.py        # User, UserPasskey
│   │   └── settings.py    # BrandingSettings, SMTPSettings
│   ├── seed_data/         # Built-in compliance framework definitions
│   ├── services/          # Business logic (importer, PDF, compliance, scoping)
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/            # CSS, JS
│   └── utils/             # RBAC, auth, logging helpers
├── migrations/versions/   # Alembic migration scripts (001–008)
├── tests/                 # Unit and property-based tests
├── deploy.sh              # Pi deployment script
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Database Migrations

Migrations run automatically on container startup via Alembic. The current migration chain:

| Migration | Description |
|-----------|-------------|
| 001 | Initial schema (users, templates, audits, scores, sign-off) |
| 002 | Evidence attachments |
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

Change the admin password immediately after first login in production.

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
