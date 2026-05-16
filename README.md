# Tesla Powerwall UPS Bridge

This project monitors a Tesla Powerwall through a local proxy and reports grid outages to a Network UPS Tools (NUT) server. When a Powerwall outage is detected, it writes NUT-compatible UPS status data and can send a notification email.

## Scope

- Poll the Powerwall proxy API for battery and grid state
- Write a NUT UPS status file at `/var/lib/nut/ups/powerwall.dev`
- Detect grid outages and low battery conditions
- Send email notifications when an outage begins
- Provide a small FastAPI dashboard and JSON status endpoint

## Architecture

- `pypowerwall` container: fetches Powerwall data from the home energy system
- `nut-upsd` container: exposes NUT UPS state for the homelab
- `powerwall-bridge` container: polls the Powerwall API, updates NUT state, and sends notifications

```text
Powerwall -> pypowerwall proxy -> powerwall-bridge -> NUT status file
                       \-> dashboard / API
```

## Files

- `bridge.py` - main FastAPI application and NUT bridge logic
- `providers/` - battery provider package (abstract interface + implementations)
- `providers.yaml` - selects the active provider and passes its settings
- `Dockerfile` - container image definition for the bridge service
- `compose.yaml` / `docker-compose.yml` - Docker Compose stack for the full system
- `requirements.txt` - runtime Python dependencies
- `requirements-dev.txt` - developer/test dependencies
- `tests/` - unit and integration tests

## Dependencies

- Docker
- Docker Compose
- Python 3.11 (for local development and tests)

## Environment

The bridge service supports these environment variables:

- `SMTP_SERVER` - SMTP host for email notifications
- `SMTP_PORT` - SMTP port (default: `587`)
- `EMAIL_USER` - SMTP login user
- `EMAIL_PASS` - SMTP login password
- `NOTIFY_TO` - notification recipient email or phone gateway address
- `DEFAULT_LANGUAGE` - Interface language (`en` or `it`, default: `en`)

Provider-specific settings (such as the Powerwall proxy URL) are configured in `providers.yaml` rather than environment variables.

## Internationalization

The dashboard and email alerts support multiple languages:

- **English** (`en`) - Default
- **Italian** (`it`)

Access the dashboard in Italian:
```
http://bridge-host:8000/?lang=it
```

Or set your browser's preferred language to Italian. The bridge also respects the `Accept-Language` HTTP header for automatic language detection.

## Provider Configuration

The active battery provider is selected via `providers.yaml` in the project root:

```yaml
provider: powerwall
config:
  proxy_url: http://pypowerwall:8675/api/status
  timeout: 5
```

- **`provider`** — name of the provider module under `providers/`. Currently only `powerwall` is built in.
- **`config`** — key/value pairs passed as constructor arguments to the provider class.

At startup the bridge loads this file, instantiates the provider, and runs its `health_check()`. A failed health check logs a warning but does not abort startup.

### Writing a custom provider

1. Create `providers/myprovider.py` and implement the `BatteryProvider` ABC:

   ```python
   from providers.base import BatteryProvider, BatteryStatus

   class MyProvider(BatteryProvider):
       def __init__(self, api_url: str) -> None:
           self._api_url = api_url

       @property
       def provider_name(self) -> str:
           return "My Battery System"

       def fetch_status(self) -> BatteryStatus:
           # call your system's API and return a BatteryStatus
           ...
   ```

2. Register it in `providers/__init__.py` by adding an entry to `_PROVIDER_CLASS_MAP`:

   ```python
   _PROVIDER_CLASS_MAP = {
       "powerwall": ("providers.powerwall", "PowerwallProvider"),
       "myprovider": ("providers.myprovider", "MyProvider"),
   }
   ```

3. Update `providers.yaml` to select it:

   ```yaml
   provider: myprovider
   config:
     api_url: http://mybattery:1234/status
   ```

## Usage

Build and start the stack:

```bash
docker compose -f compose.yaml up --build
```

Or use the standard compose file:

```bash
docker compose up --build
```

The bridge dashboard will be available on `http://localhost:8000/` and the status endpoint on `http://localhost:8000/api/status`.

## Testing

### Prerequisites

- Python 3.11 or later
- A virtual environment is recommended to isolate dependencies

### Set up the test environment

Create and activate a virtual environment, then install both runtime and developer dependencies:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run the full test suite

```bash
pytest
```

Pytest is configured via `pytest.ini`. Tests are discovered automatically from the `tests/` directory. The `-v` flag is always on so each test name is printed, and `--tb=short` keeps tracebacks concise.

### Run a specific test file

```bash
pytest tests/test_bridge.py
pytest tests/test_api.py
```

### Run tests by marker

Tests are marked as either `unit` or `integration`:

```bash
pytest -m unit
pytest -m integration
```

### What the tests cover

- **`tests/test_bridge.py`** — unit tests for core bridge logic:
  - `determine_status` — grid-connected, outage, and low-battery UPS status labels
  - `send_alert` — skips sending when SMTP configuration is absent
  - `write_nut_status_file` — verifies NUT-format output written to a temp file
  - `process_powerwall_data` — end-to-end state update, alert dispatch, and file write
- **`tests/test_api.py`** — FastAPI endpoint tests using `TestClient`:
  - `GET /api/status` — returns the current state dict as JSON
  - `GET /` — returns the HTML dashboard with expected status fields

All tests use `monkeypatch` and `tmp_path` pytest fixtures; no live Powerwall or SMTP server is required.

## Building and Deploying

### Build Prerequisites

- Docker Engine 24+ and Docker Compose v2 (`docker compose` subcommand, not the legacy `docker-compose` binary)
- Network access to the Tesla Powerwall gateway on your LAN
- A working SMTP account if you want email notifications (optional)

### 1. Configure the stack

Before the first build, edit `compose.yaml` (recommended) or `docker-compose.yml` to set real values for every environment variable. At minimum you must set the `pypowerwall` credentials and your Powerwall's LAN IP:

```yaml
services:
  pypowerwall:
    environment:
      - PW_HOST=<powerwall-lan-ip>       # e.g. 192.168.1.100
      - PW_PASSWORD=<gateway-password>
      - PW_EMAIL=<tesla-account-email>
      - PW_TIMEZONE=<your-timezone>       # e.g. Australia/Brisbane
```

And in the `powerwall-bridge` service, set your SMTP credentials:

```yaml
  powerwall-bridge:
    environment:
      - SMTP_SERVER=smtp.gmail.com
      - SMTP_PORT=587
      - EMAIL_USER=you@gmail.com
      - EMAIL_PASS=your_app_password      # use a Gmail App Password, not your login password
      - NOTIFY_TO=recipient@example.com
```

> **Security note:** Do not commit real credentials to version control. Prefer Docker Compose [secrets](https://docs.docker.com/compose/use-secrets/) or a `.env` file (add `.env` to `.gitignore`).

### 2. Build and start the full stack

```bash
docker compose -f compose.yaml up --build
```

This will:

1. Pull the `jasonacox/pypowerwall` and `instantlinux/nut-upsd` images from Docker Hub.
2. Build the `powerwall-bridge` image from `Dockerfile` using Python 3.11-slim.
3. Install Python dependencies (`fastapi`, `uvicorn`, `requests`) inside the image.
4. Start all three containers and create the shared `ups_status` named volume.

To run in the background (detached):

```bash
docker compose -f compose.yaml up --build -d
```

### 3. Verify the stack is running

Check container status:

```bash
docker compose -f compose.yaml ps
```

Inspect live logs from the bridge service:

```bash
docker compose -f compose.yaml logs -f powerwall-bridge
```

Confirm the bridge is polling successfully — you should see lines like:

```text
2025-06-01 10:00:00 INFO Powerwall poll succeeded ...
```

### 4. Access the dashboard and API

| Endpoint | URL |
| --- | --- |
| Browser dashboard | `http://localhost:8000/` |
| JSON status | `http://localhost:8000/api/status` |
| Powerwall proxy | `http://localhost:8675/api/status` |
| NUT daemon | `localhost:3493` (TCP) |

The dashboard auto-refreshes every 15 seconds. The JSON status endpoint returns the current `ups.status`, battery charge (`soe`), grid state, and last notification time.

### 5. Verify NUT is receiving the state file

The bridge writes `/var/lib/nut/ups/powerwall.dev` inside the shared `ups_status` volume every 15 seconds. To confirm it from the host:

```bash
docker exec nut-upsd cat /var/lib/nut/ups/powerwall.dev
```

Expected output when on grid:

```text
ups.status: OL
battery.charge: 95.0
```

To query NUT directly (requires `nut-client` tools on the host or inside the container):

```bash
docker exec nut-upsd upsc powerwall@localhost
```

### 6. Rebuild after code changes

The `bridge.py` file is bind-mounted into the running container (see `compose.yaml`), so small code edits take effect after restarting the service — a full image rebuild is not required:

```bash
docker compose -f compose.yaml restart powerwall-bridge
```

For dependency changes (edits to `requirements.txt` or `Dockerfile`), rebuild the image:

```bash
docker compose -f compose.yaml up --build powerwall-bridge
```

### 7. Stop and clean up

Stop all services (preserves volumes):

```bash
docker compose -f compose.yaml down
```

Stop and remove all volumes (destroys the shared NUT state volume):

```bash
docker compose -f compose.yaml down -v
```

## Improvements and future additions

- Add NUT event handler support for graceful shutdown commands
- Add more robust retry and backoff for Powerwall API failures
- Integrate with Slack, Telegram, or SMS notification services
- Add CI automation (e.g. GitHub Actions) for tests and Docker image builds
- Add metrics / Prometheus export for outage monitoring
- Add secrets management for SMTP credentials

## License

This project is released under the MIT License.
