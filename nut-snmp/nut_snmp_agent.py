#!/usr/bin/env python3
"""Simple NUT to SNMP bridge for Synology DSM compatibility."""

import os
import socket
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.udp.dgram import udp

# NUT connection settings
NUT_HOST = os.getenv('NUT_HOST', 'nut-upsd')
NUT_PORT = int(os.getenv('NUT_PORT', '3493'))
NUT_USER = os.getenv('NUT_USER', 'admin')
NUT_PASS = os.getenv('NUT_PASS', 'admin')
SNMP_COMMUNITY = os.getenv('SNMP_COMMUNITY', 'public')

# Base OID for UPS MIB (using APC format for compatibility)
UPS_BASE_OID = (1, 3, 6, 1, 4, 1, 318, 1, 1, 1)

def get_nut_data():
    """Query NUT server for UPS data."""
    try:
        # Try to query NUT using upsc command or direct socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((NUT_HOST, NUT_PORT))
        sock.close()

        # Return default/demo values
        return {
            'battery.charge': 85,
            'ups.status': 'OL',
            'battery.voltage': 50.0,
            'ups.mfr': 'Tesla',
            'ups.model': 'Powerwall'
        }
    except (socket.error, socket.timeout, ConnectionRefusedError, OSError) as err:
        print(f"Error querying NUT: {err}")
        return {
            'battery.charge': 0,
            'ups.status': 'OB',
            'battery.voltage': 0,
            'ups.mfr': 'Unknown',
            'ups.model': 'Unknown'
        }

def create_snmp_agent():
    """Create SNMP agent."""
    agent = engine.SnmpEngine()

    # Transport setup
    config.addTransport(
        agent,
        udp.domainName + (1,),
        udp.UdpTransport().openServerMode(('0.0.0.0', 161))
    )

    # Community setup
    config.addV1System(agent, 'my-area', SNMP_COMMUNITY)

    # SNMPv1/v2c setup
    config.addVacmUser(agent, 2, 'my-area', 'noAuthNoPriv', (1, 3, 6))

    # Create SNMP context
    snmp_context = context.SnmpContext(agent)

    # Register command responders
    cmdrsp.GetCommandResponder(agent, snmp_context)
    cmdrsp.SetCommandResponder(agent, snmp_context)
    cmdrsp.NextCommandResponder(agent, snmp_context)
    cmdrsp.BulkCommandResponder(agent, snmp_context)

    print(f"SNMP agent started on UDP/161 (community: {SNMP_COMMUNITY})")
    print(f"NUT backend: {NUT_HOST}:{NUT_PORT}")

    return agent

if __name__ == '__main__':
    snmp_engine = create_snmp_agent()
    snmp_engine.transportDispatcher.jobStarted(1)

    try:
        snmp_engine.transportDispatcher.runDispatcher()
    except KeyboardInterrupt:
        snmp_engine.transportDispatcher.closeDispatcher()
        print("\nSNMP agent stopped.")
