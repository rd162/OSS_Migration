#!/bin/bash
set -e

db_host=${TT_DB_HOST:-db}
db_name=${TT_DB_NAME:-ttrss}
db_user=${TT_DB_USER:-root}
db_pass=${TT_DB_PASS:-ttrss}
domain=${TT_DOMAIN:-localhost}
php=$(which php)

echo "Writing /ttrss/config.php..."
cat > /ttrss/config.php <<CONFIG
<?php
  define('DB_TYPE', 'mysql');
  define('DB_HOST', '${db_host}');
  define('DB_USER', '${db_user}');
  define('DB_NAME', '${db_name}');
  define('DB_PASS', '${db_pass}');
  define('DB_PORT', '3306');
  define('MYSQL_CHARSET', 'UTF8');
  define('SELF_URL_PATH', 'http://${domain}/');
  define('PHP_EXECUTABLE', '${php}');
  define('FEED_CRYPT_KEY', '');
  define('SINGLE_USER_MODE', false);
  define('SIMPLE_UPDATE_MODE', false);
  define('LOCK_DIRECTORY', 'lock');
  define('CACHE_DIR', 'cache');
  define('ICONS_DIR', "feed-icons");
  define('ICONS_URL', "feed-icons");
  define('AUTH_AUTO_CREATE', true);
  define('AUTH_AUTO_LOGIN', true);
  define('FORCE_ARTICLE_PURGE', 0);
  define('PUBSUBHUBBUB_HUB', '');
  define('PUBSUBHUBBUB_ENABLED', false);
  define('SPHINX_ENABLED', false);
  define('SPHINX_SERVER', 'localhost:9312');
  define('SPHINX_INDEX', 'ttrss, delta');
  define('ENABLE_REGISTRATION', false);
  define('REG_NOTIFY_ADDRESS', 'user@your.domain.dom');
  define('REG_MAX_USERS', 10);
  define('SESSION_COOKIE_LIFETIME', 86400);
  define('SESSION_CHECK_ADDRESS', 1);
  define('SMTP_FROM_NAME', 'Tiny Tiny RSS');
  define('SMTP_FROM_ADDRESS', 'noreply@your.domain.dom');
  define('DIGEST_SUBJECT', '[tt-rss] New headlines for last 24 hours');
  define('SMTP_SERVER', '');
  define('SMTP_LOGIN', '');
  define('SMTP_PASSWORD', '');
  define('SMTP_SECURE', '');
  define('CHECK_FOR_NEW_VERSION', true);
  define('DETECT_ARTICLE_LANGUAGE', false);
  define('ENABLE_GZIP_OUTPUT', false);
  define('PLUGINS', 'auth_internal, note, updater');
  define('LOG_DESTINATION', 'sql');
  define('CONFIG_VERSION', 26);
?>
CONFIG

echo "Creating cache subdirectories..."
mkdir -p /ttrss/cache/images /ttrss/cache/upload /ttrss/cache/export /ttrss/cache/js

echo "Updating permissions on /ttrss..."
chown -R www-data:www-data /ttrss
chmod -R 755 /ttrss
chmod -R 777 /ttrss/cache /ttrss/lock /ttrss/feed-icons

exec "$@"