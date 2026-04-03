# 07 — Deployment & Infrastructure Spec

## Deployment Architecture

```
┌──────────────────────────────────────────────────────┐
│                Docker Compose Stack                   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ttrss-app Container        ttrss-db Container       │
│  ┌────────────────────┐    ┌──────────────────┐     │
│  │ PHP 7.4 / Apache   │    │ MariaDB 10.3     │     │
│  │ Port 80 (HTTP)     │    │ Port 3306 (int)  │     │
│  │ /ttrss (docroot)   │    │ ttrss database   │     │
│  │ mod_rewrite        │    │                  │     │
│  │                    │    │ Health check:    │     │
│  │ docker-entrypoint: │    │ mysqladmin ping  │     │
│  │  - gen config.php  │    │ interval: 10s    │     │
│  │  - set permissions │    │ retries: 10      │     │
│  │  - apache2-fgnd    │    └──────────────────┘     │
│  └────────────────────┘                              │
│                                                       │
│  Depends On: ttrss-db (healthy)                      │
└──────────────────────────────────────────────────────┘
```

## Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Legacy image (phusion/baseimage:0.11, runit, nginx+php5-fpm) |
| `Dockerfile.local` | Modern image (php:7.4-apache, mod_rewrite) |
| `docker-compose.yaml` | Production stack (MySQL 5.5 + app) |
| `docker-compose.override.yml` | Local dev (MariaDB 10.3 + health checks) |
| `docker-entrypoint.sh` | Config generation + permission setup |

All paths relative to `source-repos/ttrss-php/`.

## Two Dockerfile Strategies

### Legacy (Dockerfile — runit supervision)
- **Base**: `phusion/baseimage:0.11` (Ubuntu + runit)
- **Services**: nginx + php5-fpm + update-feeds daemon
- **Process supervisor**: runit (`/etc/runit/runsvdir/default`)
- **PHP**: 5.x (php5-fpm, php5-cli, php5-gd, php5-mysql)
- **Web server**: Nginx with FastCGI to PHP-FPM unix socket

### Modern (Dockerfile.local — Apache)
- **Base**: `php:7.4-apache`
- **PHP extensions**: gd, mysqli, pdo_mysql, zip
- **Web server**: Apache with mod_rewrite
- **Single process**: apache2-foreground

## Service Supervision (Legacy — runit)

| Service | Script | Command |
|---------|--------|---------|
| nginx | `service/nginx/run` | `nginx` |
| php5-fpm | `service/php5-fpm/run` | `php5-fpm -F` (foreground) |
| update-feeds | `service/update-feeds/run` | Loop: `php /ttrss/update.php --feeds --quiet`, sleep TT_REFRESH |

## Web Server Configuration

### Nginx (Legacy)
- **File**: `etc/nginx/nginx.conf` + `etc/nginx/sites-enabled/ttrss`
- Worker processes: 1
- Worker connections: 500
- Gzip enabled
- Daemon: off (container logging)
- FastCGI: Unix socket `/var/run/php5-fpm.sock`
- Security: `try_files $uri = 404` (prevent path traversal)

### PHP-FPM (Legacy)
- **File**: `etc/php5/fpm/pool.d/www.conf`
- Pool: www (user/group: www-data)
- Process manager: dynamic
- max_children: 5, start_servers: 2, min_spare: 1, max_spare: 3

## Entrypoint (docker-entrypoint.sh)

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TT_DB_HOST` | db | Database hostname |
| `TT_DB_NAME` | ttrss | Database name |
| `TT_DB_USER` | root | Database user |
| `TT_DB_PASS` | ttrss | Database password |
| `TT_DOMAIN` | localhost | Application domain (SELF_URL_PATH) |
| `TT_REFRESH` | 5 | Feed update interval (minutes) |

### Generated config.php
Entrypoint writes `/ttrss/config.php` from environment variables:
- DB_TYPE: mysql, MYSQL_CHARSET: UTF8
- SINGLE_USER_MODE: false
- AUTH_AUTO_CREATE: true, AUTH_AUTO_LOGIN: true
- PLUGINS: auth_internal, note, updater
- LOG_DESTINATION: sql
- SESSION_COOKIE_LIFETIME: 86400

### Permissions
- App directory: 755
- Cache, lock, feed-icons: 777 (writable by www-data)
- Owner: www-data:www-data

## Docker Compose

### Production (docker-compose.yaml)
```yaml
services:
  ttrss-db:
    image: mysql:5.5
    volumes:
      - db_data:/var/lib/mysql
    # Schema init: ttrss/schema/ttrss_schema_mysql.sql

  ttrss-app:
    build: .
    ports: ["80:80"]
    depends_on: [ttrss-db]
```

### Development Override (docker-compose.override.yml)
```yaml
services:
  ttrss-db:
    image: mariadb:10.3
    healthcheck:
      test: mysqladmin ping -h 127.0.0.1
      interval: 10s, timeout: 5s, retries: 10, start_period: 30s

  ttrss-app:
    build:
      dockerfile: Dockerfile.local
    depends_on:
      ttrss-db:
        condition: service_healthy
    environment:
      TT_DB_HOST, TT_DB_NAME, TT_DB_USER, TT_DB_PASS, TT_DOMAIN, TT_REFRESH
```

## CI/CD Pipeline

### GitLab CI (.gitlab-ci.yml)
```yaml
sonarqube-check:
  image: sonarsource/sonar-scanner-cli:latest
  variables:
    SONAR_USER_HOME: .sonar
    GIT_DEPTH: 0
  cache:
    key: ${CI_JOB_NAME}
    paths: [.sonar/cache]
  script: sonar-scanner
  allow_failure: true  # Non-blocking
```

### SonarQube (sonar-project.properties)
- Project key: PXMT
- Quality gate wait: enabled

## Internationalization

- 18+ locales in `ttrss/locale/{lang}/LC_MESSAGES/`
- gettext-based (.po/.mo files)
- Languages: ca, cs, de, es, fi, fr, hu, it, ja, ko, lv, nb, nl, pl, pt_BR, ru, sv, tr, zh_CN, zh_TW

## Third-Party Libraries (bundled in ttrss/lib/)

| Library | Purpose |
|---------|---------|
| Dojo Toolkit + dijit | Frontend UI framework |
| Prototype.js + Scriptaculous | DOM/AJAX library |
| PHPMailer | Email sending (digests) |
| SimplePie (implied) | RSS/Atom parsing |
| MiniTemplator | Template engine (digests) |
| Mobile_Detect | Device detection |
| phpqrcode | QR code generation (OTP) |
| OTPlib (otphp) | TOTP two-factor auth |
| Text_LanguageDetect | Article language detection |
| PubSubHubbub | Real-time feed push |
| SphinxAPI | Full-text search client |
| JShrink | JavaScript minification |
| gettext | PHP gettext implementation |

## Python Migration Notes

### Deployment Stack
```
Python Migration Target:
├── Dockerfile (python:3.12-slim + gunicorn/uvicorn)
├── docker-compose.yaml (app + db + redis + celery worker)
├── requirements.txt / pyproject.toml
├── gunicorn.conf.py or uvicorn config
└── nginx.conf (reverse proxy)
```

### Key Decisions
- **WSGI/ASGI**: Gunicorn (sync) or Uvicorn (async) behind Nginx
- **Database**: Keep MariaDB/MySQL or migrate to PostgreSQL (recommended)
- **Background worker**: Celery replaces update_daemon2.php
- **Cache**: Redis replaces file-based caching
- **CI/CD**: Adapt GitLab CI for Python (pytest, ruff, mypy, SonarQube)
- **i18n**: Python `gettext` module (compatible with existing .po files)
- **Config**: Environment variables (12-factor) via python-decouple or pydantic-settings
