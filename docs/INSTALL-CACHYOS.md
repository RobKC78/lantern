# Lantern for CachyOS — test package

Use `lantern-diagnostics-0.1.0-1-any.pkg.tar.gz`, not the Debian `.deb` file. Do not extract the package before installation.

Open a terminal in the folder containing your downloaded package and run:

```bash
sudo pacman -U ./lantern-diagnostics-0.1.0-1-any.pkg.tar.gz
```

Review the package manager's proposed installation and approve it. Missing Python/psutil dependencies are handled through the configured distribution repositories. Then open **Lantern Diagnostics** from the applications menu. The dashboard opens in your browser; keep the accompanying terminal open until you choose Stop in the dashboard. Run the app as your normal user, not with sudo.

You can also launch it by typing `lantern`. Remove the application with `sudo pacman -R lantern-diagnostics`; saved baselines and repair backups remain.

This is an unsigned local test package. Do not disable package-signature checks if your configuration rejects it; report the error so packaging can be corrected for your system.

The archive structure, metadata, app files and launcher permissions have been checked on Windows. Installation with pacman and live operation on CachyOS have **not** been tested because a Linux environment is unavailable here. The package contains portable Python source and uses distribution dependencies; no Linux binary was cross-compiled. It does not modify your kernel, graphics drivers or boot configuration.

AI research still needs a configured hosted service. Repairs are limited to the documented, vetted catalog, and request separate permission. Optional `pciutils` improves driver inventory; `polkit` and a desktop authentication agent enable approved service repairs.

Build from source with `python scripts/build-cachyos.py`. Installation command reference: https://pacman.archlinux.page/pacman.8.html (Upgrade operation, `-U`).
