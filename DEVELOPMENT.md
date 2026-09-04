In-app AI research is now implemented; see [AI-SERVICE.md](AI-SERVICE.md) for operator setup and deployment limits. The service is not yet hosted or activated.

# Lantern Diagnostics — initial MVP

Recent additions: working baselines, scan comparisons, repeated-log grouping, session repair outcomes, in-app AI research and support summaries, guided checks and consented nearby-media discovery. See [INSIGHTS-AND-RESEARCH.md](INSIGHTS-AND-RESEARCH.md) for implemented capabilities and limits. Casting itself is not implemented. AI research sends only after the user reviews and approves the summary.

## Shared Windows/Linux repair experience

The common-problem expansion adds sound, Bluetooth and driver evidence plus ten symptom-based help workflows. See [COMMON-PROBLEMS.md](COMMON-PROBLEMS.md) for what is automatic, what is guided, sources and the next repair adapters.

The app now includes plain-English explanations with optional light humor, **Fix this**, **Fix selected**, **Fix all my stuff**, a concrete approval screen, native administrator permission, verified service-state backups and per-item results. Read [REPAIRS.md](REPAIRS.md) for the supported repair catalog, Linux setup and backup limits. The catalog starts inactive supported printing, time-sync, Bluetooth and Windows audio services; unsupported findings provide guidance. No full-system backup or automatic rollback is claimed. Linux live repair and installer validation remain outstanding.

Local Windows/Linux diagnostics agent with a bundled browser dashboard. Python 3.12+, psutil, standard-library HTTP server and plain JavaScript. Diagnostics remain local. Optional user-approved research uses a separately configured hosted service and the OpenAI API; no account enrollment or automatic telemetry is implemented. This is an initial scaffold/MVP, not a production-certified diagnostic or a replacement for vendor hardware tests.

## Run from source

```text
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Your default browser opens the dashboard. Keep the agent terminal open. Stop with the dashboard button or Ctrl+C; merely closing the browser does not stop the agent. `--no-browser` prints a private local session URL. Do not share this URL. An already elevated session requires an explicit `--consent-elevated` argument; the app does not elevate itself.

## Implemented

- Startup OS, architecture, processor, CPU load, memory, disk capacity, interface and socket collection.
- Top memory processes and service inventory.
- Passive private-LAN neighbor discovery and an observed-membership map.
- Explicitly authorized active TCP discovery: directly connected RFC1918 IPv4 only, maximum /24, 16 workers, five fixed ports. Service names are port-based guesses, not verified identities. IPv6 and routed networks are not probed.
- Bounded accessible Windows System/Application events (24h, 150 per source), Linux journal (24h, 300 events) and selected readable Linux log tails.
- Evidence-linked suggestions for storage pressure, selected log patterns, WHEA, shutdowns, crashes, storage events and broad listener bindings. Supported service-start repairs are available after review; see REPAIRS.md.
- Collector coverage/error reporting, searchable log view, JSON export on explicit click.

The separate `Rob-Linux-Health-Check.sh` deliverable is the closer command-line counterpart to your original PowerShell health check; it includes additional Linux hardware and historical checks not yet integrated here.

## Build packages

Build on each target OS/architecture; PyInstaller is not a cross compiler. Dependencies are downloaded at build time; bundled applications run offline.

Windows: install Python and Inno Setup 6, with `ISCC.exe` on PATH:

```powershell
powershell -File scripts\build-windows.ps1
```

Produces `dist/Lantern-Setup-0.1.0.exe`: per-user installer and shortcuts, no admin required. For just the portable folder use `-PortableOnly`. The installer supports `/VERYSILENT` for an unattended per-user install. Uninstall through Windows Apps. No login-start task/service is created.

Linux:

```bash
bash scripts/build-linux.sh
```

Produces a tar.gz with a per-user `Install-Lantern.sh` and, when `dpkg-deb` is available, a `.deb` for installation using the distribution's package UI. The tar installer copies to the user's local data directory and adds an application-menu entry. Shell double-click behavior varies by desktop; `bash Install-Lantern.sh` is the dependable entry point. A universally one-click Linux installer is not implemented. Build on the oldest supported glibc distribution for compatibility and test each release on clean machines.

## Architecture and data model

`run.py → server.py → collector registry → normalized report → analysis.py → dashboard`

The agent binds only to 127.0.0.1 on an ephemeral port. A random session token is transferred in the browser fragment, removed from the address bar, and required on all API requests. Exact Host/Origin checks and a restrictive content policy limit cross-origin access. State stays in memory; there is no database or automatic report upload. OS/browser swap and caches are outside this application's control.

Report schema version 1 (findings also include `id`, `plain_explanation`, `humor`, `importance`, and optional `repair`; the state envelope includes repair progress):

```json
{"schema_version":1,"collected_at":"UTC ISO-8601","collectors":{"name":{"status":"ok | unavailable","data":{},"error":"optional"}},"findings":[{"severity":"warning | info","title":"...","evidence":{},"likely_cause":"...","suggestion":"...","confidence":"heuristic"}],"networks":["192.168.1.0/24"],"privilege":"standard user"}
```

The API state envelope adds `status`, `report`, `discovery`, and `error`. Device records have IP, optional MAC, observation evidence and inferred services. The map is observed network membership, not switch-port or physical topology. Connection endpoints contain IP/port; process identity is PID only.

Collector plugins are trusted Python functions registered with `@collector('name')` in `collectors.py`. Each returns JSON-serializable data; errors become unavailable results without aborting the whole report. Add fixed command arguments, bounded collection and coverage notes for each new collector. Plugins run with agent privileges and are **not sandboxed**. No third-party plugin installation/loading is exposed.

## Safety and limitations

No credentials, process arguments, browser data, arbitrary file trees or Security audit logs are deliberately collected. Event text can still contain sensitive data; redaction is best effort. Review exports before sharing. No startup persistence, unattended elevation, firewall changes, remote diagnostic listeners or remote-device login exists. Optional AI research sends the user-approved summary to the configured hosted service. Explicitly approved service repairs use a separate elevated helper and save local backup/audit records; see REPAIRS.md.

Network interfaces can change during a scan. Scope is validated at scan start, not bound to a physical interface; VPN/route changes during discovery are a known limitation. Discovery is manual and should be run only on a network you administer. Closed-port/firewalled devices can be missed. Large local networks require selecting a contained /24 or smaller subnet.

Log queries and rules are deliberately bounded. Missing logs or an empty finding list must not be interpreted as healthy. Per-process socket visibility can be incomplete without privilege, including silent omissions on Linux. Rule matches are hypotheses, not proven causes. Some native commands can be unavailable on minimal distributions. CPU temperatures, GPU telemetry, SMART, DNS settings, and custom application-log selection are not integrated. Automatic repairs are limited to the documented service-start catalog.

## Tests

```text
python -m unittest discover -s tests -v
```

Safety tests check off-network discovery rejection before sockets open, redaction, evidence rules, API authentication, origin rejection and missing discovery consent. These do not establish cross-platform hardware support or installer correctness.

## Roadmap

1. **Current:** runnable local collector/dashboard scaffold, private-LAN discovery, evidence rules, build recipes, standalone Linux health script.
2. **Platform validation:** clean Windows and Ubuntu/Fedora testing, signed Windows installer, Debian/RPM/AppImage packages, uninstall/upgrade checks, release checksums, locked transitive dependencies.
3. **Richer diagnostics:** integrate the original health-check categories: SMART/NVMe, GPU/driver state, targeted historical WHEA/crash queries, reboot state, sampled per-process CPU, user-selected application logs and evidence-based noise classification.
4. **Discovery and reporting:** interface-bound probes, IPv6/mDNS with clear consent, device merging, subnet graph visualization, report diff/history with retention controls.
5. **Privilege separation:** narrow elevated helper with per-operation consent, structured capability manifests and isolated collector processes. Keep the dashboard unprivileged.
6. **Guided remediation:** service-start previews, consent, backup records and verification are implemented. Expand the reviewed action catalog and add operation-specific rollback before supporting file/configuration changes. Do not reuse old repair scripts as automatic actions.

