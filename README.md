# ρυφλοπόντικας

pyflop creates SSH tunnels using dummy interfaces (so multiple tunnels may use the same port).

This is achieved by adding a dummy interface (`pyflopX`) with an IPv4 IP in the range `10.10.0.0/24` and SSH to create the actual tunnels.

It might be desired to allow users to bind to restricted ports to make this even more usable. You can either do this system wide:

```bash
echo 'net.ipv4.ip_unprivileged_port_start=0' > /etc/sysctl.d/50-unprivileged-ports.conf
sysctl --system
```

Or just allow SSH to bind to privileged ports:

```bash
setcap CAP_NET_BIND_SERVICE=+eip /your/ssh/binary
```