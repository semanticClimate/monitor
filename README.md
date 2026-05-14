# semanticClimate Monitor

Live uptime monitoring and status page for semanticClimate services, powered by [Upptime](https://upptime.js.org) with Python-based diagnostic log collection.

## Monitored sites

| Site          | URL                                        |
| ------------- | ------------------------------------------ |
| ClimateKG Dev | https://dev-climatekg.semanticclimate.org/ |

## How it works

- **Uptime checks** run every 5 minutes via GitHub Actions (Upptime).
- When a site goes down, a GitHub Issue is opened automatically and an **email notification** is sent to the configured recipient.
- **Diagnostic logs** are collected automatically when an outage issue is opened: DNS resolution, SSL certificate validity/expiry, HTTP status code, response time, and response headers are captured and uploaded as a workflow artifact. A summary table is also posted as a comment on the outage issue.
- Response-time graphs and the status page are regenerated daily.
- The status page is published to GitHub Pages.

## Diagnostic log collection (Python)

### Automatic (on outage)

Whenever Upptime opens an issue titled `… is down`, the **Collect Diagnostic Logs** workflow triggers automatically. It runs `collect_logs.py` against all monitored sites, uploads a timestamped JSON report as a workflow artifact (kept for 30 days), and posts a summary table to the issue.

### Manual (on demand)

1. Go to **Actions → Collect Diagnostic Logs → Run workflow**.
2. Optionally enter a specific URL in the *Specific URL to diagnose* field; leave blank to check all configured sites.
3. Download the `diagnostic-logs-<run-id>` artifact from the completed run for the full JSON report.

### Running locally

```bash
pip install -r requirements.txt
python collect_logs.py                          # all sites in .upptimerc.yml
TARGET_URL=https://example.com python collect_logs.py  # one specific URL
LOG_DIR=/tmp/logs python collect_logs.py        # custom output directory
```

The JSON report is written to `logs/diagnostic-<timestamp>.json` and contains per-site DNS, SSL, and HTTP probe results. The script exits with code `1` if any site is unreachable.

## Setup (one-time, for repository admins)

1. **`GH_PAT` secret** – Create a [Personal Access Token](https://github.com/settings/tokens) with `repo` and `workflow` scopes, then add it as a repository secret named `GH_PAT` in _Settings → Secrets and variables → Actions_.

2. **Email notification secrets** – Upptime uses SMTP to send email alerts. Add the following repository secrets:

   | Secret | Description |
   |---|---|
   | `NOTIFICATION_EMAIL` | Recipient address (set in `.upptimerc.yml`) |
   | `SMTP_HOST` | SMTP server hostname |
   | `SMTP_PORT` | SMTP port (e.g. `587`) |
   | `SMTP_USERNAME` | SMTP login username |
   | `SMTP_PASSWORD` | SMTP login password |

3. **GitHub Pages** – In _Settings → Pages_, set the source to the `gh-pages` branch, root directory. The status page will be published at `https://semanticclimate.github.io/monitor/`.

4. **GitHub Actions permissions** – In _Settings → Actions → General_, ensure _Workflow permissions_ is set to **Read and write permissions** and allow workflows to create and approve pull requests.

## Configuration

All uptime-check configuration lives in [`.upptimerc.yml`](.upptimerc.yml). Edit that file to add or remove monitored sites, change notification recipients, or customise the status page.

> ⚠️ Do **not** edit the Upptime workflow files in `.github/workflows/` directly — they are regenerated automatically from `.upptimerc.yml` by the Updates CI workflow. The `collect-logs.yml` workflow is safe to edit.
