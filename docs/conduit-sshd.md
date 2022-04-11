# conduit-sshd docker image

This image provides an ssh server implemnted in node.js using ssh2 library. This server supports key authentication and integrates with the homeland social website project to perform key verification.

## Using this image

```bash
$ docker run -ti homelandsocial/sshd
```

### Example docker-compose

[https://raw.githubusercontent.com/homeland-social/conduit/master/docker-compose.yml](https://raw.githubusercontent.com/homeland-social/conduit/master/docker-compose.yml)

## Environment variables

| Name | Description | Default |
| ---- | ----------- | ------- |
| `PROXY_HOST` | Bind address for HTTP proxy server. | `0.0.0.0`
| `PROXY_PORT` | Bind port for HTTP proxy server. | `80` |
| `SSHD_HOST` | Bind address for SSH server. | `0.0.0.0` |
| `SSHD_PORT` | Bind port for SSH server. | `22` |`
| `ANNOUNCE_HOST` | Bind address for announce server. | `0.0.0.0` |
| `ANNOUNCE_PORT` | Bind port for announce server. | `1337` |
| `DEBUG` | Controls logging via debug module, use `sshd*` to enable logging. | |
| `AUTORELOAD` | Uses `nodemon` to reload server; `true` or `false` | `false` |
| `SHANTY_URL` | Homeland social website url | https://www.homeland-social.com/ |
| `SSHD_HOST_KEY_DIR` | Location at which to load ssh host keys. | `/etc/sshd/keys/` |
| `HAPROXY_HOSTS` | List of HAproxy hosts, separated by commas. |  |
| `HAPROXY_PORT` | HAproxy admin socket port. | `9999` |
| `MAP_NAME` | Map name to use over HAproxy admin socket. | `/usr/local/etc/haproxy/tunnels.map` |

## Volumes

| Path | Purpose |
| ---- | ------- |
| `/etc/sshd/keys/` | Directory in which sshd host keys are stored. Keys will be generated on startup if they do not exist. |
