import subprocess
import sys
import unittest
from argparse import ArgumentError
from ipaddress import IPv4Address
from unittest.mock import call, patch

from pyflop.pyflop import Interface, Tunnel, create_tunnel, parse_arguments


def mock_run_side_effect(cmd, *args, **kwargs):
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")


class TestTunnel(unittest.TestCase):
    def test_tunnel_str(self):
        tunnel = Tunnel(local_port=8080, remote_host="example.com", remote_port=80)
        expected_str = "8080:example.com:80"
        self.assertEqual(str(tunnel), expected_str)


@patch("glob.glob", return_value=["/sys/class/net/pyflop0", "/sys/class/net/pyflop1"])
class TestInterface(unittest.TestCase):
    def test_interface_init(self, mock_glob):
        interface = Interface()
        self.assertEqual(interface.name, "pyflop2")
        self.assertEqual(interface.number, 2)
        self.assertEqual(interface.ipv4, IPv4Address("10.10.0.3"))
        expected_str = f"{interface.name} ({interface.ipv4})"
        self.assertEqual(str(interface), expected_str)

    @patch("subprocess.run", side_effect=mock_run_side_effect)
    def test_create_interface(self, mock_run, mock_glob):
        interface = Interface()

        with interface.create_interface() as created_interface:
            self.assertEqual(created_interface, interface)

        mock_run.call_count = 4
        expected_call_args = [
            call(f"sudo ip link add {interface.name} type dummy", shell=True),
            call(
                f"sudo ip addr add {interface.ipv4}/24 dev {interface.name}", shell=True
            ),
            call(f"sudo ip link set {interface.name} up", shell=True),
            call(f"sudo ip link del {interface.name}", shell=True),
        ]
        self.assertEqual(mock_run.call_args_list, expected_call_args)

    @patch("subprocess.run", side_effect=mock_run_side_effect)
    def test_create_hosts_entry(self, mock_run, mock_glob):
        interface = Interface()
        with interface.create_hosts_entry(("n0.pyflop.com", "n1.pyflop.com")) as created_interface:
            self.assertEqual(created_interface, interface)

        mock_run.call_count = 3
        expected_call_args = [
            call(
                f"sudo {sys.executable} -m hosts.editor add {interface.ipv4} n0.pyflop.com n1.pyflop.com",
                shell=True,
                capture_output=True,
            ),
            call(
                f"sudo {sys.executable} -m hosts.editor delete {interface.ipv4} n0.pyflop.com",
                shell=True,
                capture_output=True,
            ),
            call(
                f"sudo {sys.executable} -m hosts.editor delete {interface.ipv4} n1.pyflop.com",
                shell=True,
                capture_output=True,
            ),
        ]
        self.assertEqual(mock_run.call_args_list, expected_call_args)


@patch("glob.glob", return_value=["/sys/class/net/pyflop0", "/sys/class/net/pyflop1"])
class TestCreateTunnel(unittest.TestCase):
    def test_create_tunnel(self, mock_glob):
        interface = Interface()
        tunnels = [
            Tunnel(local_port=8080, remote_host="example.com", remote_port=80),
        ]
        # Single tunnel
        with patch("subprocess.run", side_effect=mock_run_side_effect) as mock_run:
            create_tunnel(interface, tunnels, remote="somewhere.com")
            mock_run.assert_called_once_with(
                "ssh -N -L 10.10.0.3:8080:example.com:80 somewhere.com", shell=True
            )
        # Multiple tunnels
        tunnels.append(
            Tunnel(local_port=80, remote_host="foo.example.com", remote_port=80)
        )
        with patch("subprocess.run", side_effect=mock_run_side_effect) as mock_run:
            create_tunnel(interface, tunnels, remote="root@somewhere.com")
            mock_run.assert_called_once_with(
                "ssh -N -L 10.10.0.3:8080:example.com:80 -L 10.10.0.3:80:foo.example.com:80 root@somewhere.com",
                shell=True,
            )


class TestParseArguments(unittest.TestCase):
    def test_valid_tunnel_arguments(self):
        test_cases = [
            (
                ["-L", "1234:example.com:22", "remote_host"],
                [Tunnel(1234, "example.com", 22)],
                "remote_host",
            ),
            (
                ["-L", "example.com:22", "remote_host"],
                [Tunnel(22, "example.com", 22)],
                "remote_host",
            ),
            (
                [
                    "-L",
                    "1234:example.com:22",
                    "-L",
                    "5678:another.com:80",
                    "remote_host",
                ],
                [Tunnel(1234, "example.com", 22), Tunnel(5678, "another.com", 80)],
                "remote_host",
            ),
        ]

        for test_args, expected_tunnels, expected_remote in test_cases:
            with self.subTest(test_args=test_args):
                with patch("sys.argv", ["port-forward"] + test_args):
                    args = parse_arguments()
                    self.assertEqual(args.tunnels, expected_tunnels)
                    self.assertEqual(args.remote, expected_remote)

    def test_invalid_tunnel_arguments(self):
        test_cases = [
            (["remote_host"], SystemExit, "", 2),
            (["-L", "foo:123"], SystemExit, "", 2),
            (
                ["-L", "invalid_tunnel_format", "remote_host"],
                ArgumentError,
                "Invalid number of parameters for tunnel format",
                None,
            ),
            (
                ["-L", "nono:foo:123", "remote_host"],
                ArgumentError,
                "Invalid tunnel format: invalid literal for int() with base 10: 'nono'",
                None,
            ),
            (
                ["-L", "123:foo:nono", "remote_host"],
                ArgumentError,
                "Invalid tunnel format: invalid literal for int() with base 10: 'nono'",
                None,
            ),
            (["-h"], SystemExit, "", 0),
        ]

        for (
            test_args,
            expected_exception,
            expected_exception_message,
            expected_exit_code,
        ) in test_cases:
            with self.subTest(test_args=test_args):
                with patch("sys.argv", ["script_name"] + test_args), self.assertRaises(
                    expected_exception, msg="foo"
                ) as cm:
                    parse_arguments()

                if expected_exception_message:
                    self.assertEqual(cm.exception.message, expected_exception_message)
                if expected_exit_code is not None:
                    self.assertEqual(cm.exception.code, expected_exit_code)


if __name__ == "__main__":
    unittest.main()
