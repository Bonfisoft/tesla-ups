"""English translations for Tesla UPS Bridge."""

TRANSLATIONS = {
    # Dashboard
    "dashboard.title": "UPS Bridge Status",
    "dashboard.provider": "Provider",
    "dashboard.grid": "Grid",
    "dashboard.battery": "Battery",
    "dashboard.last_notification": "Last Notification",
    "dashboard.refreshing": "Refreshing every 15 seconds",
    
    # Status labels
    "status.online": "Online",
    "status.on_battery": "On Battery",
    "status.low_battery": "Low Battery",
    "status.unknown": "Unknown",
    
    # Grid states
    "grid.connected": "Connected",
    "grid.down": "Down",
    
    # Email alerts
    "alert.grid_outage": "Grid outage detected! Battery at {soe}%",
    "alert.grid_restored": "Grid power restored! Battery at {soe}%",
    "alert.battery_warning": "Battery warning! Battery at {soe}%",
    "alert.battery_critical": "Battery critical! Battery at {soe}% - initiating shutdown",
    "alert.subject": "UPS Bridge Alert: Grid Outage",
    
    # Error messages
    "error.connection": "Failed to connect to bridge",
    "error.provider": "Provider error",
}
