# conduit-haproxy docker image

This image contains the configuration for haproxy used by conduit. This haproxy configuration handles SSH and HTTP traffic.

SSH traffic is load balanced to one or more ssh servers. The non-standard port of 2222 is used for SSH. SSH clients establish tunnels for the purpose of transporting HTTP traffic to the other end.

HTTP traffic is also load balanced to the sshd servers, but in the case of HTTP traffic, it is directed over an established tunnel. An SSH tunnel for any given http host may be connected to any sshd backend. Thus the correct backend must be determined dynamically by haproxy.

Determining which sshd backend should receive HTTP traffic for a given http host is done using an haproxy map. This map is updated using two methods; announce and poll. When an new ssh client connects and establishes a tunnel, the sshd announces the new tunnel to haproxy via it's admin socket. This puts the new tunnel into the map immediately. Additionally, sshd instance also provide and HTTP server that produces a list of all active tunnels on that instance. HAproxy then polls these http endpoints using lua and updates the map.

Using this dual approach means that tunnels become available immediately, but also allow haproxy to rebuild it's map upon restart, and also handles cases where the announcement may fail.

## Using this image

```bash
$ docker -ti homelandsocial/conduit-haproxy
```

### Example docker-compose

[https://raw.githubusercontent.com/homeland-social/conduit/master/docker-compose.yml](https://raw.githubusercontent.com/homeland-social/conduit/master/docker-compose.yml)

## Environment variables

| Name | Description | Default |
| ---- | ----------- | ------- |
| `SSHD_BACKEND` |  | `sshd` |
| `TUNNELS_MAP` |  | `/usr/local/etc/haproxy/tunnels.map` |
| `ANNOUNCE_PORT` |  | `1337` |

## Volumes

| Path | Description |
| ---- | ----------- |
| `/usr/local/etc/haproxy/errors/???.http` | Name file for http status code, such as `404.http` to customize error pages. |
| `/usr/local/etc/haproxy/tunnels.map` | Location of map. Not necessary to be persistent. |
| `/usr/local/etc/haproxy/lua` | Lua code is located here in case you want to customize it. |
| `/etc/haproxy/haproxy.cfg` | HAproxy config file. |
