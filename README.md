# Lantern Diagnostics

A Windows/Linux troubleshooting app with plain-English findings, optional light humor, local network mapping, reviewed service repairs and opt-in AI research.

## Download and install — v0.2.0 test builds

| System | Download | Instructions | Validation |
| --- | --- | --- | --- |
| Windows 64-bit | [Windows Setup.exe](https://github.com/RobKC78/lantern/raw/refs/heads/main/downloads/Lantern-Setup-0.2.0.exe) | [Windows installation](docs/INSTALL-WINDOWS.md) | Packaged app startup and diagnostics tested; installer lifecycle untested |
| Ubuntu / Debian / Linux Mint | [Debian package](https://github.com/RobKC78/lantern/raw/refs/heads/main/downloads/Lantern-0.2.0_all.deb) | [Debian installation](docs/INSTALL-DEBIAN.md) | Package structure checked; Linux installation/runtime untested |
| CachyOS / compatible Arch systems | [CachyOS package](https://github.com/RobKC78/lantern/raw/refs/heads/main/downloads/lantern-diagnostics-0.2.0-1-any.pkg.tar.gz) | [CachyOS installation](docs/INSTALL-CACHYOS.md) | Package structure checked; pacman installation/runtime untested |

[Download checksums](downloads/SHA256SUMS). These are unsigned test packages, not production-validated releases. Choose the package for your operating system; do not extract Linux packages before passing them to the package manager. Linux packages use distribution Python dependencies.

## What it does

- Collects OS, hardware, interfaces, listening ports, connections and accessible logs locally.
- Groups repeated log patterns and explains known findings in plain language.
- Offers symptom guides for audio, drivers, printing, Bluetooth and other common problems.
- Maps observed nearby devices, with explicit consent for active private-network discovery.
- Offers **Fix this**, **Fix selected**, and **Fix all my stuff** for supported service starts and conditional Windows component/GameInput repair workflows. Each batch requires plan approval, elevation, the required verified backup/checkpoint and result checks.
- Provides optional saved working baselines and comparisons between scans.
- Offers **Ask AI for help**: review the summary, approve transmission, and read research and citations inside the app.

## Important limits

AI research is implemented but **not hosted or activated**. It requires an operator-run HTTPS service and OpenAI API billing. Users do not need to manually share files or conversations. [Connect the AI service](AI-SERVICE.md).

New in 0.2.0: named application crashes, correlated shutdown notices, explicit missing-installer explanations, repair coverage counts and conditional Windows repair workflows. These new repair operations have been tested with simulated commands, not executed against a live Windows installation.

Most log errors are not automatically repairable. Driver reinstall/update, full-system backups, automatic rollback, and casting media to discovered TVs are not implemented. Linux and Windows share the interface, but available evidence and repair actions differ. [Supported repairs](REPAIRS.md) and [common-problem coverage](COMMON-PROBLEMS.md).

Diagnostics run as a normal user. Repairs use a separate administrator helper. Nothing starts automatically at login. AI research cannot execute commands or add repairs to the approved catalog. Review summaries because logs may contain sensitive information.

## Documentation and development

- [Architecture, collectors, data model and build commands](DEVELOPMENT.md)
- [Repair workflow and backup limits](REPAIRS.md)
- [Insights and research](INSIGHTS-AND-RESEARCH.md)
- [AI hosting, privacy and operator configuration](AI-SERVICE.md)

Run from source with Python 3.12+: create a virtual environment, install `requirements.txt`, then run `python run.py`. Run tests with `python -m unittest discover -s tests -v`.

Windows packaging: `scripts/build-windows.ps1` (Python, PyInstaller and Inno Setup required). Debian source package: `python scripts/build-linux-deb.py`. CachyOS source package: `python scripts/build-cachyos.py`. Native Linux bundle: `bash scripts/build-linux.sh` on Linux.

## Roadmap

1. Test clean installs, upgrades, removal and live repairs on Windows and Linux.
2. Deploy and test the AI service; add simple activation, durable quotas and usage controls.
3. Expand evidence-based diagnostics and independently reviewed repairs with rollback where feasible.
4. Add signed releases and broader Linux packaging after platform validation.

## License

[GNU GPL v3](LICENSE), preserving this repository's existing license. Bundled third-party components retain their respective licenses.
