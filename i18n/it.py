"""Italian translations for Tesla UPS Bridge."""

TRANSLATIONS = {
    # Dashboard
    "dashboard.title": "Stato UPS Bridge",
    "dashboard.provider": "Provider",
    "dashboard.grid": "Rete",
    "dashboard.battery": "Batteria",
    "dashboard.last_notification": "Ultima Notifica",
    "dashboard.refreshing": "Aggiornamento ogni 15 secondi",
    # Status labels
    "status.online": "Online",
    "status.on_battery": "Su Batteria",
    "status.low_battery": "Batteria Scarica",
    "status.unknown": "Sconosciuto",
    # Grid states
    "grid.connected": "Connessa",
    "grid.down": "Interrotta",
    # Email alerts
    "alert.grid_outage": "Rilevata interruzione di rete! Batteria al {soe}%",
    "alert.grid_restored": "Alimentazione di rete ripristinata! Batteria al {soe}%",
    "alert.battery_warning": "Avviso batteria! Batteria al {soe}%",
    "alert.battery_critical": "Batteria critica! Batteria al {soe}% - avvio spegnimento",
    "alert.subject": "Allarme UPS Bridge: Interruzione di Rete",

    # Error messages
    "error.connection": "Connessione al bridge fallita",
    "error.provider": "Errore del provider",
}
