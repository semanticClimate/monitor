# semanticClimate Monitor

Live uptime monitoring and status page for semanticClimate services, powered by [Upptime](https://upptime.js.org).

## Monitored sites

| Site | URL |
|------|-----|
| ClimateKG Dev | https://dev-climatekg.semanticclimate.org/ |

## How it works

- **Uptime checks** run every 5 minutes via GitHub Actions.
- When a site goes down, a GitHub Issue is opened automatically and an **email notification** is sent to the configured recipient.
- Response-time graphs and the status page are regenerated daily.
- The status page is published to GitHub Pages.

## Setup (one-time, for repository admins)

1. **`GH_PAT` secret** – Create a [Personal Access Token](https://github.com/settings/tokens) with `repo` and `workflow` scopes, then add it as a repository secret named `GH_PAT` in *Settings → Secrets and variables → Actions*.

2. **Email notification secrets** – Upptime uses SMTP to send email alerts. Add the following repository secrets:
   - `NOTIFICATION_EMAIL` – recipient address (already set to `simon.worthington@tib.eu` in `.upptimerc.yml`)
   - `SMTP_HOST` – your SMTP server hostname
   - `SMTP_PORT` – SMTP port (e.g. `587`)
   - `SMTP_USERNAME` – SMTP login username
   - `SMTP_PASSWORD` – SMTP login password

3. **GitHub Pages** – In *Settings → Pages*, set the source to the `gh-pages` branch, root directory. The status page will be published at `https://semanticclimate.github.io/monitor/`.

4. **GitHub Actions permissions** – In *Settings → Actions → General*, ensure *Workflow permissions* is set to **Read and write permissions** and allow workflows to create and approve pull requests.

## Configuration

All monitoring configuration lives in [`.upptimerc.yml`](.upptimerc.yml). Edit that file to add or remove monitored sites, change notification recipients, or customise the status page.

> ⚠️ Do **not** edit the workflow files in `.github/workflows/` directly — they are regenerated automatically from `.upptimerc.yml` by the Updates CI workflow.
