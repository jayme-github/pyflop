#!/usr/bin/env python3

import glob
import subprocess
from typing import Iterable
from dataclasses import dataclass
from ipaddress import IPv4Address
from contextlib import contextmanager
import argparse


FIRST_IP = IPv4Address("10.10.0.1")
SCHEME_MAP = {80: "http://", 443: "https://", 5900: "vnc://", 3389: "rdp://"}


@dataclass
class Tunnel:
    local_port: int
    remote_host: str
    remote_port: int

    def __str__(self):
        return f"{self.local_port}:{self.remote_host}:{self.remote_port}"


class Interface:
    name: str
    number: int
    ipv4: IPv4Address

    def __init__(self):
        self.number = self.get_next_available_interface_number()
        self.name = f"pyflop{self.number}"
        self.ipv4 = FIRST_IP + self.number

    def __str__(self):
        return f"{self.name} ({self.ipv4})"

    def get_next_available_interface_number(self) -> int:
        # Get the next free interface number from /sys/class/net/pyflop*
        interfaces = glob.glob("/sys/class/net/pyflop*")
        interface_numbers = [
            int(interface.split("pyflop")[1]) for interface in interfaces
        ]
        next_available_interface = (
            max(interface_numbers) + 1 if interface_numbers else 0
        )
        if next_available_interface >= 255:
            raise ValueError("No more interfaces available")
        return next_available_interface

    @contextmanager
    def create_interface(self):
        # Create a new interface and yield the interface instance
        try:
            subprocess.run(f"sudo ip link add {self.name} type dummy", shell=True)
            subprocess.run(
                f"sudo ip addr add {self.ipv4}/24 dev {self.name}", shell=True
            )
            subprocess.run(f"sudo ip link set {self.name} up", shell=True)
            yield self
        finally:
            subprocess.run(f"sudo ip link del {self.name}", shell=True)


def create_tunnel(interface: Interface, tunnels: Iterable[Tunnel], remote: str):
    # Create a ssh new tunnel using the interface, local_port, remote_host, and remote_port
    tunnels_str = " -L".join([f" {interface.ipv4}:{str(t)}" for t in tunnels])
    command = f"ssh -N -L{tunnels_str} {remote}"
    try:
        subprocess.run(command, shell=True)
    except KeyboardInterrupt:
        return


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SSH port forwarding using local dummy interfaces"
    )
    tunnels_arg = parser.add_argument(
        "-L",
        dest="tunnels",
        metavar="[local_port:]remote_host:remote_port",
        action="append",
        help="Specify one or more tunnels",
        required=True,
    )
    parser.add_argument(dest="remote", help="Remote host")

    args = parser.parse_args()

    tunnels = []
    for tunnel_str in args.tunnels:
        split = tunnel_str.split(":")
        if len(split) == 2:
            remote_host, remote_port = split
            local_port = remote_port
        elif len(split) == 3:
            local_port, remote_host, remote_port = split
        else:
            raise argparse.ArgumentError(
                tunnels_arg, "Invalid number of parameters for tunnel format"
            )

        try:
            tunnel = Tunnel(
                local_port=int(local_port),
                remote_host=remote_host,
                remote_port=int(remote_port),
            )
            tunnels.append(tunnel)
        except ValueError as e:
            raise argparse.ArgumentError(tunnels_arg, f"Invalid tunnel format: {e}")
    args.tunnels = tunnels
    return args


def main():
    args = parse_arguments()

    with Interface().create_interface() as interface:
        for tunnel in args.tunnels:
            scheme = SCHEME_MAP.get(tunnel.local_port, "")
            print(
                f"Tunnel created: {scheme}{interface.ipv4}:{tunnel.local_port}"
                f" -> {tunnel.remote_host}:{tunnel.remote_port}"
            )
        create_tunnel(interface, args.tunnels, args.remote)


if __name__ == "__main__":
    main()
