"""Tests for the native NUT protocol server."""

import os
import socket
import time

import pytest

from nut_server import NUTServer


# ============================================================================
# NUT Server Integration Tests
# ============================================================================

@pytest.mark.integration
def test_nut_server_start_stop():
    """Test server can start and stop."""
    server = NUTServer(host='127.0.0.1', port=0)  # Port 0 for auto-assign
    server.start()

    assert server.is_running()

    server.stop()
    # Give it a moment to shut down
    time.sleep(0.1)

    assert not server.is_running()


@pytest.mark.integration
def test_nut_server_accepts_connection():
    """Test server accepts TCP connections."""
    server = NUTServer(host='127.0.0.1', port=0)
    server.start()

    # Get the actual port
    actual_port = server._server.server_address[1]

    try:
        # Connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', actual_port))

        # Send VER command
        sock.sendall(b"VER\n")

        # Receive response
        response = sock.recv(1024).decode('utf-8')
        assert "Tesla-UPS-Bridge" in response

        sock.close()
    finally:
        server.stop()


@pytest.mark.integration
def test_nut_server_list_var():
    """Test LIST VAR via real TCP connection."""
    server = NUTServer(host='127.0.0.1', port=0)
    server.start()

    actual_port = server._server.server_address[1]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', actual_port))

        # Send LIST VAR command
        sock.sendall(b"LIST VAR ups\n")

        # Receive response (may take multiple reads)
        response = b""
        sock.settimeout(1)
        try:
            while True:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
        except socket.timeout:
            pass

        response_str = response.decode('utf-8')
        assert "BEGIN LIST VAR ups" in response_str
        assert "ups.status" in response_str
        assert "battery.charge" in response_str
        assert "END LIST VAR ups" in response_str

        sock.close()
    finally:
        server.stop()


@pytest.mark.integration
def test_nut_server_custom_ups_name():
    """Test custom UPS name via environment variable."""
    # Set custom UPS name
    os.environ["NUT_UPS_NAME"] = "myups"
    os.environ["NUT_USERNAME"] = "testuser"
    os.environ["NUT_PASSWORD"] = "testpass"

    # Re-import to pick up environment variables
    import importlib
    import nut_server
    importlib.reload(nut_server)

    server = nut_server.NUTServer(host='127.0.0.1', port=0)
    server.start()

    actual_port = server._server.server_address[1]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', actual_port))

        # Send LIST UPS command
        sock.sendall(b"LIST UPS\n")

        response = b""
        sock.settimeout(1)
        try:
            while True:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
        except socket.timeout:
            pass

        response_str = response.decode('utf-8')
        assert "UPS myups" in response_str

        sock.close()
    finally:
        server.stop()
        # Clean up environment
        del os.environ["NUT_UPS_NAME"]
        del os.environ["NUT_USERNAME"]
        del os.environ["NUT_PASSWORD"]
        importlib.reload(nut_server)


@pytest.mark.integration
def test_nut_server_authentication_success():
    """Test successful authentication with correct credentials."""
    os.environ["NUT_USERNAME"] = "testuser"
    os.environ["NUT_PASSWORD"] = "testpass"

    import importlib
    import nut_server
    importlib.reload(nut_server)

    server = nut_server.NUTServer(host='127.0.0.1', port=0)
    server.start()

    actual_port = server._server.server_address[1]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', actual_port))

        # Send LOGIN command with correct credentials
        sock.sendall(b"LOGIN ups testuser testpass\n")

        response = sock.recv(1024).decode('utf-8')
        assert "OK" in response

        sock.close()
    finally:
        server.stop()
        del os.environ["NUT_USERNAME"]
        del os.environ["NUT_PASSWORD"]
        importlib.reload(nut_server)


@pytest.mark.integration
def test_nut_server_authentication_failure():
    """Test authentication failure with wrong credentials."""
    os.environ["NUT_USERNAME"] = "testuser"
    os.environ["NUT_PASSWORD"] = "testpass"

    import importlib
    import nut_server
    importlib.reload(nut_server)

    server = nut_server.NUTServer(host='127.0.0.1', port=0)
    server.start()

    actual_port = server._server.server_address[1]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', actual_port))

        # Send LOGIN command with wrong credentials
        sock.sendall(b"LOGIN ups wronguser wrongpass\n")

        response = sock.recv(1024).decode('utf-8')
        assert "ERR ACCESS-DENIED" in response

        sock.close()
    finally:
        server.stop()
        del os.environ["NUT_USERNAME"]
        del os.environ["NUT_PASSWORD"]
        importlib.reload(nut_server)
