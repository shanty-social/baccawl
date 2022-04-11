# sshd docker image

This image provides an ssh server implemnted in node.js using ssh2 library. This server supports key authentication and integrates with the homeland social website project to perform key verification.

## Environment variables

| Name | Description | Default |
| ---- | ----------- | ------- |
| `FLASK_WPA_SOCKET_PATH` | Not currently used | |
| `FLASK_NDS_SOCKET_PATH` | Not currently used | |
| `FLASK_DOCKER_SOCKET_PATH` | Docker socket path | `/var/run/sockets/docker.sock` |
| `FLASK_LOG_LEVEL` | Logging level | `DEBUG` |
| `FLASK_DEBUG` | Flask debugging; `true` or `false` | `false` |
| `FLASK_HOST` | Bind to address | `0.0.0.0` |
| `FLASK_PORT` | Bind to port, port to expose | `8000` |
| `FLASK_DB_PATH` | Path where sqlite database is stored | `/var/lib/console/db.sqlite3` |
| `FLASK_UUID_PATH` | Path where console stores it's id | `/var/lib/console/console.uuid` |
| `FLASK_CACHE_TYPE` | Cache driver | `flask_caching.contrib.uwsgicache.UWSGICache` |
| `FLASK_SHANTY_OAUTH_CONFIG_URL` | URL of provider configuration | `https://www.homeland-social.com/api/oauth/config.json` |
| `FLASK_SHANTY_BASE_URL` | URL of provider | `https://www.homeland-social.com/`
| `CERT_DIR` | Not currently used | `/var/lib/certs` |
| `SSH_HOST` | SSH host address | `ssh.homeland-social.com` |
| `SSH_PORT` | SSH port | `2222` |
| `SSH_KEY_FILE` | SSH client key path | `/var/lib/console/client.key` |
| `SSH_HOST_KEYS_FILE` | SSH host key path (fetched automatically) | `/var/lib/console/authorized_keys` |

## Volumes

| Path | Purpose |
| ---- | ------- |
| `/var/run/sockets/docker.sock` | Allows console to list available containers, path should match `FLASK_DOCKER_SOCKET_PATH` config variable |
| `/var/lib/console/` | Data storage path |
