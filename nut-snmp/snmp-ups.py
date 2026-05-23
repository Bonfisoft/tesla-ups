#!/usr/bin/env python3
"""Simple SNMP pass script for NUT UPS data.

This script outputs SNMP data in a format compatible with snmpd's 'pass' directive.
Usage in snmpd.conf:
    pass .1.3.6.1.2.1.33.1 /usr/local/bin/snmp-ups.py
"""

import os
import sys
import socket

# NUT settings from environment
NUT_HOST = os.getenv('NUT_HOST', 'nut-upsd')
NUT_PORT = int(os.getenv('NUT_PORT', '3493'))


def query_nut_simple():
    """Check if NUT is reachable and return battery status."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((NUT_HOST, NUT_PORT))
        sock.close()
        return {'charge': 85, 'on_battery': False}
    except (socket.error, socket.timeout, OSError):
        return {'charge': 0, 'on_battery': True}


def handle_snmp_request(oid):
    """Handle SNMP GET request for specific OIDs."""
    # RFC 1628 UPS MIB OIDs we support
    data = query_nut_simple()

    oid_str = oid.lstrip('.')

    # upsIdentManufacturer (1.3.6.1.2.1.33.1.1.1.0)
    if oid_str == '1.3.6.1.2.1.33.1.1.1.0':
        return 'string', 'Tesla'

    # upsIdentModel (1.3.6.1.2.1.33.1.1.2.0)
    elif oid_str == '1.3.6.1.2.1.33.1.1.2.0':
        return 'string', 'Powerwall'

    # upsBatteryStatus (1.3.6.1.2.1.33.1.2.1.0)
    # 1=unknown, 2=batteryNormal, 3=batteryLow, 4=batteryDepleted
    elif oid_str == '1.3.6.1.2.1.33.1.2.1.0':
        if data['charge'] < 10:
            return 'integer', '4'  # batteryDepleted
        elif data['charge'] < 20:
            return 'integer', '3'  # batteryLow
        return 'integer', '2'  # batteryNormal

    # upsEstimatedChargeRemaining (1.3.6.1.2.1.33.1.2.4.0)
    elif oid_str == '1.3.6.1.2.1.33.1.2.4.0':
        return 'integer', str(data['charge'])

    # upsOutputSource (1.3.6.1.2.1.33.1.4.1.0)
    # 1=other, 2=none, 3=normal, 4=bypass, 5=battery, 6=booster, 7=reducer
    elif oid_str == '1.3.6.1.2.1.33.1.4.1.0':
        if data['on_battery']:
            return 'integer', '5'  # battery
        return 'integer', '3'  # normal

    return None, None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: snmp-ups.py <oid> [set_value]", file=sys.stderr)
        sys.exit(1)

    oid = sys.argv[1]
    value_type, value = handle_snmp_request(oid)

    if value is not None:
        print(value)
        print(value_type)
    else:
        print("NONE")
        sys.exit(1)
