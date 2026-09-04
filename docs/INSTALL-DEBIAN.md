# Install Lantern on Linux

`Lantern-0.2.0_all.deb` is an initial Debian-format installer for compatible Ubuntu, Linux Mint and Debian desktop systems. It installs the app and an applications-menu entry. It uses your distribution's Python and psutil packages, so a separate Python setup or source build is not required. The package manager may need internet access to install missing dependencies.

1. Download the `.deb` onto the Linux computer.
2. Open it with your software installer and choose Install. Enter your password when the operating system asks.
3. Open **Lantern Diagnostics** from your applications menu. Its dashboard opens in your browser. Keep the accompanying terminal open until you choose Stop in the dashboard.

If your desktop does not have an installer for `.deb` files, open a terminal in the folder containing the download and run:

```bash
sudo apt install ./Lantern-0.2.0_all.deb
```

Then launch Lantern from the applications menu, or run `lantern` as your normal user. Do not launch the diagnostic app with sudo. Supported repairs request separate administrator approval after the repair plan is reviewed.

Remove it through your package manager or with `sudo apt remove lantern-diagnostics`. User-saved baselines and repair backups are retained.

## Build status and limits

The package archive, control fields, launcher permissions and bundled dashboard files were checked on Windows. Installation and app behavior have **not yet been tested on Linux**. This is a test build, not a verified production release. It requires Python 3.10+ and distribution psutil 5.9+. Fedora and Arch do not use this installer.

Optional in-app AI research is included but remains disconnected until the hosted research service is configured. Not every Windows repair has a Linux equivalent. The source README and repair documentation describe the current supported features.

The reproducible package builder is `scripts/build-linux-deb.py` inside the source archive. It packages Python source and declares distribution dependencies; it does not claim to cross-compile a Linux executable on Windows.
