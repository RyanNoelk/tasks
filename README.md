# Daily Tasks

Self-hosted, single-user daily checklist. Define a list of tasks once; every day the same list shows up unchecked. Check things off as you go. At local midnight the next day starts fresh — yesterday's state is preserved as history.

No accounts, no cloud, no notifications. One Docker container, one SQLite file.

---

## Features

- **Recurring daily checklist** — one template list, auto-resets every day at local midnight.
- **One-off tasks** — add ad-hoc tasks that stay on the Today page until completed, then move to a separate "Done" history page.
- **History** — view any past date's completions read-only.
- **Multi-device access** — run on one host (NAS, home server, spare laptop); reach it from phone, tablet, or any laptop on the same network.
- **Persistent storage** — SQLite file in a bind-mounted `./data` directory. Survives container rebuilds.
- **No login** — designed for trusted LAN only. Do **not** expose to the public internet.
- **No JS build step** — server-rendered HTML with HTMX for partial updates.

---

## Architecture

```
┌────────────┐   HTTP    ┌──────────────────────────┐
│ Browser    │──────────▶│ FastAPI + Uvicorn        │
│ (HTMX)     │           │  ├─ Jinja2 templates     │
└────────────┘           │  ├─ Routes (REST + HTML) │
                         │  └─ SQLAlchemy ORM       │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │ SQLite (./data/tasks.db) │
                         └──────────────────────────┘
```

| Layer       | Choice                                |
|-------------|---------------------------------------|
| Language    | Python 3.12                           |
| Web         | FastAPI + Uvicorn                     |
| Templates   | Jinja2 (server-rendered)              |
| Interactivity | HTMX (CDN, no bundler)              |
| ORM         | SQLAlchemy 2.x                        |
| Migrations  | Alembic                               |
| Database    | SQLite (single file)                  |
| Container   | Docker + docker compose               |

---

## Data Model

Three tables. Templates + completions cover the recurring daily list. `one_off_task` covers ad-hoc tasks that aren't tied to a date.

### `task_template`

| Column             | Type       | Notes                                                |
|--------------------|------------|------------------------------------------------------|
| `id`               | INTEGER PK | autoincrement                                        |
| `name`             | TEXT       | not null                                             |
| `position`         | INTEGER    | display order                                        |
| `active`           | BOOLEAN    | soft-delete; false = hidden today                    |
| `created_at`       | TIMESTAMP  | UTC                                                  |
| `schedule_rrule`   | TEXT       | RFC 5545 RRULE string (e.g., `FREQ=DAILY`)           |
| `schedule_dtstart` | DATE       | anchor date for INTERVAL (every-N-weeks)             |

### `task_completion`

| Column        | Type      | Notes                                 |
|---------------|-----------|---------------------------------------|
| `id`          | INTEGER PK | autoincrement                        |
| `template_id` | INTEGER FK → `task_template.id`       |
| `date`        | DATE      | local date (per `TZ`)                 |
| `completed_at`| TIMESTAMP | UTC, when the box was checked         |
| **UNIQUE**    | (`template_id`, `date`)               |

**Soft-delete rationale:** if you delete a template later, history pages would lose the task name. Marking `active=false` keeps history readable while removing the task from today's list.

### `one_off_task`

| Column         | Type       | Notes                                          |
|----------------|------------|------------------------------------------------|
| `id`           | INTEGER PK | autoincrement                                  |
| `name`         | TEXT       | not null                                       |
| `completed_at` | TIMESTAMP  | nullable; `NULL` = pending, visible on Today   |
| `created_at`   | TIMESTAMP  | UTC                                            |

One-offs are not tied to a date. They appear on `/` until marked complete, then surface on `/one-offs/history` (newest-completed first) where they can be restored or deleted.

---

## Scheduling

Each `task_template` has a schedule defined by an RRULE string + DTSTART
anchor. The Manage page exposes presets that compile to standard RRULE:

| Preset                    | Example RRULE                          |
|---------------------------|----------------------------------------|
| Daily                     | `FREQ=DAILY`                           |
| Weekdays                  | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR`     |
| Weekends                  | `FREQ=WEEKLY;BYDAY=SA,SU`              |
| Specific days of week     | `FREQ=WEEKLY;BYDAY=MO,WE,FR`           |
| Every N weeks             | `FREQ=WEEKLY;INTERVAL=2;BYDAY=MO`      |
| Monthly on day            | `FREQ=MONTHLY;BYMONTHDAY=15` (or `-1` for last day) |
| Nth weekday of month      | `FREQ=MONTHLY;BYDAY=1MO` / `-1FR`      |

A task is shown for a given date if `schedule_rrule` produces an occurrence
on that date (evaluated via `python-dateutil`).

The `schedule_dtstart` defines the anchor for `INTERVAL` rules — e.g.,
"every 3 weeks starting Mon Jun 1" means rows fall on Jun 1, Jun 22, Jul 13.

## Daily Reset Semantics

There is no cron job. The reset is implicit:

> The checklist for any given day is the set of `active=true` templates joined against `task_completion` rows for that date. If no completion row exists for `(template, date)`, the box is unchecked.

When the local clock crosses midnight, queries against `today()` return a new date and the checklist appears empty again. Past dates remain queryable through `/history`.

The "local" timezone is set by the `TZ` environment variable (default `UTC`).

---

## HTTP Routes

| Method | Path                                | Returns                |
|--------|-------------------------------------|------------------------|
| GET    | `/`                                 | today's checklist (HTML) |
| POST   | `/tasks/{id}/toggle?date=YYYY-MM-DD` | updated row partial    |
| GET    | `/manage`                           | template CRUD page     |
| POST   | `/templates`                        | new row partial        |
| PATCH  | `/templates/{id}`                   | updated row partial    |
| DELETE | `/templates/{id}`                   | empty (soft-deletes)   |
| GET    | `/history?date=YYYY-MM-DD`          | read-only past day     |
| POST   | `/one-offs`                         | create one-off (form `name`) |
| POST   | `/one-offs/{id}/complete`           | mark one-off done; row swaps out |
| POST   | `/one-offs/{id}/restore`            | clear `completed_at` (from Done page) |
| DELETE | `/one-offs/{id}`                    | hard delete one-off     |
| GET    | `/one-offs/history`                 | completed one-offs (Done page) |
| GET    | `/healthz`                          | `{"status":"ok"}`      |

`POST /tasks/{id}/toggle` inserts a completion row if absent, deletes if present. HTMX swaps the row in place — no full page reload.

---

## Configuration

All via environment variables (set in `docker-compose.yml`):

| Variable    | Default          | Purpose                                |
|-------------|------------------|----------------------------------------|
| `TZ`        | `UTC`            | Defines local midnight for reset       |
| `DB_PATH`   | `/data/tasks.db` | SQLite file location inside container  |
| `PORT`      | `8000`           | HTTP listen port                       |

---

## Run It

```bash
git clone <this-repo>
cd tasks
docker compose up -d --build
```

Then open `http://<host>:8000` from any device on the LAN.

To find the host IP from another device: `ip addr` (Linux) or `ifconfig` (macOS).

To stop:
```bash
docker compose down
```

---

## Backup

The entire app state is one file: `./data/tasks.db`.

```bash
cp ./data/tasks.db ./backups/tasks-$(date +%F).db
```

For continuous replication, [Litestream](https://litestream.io) can stream SQLite to S3/SFTP. Not included by default.

---

## Development

### Hot-reload via Docker

`docker-compose.yml` bind-mounts `./app`, `./alembic`, and `alembic.ini` into
the container and runs uvicorn with `--reload --reload-dir /app/app`. Edit any
file under `./app/` and uvicorn restarts inside the container automatically.

```bash
docker compose up --build
```

### Without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DB_PATH=./data/tasks.db TZ=America/New_York
alembic upgrade head
uvicorn app.main:app --reload
```

Run migrations after model changes:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

---

## Limitations

- **No authentication.** Anyone who can reach the port can edit your tasks. Run on trusted LAN only; never port-forward to the public internet.
- **Single user.** No concept of accounts, sharing, or multi-tenancy.
- **No notifications.** Browser-only; doesn't ping you.
- **Single instance.** Running multiple containers against the same SQLite file is unsupported (would risk write conflicts). Sync via syncing the DB file is not a supported deployment.

---

## File Layout

```
tasks/
├── README.md
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── services.py
│   ├── time.py
│   ├── routes/
│   │   ├── pages.py
│   │   ├── tasks.py
│   │   └── templates.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── manage.html
│   │   ├── history.html
│   │   └── partials/
│   └── static/
│       └── styles.css
└── data/
    └── tasks.db          # gitignored, created at runtime
```
