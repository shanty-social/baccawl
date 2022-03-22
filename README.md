# conduit
Traffic conduit for homeland social.

This repository contains all the components necessary for routing web traffic from homeland social servers to user servers.

Here you will find:
 - A Python client library that maintains an SSH connection and multiple tcpip
   tunnels.
 - A nodejs ssh server that handles the server-side of the SSH connection.
 - An example haproxy configuration that utilizes LUA to route traffic
   appropriately.
 - A build system that publishes docker images for all of the above.
