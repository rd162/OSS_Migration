# About

That's a usual TTRSS installation, plus feedly theme (font was modified).

# Available environment variables:
- `TT_REFRESH` (default is 5) - interval in minutes between feeds updates
- `TT_DB_HOST` (default is db) - MySQL hostname to connect
- `TT_DB_NAME` (default is ttrss) - MySQL database name
- `TT_DB_USER` (default is root) - MySQL username
- `TT_DB_PASS` (default is ttrss) - MySQL password
- `TT_DOMAIN` - end user domain name to be placed in ttrss `config.php`

# How to start/stop
## Navigate to main dir
```
sudo docker compose up --detach
sudo docker compose down
```

admin:password

