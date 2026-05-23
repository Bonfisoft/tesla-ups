"""Tests for the native NUT protocol server."""

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
        sock.sendall(b"LIST VAR powerwall\n")

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
        assert "BEGIN LIST VAR powerwall" in response_str
        assert "ups.status" in response_str
        assert "battery.charge" in response_str
        assert "END LIST VAR powerwall" in response_str

        sock.close()
    finally:
        server.stop()
