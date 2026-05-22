"""UPS bridge service: polls a battery provider and writes NUT status files.

This service loads a BatteryProvider from providers.yaml, polls it on a
background thread, writes a NUT-compatible UPS status file, and optionally
sends an email alert on grid outages.
"""

import asyncio
import json
import logging
import os
import smtplib
import threading
import time
from contextlib import asynccontextmanager
from email.mime.text import MIMEText
from typing import Any, AsyncGenerator, Dict

import requests

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from i18n import _, detect_language_from_header
from providers import BatteryProvider, BatteryStatus, load_provider
from providers import ConfigError


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialize the battery provider and start the background polling thread."""
    provider = load_provider()
    threading.Thread(target=background_poller, args=(provider,), daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)

STATUS_FILE = "/var/lib/nut/ups/powerwall.dev"
POLL_INTERVAL_SECONDS = 15
LOW_BATTERY_THRESHOLD = 15.0

state: Dict[str, Any] = {
    "status": "OL",
    "soe": 0.0,
    "last_notified": "Never",
    "grid": "Unknown",
    "provider": "unknown",
    "notification_sent": False,
}

# SSE event queue for broadcasting state updates to connected clients
sse_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_env(key: str, default: str = "") -> str:
    """Read a string environment variable with an optional default."""
    return os.getenv(key, default)


def get_env_int(key: str, default: int) -> int:
    """Read an integer environment variable with a default fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"Invalid integer for {key}: {value}") from exc


def load_config() -> Dict[str, Any]:
    """Load runtime configuration from environment variables."""
    auth_type = get_env("EMAIL_AUTH_TYPE", "password").lower()
    return {
        "smtp_server": get_env("SMTP_SERVER", ""),
        "smtp_port": get_env_int("SMTP_PORT", 587),
        "email_user": get_env("EMAIL_USER", ""),
        "email_pass": get_env("EMAIL_PASS", ""),
        "email_token": get_env("EMAIL_TOKEN", ""),
        "email_auth_type": auth_type,
        "notify_to": get_env("NOTIFY_TO", ""),
    }


def _oauth2_auth_string(user: str, token: str) -> str:
    """Build XOAUTH2 authentication string for OAuth 2.0.

    Format: user={user}^Aauth=Bearer {token}^A^A
    (^A represents ASCII 0x01, SOH character)
    """
    auth_string = f"user={user}\x01auth=Bearer {token}\x01\x01"
    return auth_string


def send_alert(message: str, config: Dict[str, Any], lang: str = "en") -> bool:
    """Send an email alert using SMTP settings from configuration.

    Supports both password-based and OAuth 2.0 authentication.
    """
    auth_type = config.get("email_auth_type", "password")

    # Validate required fields based on auth type
    if not config["smtp_server"] or not config["email_user"] or not config["notify_to"]:
        logger.warning("Missing email configuration; skipping alert: %s", message)
        return False

    if auth_type == "oauth2" and not config["email_token"]:
        logger.warning("Missing OAuth 2.0 token; skipping alert")
        return False

    if auth_type == "password" and not config["email_pass"]:
        logger.warning("Missing email password; skipping alert")
        return False

    msg = MIMEText(message)
    msg["Subject"] = _("alert.subject", lang)
    msg["From"] = config["email_user"]
    msg["To"] = config["notify_to"]

    try:
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()

            if auth_type == "oauth2":
                # OAuth 2.0 XOAUTH2 authentication (Gmail, Outlook, etc.)
                auth_string = _oauth2_auth_string(
                    config["email_user"], config["email_token"]
                )
                server.ehlo()
                server.docmd("AUTH", f"XOAUTH2 {auth_string}")
            else:
                # Password-based authentication (traditional or App Password)
                server.login(config["email_user"], config["email_pass"])

            server.send_message(msg)
        state["last_notified"] = time.strftime("%H:%M:%S")
        logger.info("Alert sent via %s: %s", auth_type, message)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP authentication failed (%s): %s", auth_type, exc)
    except smtplib.SMTPException as exc:
        logger.warning("Failed to send email alert: %s", exc)
    except (OSError, ValueError) as exc:
        logger.warning("Unexpected error sending alert: %s", exc)
    return False


def determine_status(
    grid_connected: bool, soe: float, notified: bool
) -> tuple[str, bool]:
    """Determine the UPS status label and whether an outage notification should be sent."""
    if grid_connected:
        return "OL", False

    status = "OB LB" if soe <= LOW_BATTERY_THRESHOLD else "OB"
    should_notify = not notified
    return status, should_notify


def write_nut_status_file(status: str, soe: float) -> None:
    """Write the UPS state file in NUT format for the UPS daemon to read."""
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as handle:
        handle.write(f"ups.status: {status}\n")
        handle.write(f"battery.charge: {soe}\n")


def broadcast_event(event_type: str, data: Dict[str, Any]) -> None:
    """Broadcast an event to all connected SSE clients."""
    try:
        # Use asyncio.run_coroutine_threadsafe to safely add to queue from sync code
        event = {"event": event_type, "data": data, "timestamp": time.time()}
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(sse_queue.put(event), loop)
    except RuntimeError:
        # No event loop running, skip broadcast
        pass


def process_status(
    battery_status: BatteryStatus, config: Dict[str, Any], provider_name: str
) -> None:
    """Update runtime state and send notifications based on provider data."""
    prev_grid = state["grid"]
    prev_status = state["status"]

    state["soe"] = battery_status.soe
    state["grid"] = (
        "SystemGridConnected" if battery_status.grid_connected else "GridDown"
    )
    state["provider"] = provider_name

    # Get language for alerts from environment
    alert_lang = os.getenv("DEFAULT_LANGUAGE", "en")

    new_status, should_notify = determine_status(
        battery_status.grid_connected, battery_status.soe, state["notification_sent"]
    )
    if should_notify and send_alert(
        _("alert.grid_outage", alert_lang, soe=battery_status.soe), config, alert_lang
    ):
        state["notification_sent"] = True

    if battery_status.grid_connected:
        state["notification_sent"] = False

    state["status"] = new_status
    write_nut_status_file(new_status, battery_status.soe)

    # Broadcast SSE event on significant changes
    event_data = dict(state)
    event_data["grid_changed"] = prev_grid != state["grid"]
    event_data["status_changed"] = prev_status != new_status
    broadcast_event("status_update", event_data)


def poll_once(provider: BatteryProvider, config: Dict[str, Any]) -> None:
    """Perform one poll cycle using the active provider and update the state."""
    battery_status = provider.fetch_status()
    process_status(battery_status, config, provider.provider_name)


def background_poller(provider: BatteryProvider) -> None:
    """Run the battery provider poll loop in a background thread."""
    config = load_config()
    while True:
        try:
            poll_once(provider, config)
        except requests.RequestException as exc:
            logger.warning("Provider network error: %s", exc)
        except ValueError as exc:
            logger.warning("Provider data error: %s", exc)
        time.sleep(POLL_INTERVAL_SECONDS)


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Return the latest UPS and battery provider state."""
    return state


def get_status_display(status: str, lang: str) -> str:
    """Get translated status label."""
    if "LB" in status:
        return _("status.low_battery", lang)
    elif "OB" in status:
        return _("status.on_battery", lang)
    elif "OL" in status:
        return _("status.online", lang)
    return _("status.unknown", lang)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, lang: str | None = None) -> str:
    """Render a simple status dashboard for browser access."""
    # Determine language: query param > Accept-Language header > default
    if lang is None:
        accept_language = request.headers.get("accept-language")
        lang = detect_language_from_header(accept_language)

    color = "green" if state["status"] == "OL" else "red"
    provider_name = state.get("provider", "unknown")
    status_display = get_status_display(state["status"], lang)

    # Translate grid state
    grid_key = (
        "grid.connected" if state["grid"] == "SystemGridConnected" else "grid.down"
    )
    grid_display = _(grid_key, lang)

    return f"""
    <html>
        <head>
            <title>{_("dashboard.title", lang)}</title>
            <meta http-equiv="refresh" content="15">
        </head>
        <body style="font-family:sans-serif; text-align:center; padding-top:50px;">
            <h1>{_("dashboard.title", lang)}</h1>
            <p style="color:gray;">{_("dashboard.provider", lang)}: {provider_name}</p>
            <div style="font-size:2em; color:{color}; font-weight:bold;">{status_display}</div>
            <p>{_("dashboard.grid", lang)}: {grid_display}</p>
            <p>{_("dashboard.battery", lang)}: {state['soe']}%</p>
            <p style="color:gray;">
                {_("dashboard.last_notification", lang)}: {state['last_notified']}
            </p>
            <p style="color:gray; font-size:0.8em;">{_("dashboard.refreshing", lang)}</p>
        </body>
    </html>
    """


async def sse_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events from the queue."""
    # Send initial state immediately
    initial_event = {"event": "connected", "data": dict(state)}
    yield f"data: {json.dumps(initial_event)}\n\n"

    while True:
        try:
            event = await asyncio.wait_for(sse_queue.get(), timeout=30.0)
            yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            # Send keepalive comment every 30s to keep connection alive
            yield ":keepalive\n\n"


@app.get("/api/events")
async def events_endpoint() -> StreamingResponse:
    """SSE endpoint for real-time state updates."""
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
