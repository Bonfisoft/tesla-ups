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

### SMTP / Email Notifications

- `SMTP_SERVER` - SMTP host for email notifications (e.g., `smtp.gmail.com`)
- `SMTP_PORT` - SMTP port (default: `587`)
- `EMAIL_USER` - SMTP login user (your email address)
- `EMAIL_PASS` - SMTP password or [App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification on Google account)
- `NOTIFY_TO` - Notification recipient email or phone gateway address

### General Settings

- `DEFAULT_LANGUAGE` - Interface language (`en`, `haw`, `it`, `nv`, default: `en`)
- `POLL_INTERVAL` - Polling interval in seconds (default: `15`)

### Port Configuration

All service ports can be customized via environment variables:

- `PYPOWERWALL_PORT` - PyPowerwall web UI port (default: `8675`)
- `NUT_UPSD_PORT` - NUT UPS daemon port (default: `3493`)
- `BRIDGE_PORT` - Tesla UPS Bridge dashboard port (default: `8000`)

Example using custom ports:
```bash
PYPOWERWALL_PORT=8080
NUT_UPSD_PORT=3494
BRIDGE_PORT=9000
```

Provider-specific settings (such as the Powerwall proxy URL) are configured in `providers.yaml` rather than environment variables.

### Email Authentication

**Gmail requires App Passwords** (Google disabled "Less Secure Apps"):

1. Enable [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification) on your Google account
2. Generate an [App Password](https://myaccount.google.com/apppasswords) (16-character code)
3. Use the App Password in `EMAIL_PASS`:

```bash
EMAIL_USER=your.email@gmail.com
EMAIL_PASS=xxxx xxxx xxxx xxxx  # 16-char app password
```

For other email providers, use your regular SMTP password.

## Internationalization

The dashboard and email alerts support multiple languages:

- **English** (`en`) - Default
- **Hawaiian** (`haw`) - ʻŌlelo Hawaiʻi
- **Italian** (`it`)
- **Navajo** (`nv`) - Diné Bizaad

Access the dashboard in any supported language:

```text
http://bridge-host:8000/?lang=it
http://bridge-host:8000/?lang=haw
http://bridge-host:8000/?lang=nv
```

Or set your browser's preferred language. The bridge also respects the `Accept-Language` HTTP header for automatic language detection.

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

## Docker Deployment

### Option 1: Pre-built Image (Recommended)

Use the pre-built Docker Hub image:

```bash
# 1. Download example files
curl -O https://raw.githubusercontent.com/darthbert/tesla-ups/main/docker-compose.hub.yml
mv docker-compose.hub.yml docker-compose.yml

# 2. Configure
cp .env.example .env
nano .env  # Edit your credentials

# 3. Run
docker compose up -d
```

### Option 2: Build Locally

```bash
git clone https://github.com/darthbert/tesla-ups.git
cd tesla-ups
cp .env.example .env
nano .env
docker compose up -d --build
```

### Publishing to Docker Hub

Set up GitHub Actions secrets (`DOCKER_USERNAME`, `DOCKER_PASSWORD`), then push tags:

```bash
git tag v1.0.0
git push origin v1.0.0
```

**Note for Forks:** GitHub Actions secrets are not inherited in forks. If you fork this repository, you must:
1. Add your own `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets in your fork's settings
2. Update `IMAGE_NAME` in `.github/workflows/docker-publish.yml` to use your Docker Hub username
3. Or build and push manually: `docker build -t yourname/tesla-ups-bridge . && docker push yourname/tesla-ups-bridge`

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

## NUT Integration

The bridge writes UPS status to a NUT-compatible file format that can be consumed by the `dummy-ups` driver.

### NUT Configuration Files

Create these files on your host for the NUT container:

**`nut-config/ups.conf`:**
```ini
[powerwall]
    driver = dummy-ups
    port = /var/lib/nut/ups/powerwall.dev
    mode = dummy-once
    desc = "Tesla Powerwall via Bridge"
```

**`nut-config/upsd.conf`:**
```
LISTEN 0.0.0.0 3493
MAXAGE 30
```

**`nut-config/upsd.users`:**
```
[admin]
    password = admin
    upsmon master
```

### NUT Docker Service

```yaml
nut-upsd:
  image: instantlinux/nut-upsd:latest
  container_name: nut-upsd
  restart: always
  privileged: true
  volumes:
    - ./nut-config:/etc/nut
    - ups_status:/var/lib/nut/ups
  environment:
    - UPS_NAME=powerwall
    - UPS_DRIVER=dummy-ups
  ports:
    - "3493:3493"
  depends_on:
    powerwall-bridge:
      condition: service_healthy
```

**Key points:**
- Use `dummy-ups` driver (reads from status file)
- Set `UPS_DRIVER=dummy-ups` environment variable
- Mount shared volume `ups_status` for the status file
- Use `depends_on` with `condition: service_healthy` to ensure bridge starts first

## Health Checks

The bridge includes a Docker healthcheck:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/status"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

The bridge also creates an initial NUT status file on startup so the `dummy-ups` driver can start immediately.

## Improvements and future additions

- Add NUT event handler support for graceful shutdown commands
- Add more robust retry and backoff for Powerwall API failures
- Integrate with Slack, Telegram, or SMS notification services
- Add CI automation (e.g. GitHub Actions) for tests and Docker image builds
- Add metrics / Prometheus export for outage monitoring
- Add secrets management for SMTP credentials

## License

This project is released under the MIT License.
