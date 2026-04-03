# Tiny Tiny RSS (tt-rss)

Standard TTRSS installation with a feedly theme (modified font).

## Stack

- **App**: PHP 7.4 + Apache (`Dockerfile.local`)
- **DB**: MariaDB 10.3 (MySQL 5.5 compatible)
- **Schema**: auto-loaded on first DB start

## Prerequisites

- Docker Desktop (v24+)
- Docker Compose v2

## Build and Run

```sh
docker compose build
docker compose up --detach
```

Open **http://localhost** in your browser.

Default credentials:

| Field    | Value      |
| -------- | ---------- |
| Login    | `admin`    |
| Password | `password` |

## Stop

```sh
docker compose down
```

To also remove the database volume:

```sh
docker compose down -v
```

## Environment Variables

| Variable     | Default     | Description                                 |
| ------------ | ----------- | ------------------------------------------- |
| `TT_REFRESH` | `5`         | Feed update interval (minutes)              |
| `TT_DB_HOST` | `db`        | Database hostname                           |
| `TT_DB_NAME` | `ttrss`     | Database name                               |
| `TT_DB_USER` | `root`      | Database user                               |
| `TT_DB_PASS` | `ttrss`     | Database password                           |
| `TT_DOMAIN`  | `localhost` | Domain placed in `config.php` SELF_URL_PATH |

## Project Structure

```
.
├── Dockerfile.local          # Modern PHP 7.4 + Apache image (replaces EOL phusion/baseimage)
├── docker-compose.yaml       # Base service definitions
├── docker-compose.override.yml  # Local overrides: MariaDB 10.3, healthcheck, build target
├── docker-entrypoint.sh      # Generates config.php from env vars, sets permissions
├── ttrss/                    # TTRSS PHP application
│   ├── schema/
│   │   └── ttrss_schema_mysql.sql  # Auto-imported into DB on first start
│   ├── cache/                # Writable cache dirs (images, upload, export, js)
│   ├── lock/                 # Writable lock dir
│   └── feed-icons/           # Writable feed icons dir
└── etc/                      # Original nginx/php5 config (reference only)
```

## Notes

- The original `Dockerfile` used `phusion/baseimage:0.11` (Ubuntu 14.04, EOL).
  `Dockerfile.local` replaces it with `php:7.4-apache` which has ARM64 support
  and current security patches.
- `docker-compose.override.yml` is picked up automatically by `docker compose`.
  It upgrades the DB to `mariadb:10.3` (the original `mysql:5.5` has no ARM64 image)
  and adds a DB healthcheck so the app waits for the DB before starting.
- `config.php` is generated at container startup from environment variables —
  do not create it manually.
