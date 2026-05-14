#!/usr/bin/env python3
"""
Diagnostic log collector for semanticClimate outage monitoring.

When a site outage is detected, this script performs in-depth diagnostics:
  - DNS resolution check
  - SSL/TLS certificate validity and expiry
  - HTTP reachability, status code, response time, and headers

Results are written as a timestamped JSON file in the LOG_DIR directory
(default: ``logs/``).  The script exits with code 1 if any site is unreachable,
so it can act as a gate in CI or be interrogated by downstream workflow steps.

Environment variables
---------------------
UPPTIME_CONFIG : path to .upptimerc.yml (default: ``.upptimerc.yml``)
LOG_DIR        : directory for JSON output (default: ``logs``)
TARGET_URL     : restrict diagnostics to this URL; if it does not appear in
                 the config it is treated as an ad-hoc one-off check.
"""

import json
import os
import socket
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml


# ---------------------------------------------------------------------------
# Site config loader
# ---------------------------------------------------------------------------

def load_sites(config_path: str = ".upptimerc.yml") -> list[dict]:
    """Return the list of ``{name, url}`` dicts from the Upptime config."""
    with open(config_path, encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    return config.get("sites", [])


# ---------------------------------------------------------------------------
# Individual diagnostic probes
# ---------------------------------------------------------------------------

def check_dns(hostname: str) -> dict:
    """Resolve *hostname* and return a result dict."""
    result: dict = {
        "hostname": hostname,
        "resolved": False,
        "addresses": [],
        "error": None,
    }
    try:
        infos = socket.getaddrinfo(hostname, None)
        result["addresses"] = sorted({info[4][0] for info in infos})
        result["resolved"] = True
    except socket.gaierror as exc:
        result["error"] = str(exc)
    return result


def check_ssl(hostname: str, port: int = 443) -> dict:
    """Connect to *hostname*:*port* over TLS and inspect the certificate."""
    result: dict = {
        "hostname": hostname,
        "valid": False,
        "subject": None,
        "issuer": None,
        "expires": None,
        "days_until_expiry": None,
        "error": None,
    }
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(
            socket.create_connection((hostname, port), timeout=10),
            server_hostname=hostname,
        ) as ssock:
            cert = ssock.getpeercert()

        result["valid"] = True
        result["subject"] = dict(x[0] for x in cert.get("subject", []))
        result["issuer"] = dict(x[0] for x in cert.get("issuer", []))

        not_after = cert.get("notAfter")
        if not_after:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=timezone.utc
            )
            result["expires"] = expiry.isoformat()
            result["days_until_expiry"] = (
                expiry - datetime.now(timezone.utc)
            ).days
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def check_http(url: str, timeout: int = 30) -> dict:
    """Perform an HTTP GET and collect reachability/timing/header data."""
    result: dict = {
        "url": url,
        "status_code": None,
        "reachable": False,
        "response_time_ms": None,
        "headers": {},
        "redirect_chain": [],
        "error": None,
    }
    try:
        t0 = time.monotonic()
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed_ms = (time.monotonic() - t0) * 1000

        result["status_code"] = resp.status_code
        result["reachable"] = resp.status_code < 500
        result["response_time_ms"] = round(elapsed_ms, 2)
        result["headers"] = dict(resp.headers)
        result["redirect_chain"] = [r.url for r in resp.history]
    except requests.exceptions.ConnectionError as exc:
        result["error"] = f"ConnectionError: {exc}"
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {timeout}s"
    except requests.exceptions.RequestException as exc:
        result["error"] = str(exc)
    return result


# ---------------------------------------------------------------------------
# Per-site orchestration
# ---------------------------------------------------------------------------

def diagnose_site(site: dict) -> dict:
    """Run all probes for *site* and return a combined result dict."""
    name = site["name"]
    url = site["url"]
    parsed = urlparse(url)
    hostname = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    print(f"  DNS  → {hostname}")
    dns = check_dns(hostname)

    ssl_info = None
    if parsed.scheme == "https":
        print(f"  SSL  → {hostname}:{port}")
        ssl_info = check_ssl(hostname, port)

    print(f"  HTTP → {url}")
    http = check_http(url)

    return {
        "name": name,
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dns": dns,
        "ssl": ssl_info,
        "http": http,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    config_path = os.environ.get("UPPTIME_CONFIG", ".upptimerc.yml")
    output_dir = Path(os.environ.get("LOG_DIR", "logs"))
    target_url = os.environ.get("TARGET_URL", "").strip()

    sites = load_sites(config_path)

    if target_url:
        filtered = [
            s for s in sites
            if s["url"].rstrip("/") == target_url.rstrip("/")
        ]
        # Fall back to an ad-hoc entry if the URL is not in the config.
        sites = filtered or [{"name": target_url, "url": target_url}]

    if not sites:
        print("No sites to check.")
        sys.exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sites": [],
    }

    for site in sites:
        print(f"\nDiagnosing: {site['name']}  ({site['url']})")
        diagnosis = diagnose_site(site)
        report["sites"].append(diagnosis)

        status = "UP" if diagnosis["http"]["reachable"] else "DOWN"
        print(f"  Status: {status}")
        if diagnosis["http"]["error"]:
            print(f"  HTTP error : {diagnosis['http']['error']}")
        if diagnosis["dns"]["error"]:
            print(f"  DNS error  : {diagnosis['dns']['error']}")
        if diagnosis.get("ssl") and diagnosis["ssl"]["error"]:
            print(f"  SSL error  : {diagnosis['ssl']['error']}")
        days = (
            diagnosis.get("ssl") or {}
        ).get("days_until_expiry")
        if days is not None and days < 30:
            print(f"  ⚠️  SSL certificate expires in {days} days")

    log_file = output_dir / f"diagnostic-{timestamp}.json"
    with open(log_file, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"\nDiagnostic report saved to {log_file}")

    any_down = any(not s["http"]["reachable"] for s in report["sites"])
    if any_down:
        sys.exit(1)


if __name__ == "__main__":
    main()
