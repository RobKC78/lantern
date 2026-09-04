# New in 0.2.0: conditional Windows repair workflows

**Check and repair Windows components** is offered for logged crashes of executables in Windows System32. It is a repair candidate, not a diagnosis. After a newly created and verified Windows System Restore checkpoint and local preflight record, it scans with DISM and checks protected files with SFC. It repairs only recognized corruption, then verifies again. Healthy checks do not trigger repair. Unrecognized output stops the affected workflow. SFC result interpretation currently supports English output only. No restart is forced. Servicing commands may take an hour or longer; keep the app running. Windows repair may contact Windows Update.

**Repair Microsoft GameInput** is offered for GameInput installer failures 1714/1612 only when exactly one matching Microsoft MSI registration has an accessible, valid Microsoft-signed cached installer. It backs up and verifies that installer and creates the new restore checkpoint, then runs a fixed Windows Installer repair without forced reboot. The source is rechecked before execution. If the source is missing, inaccessible, ambiguous or untrusted, the app explains why repair is unavailable. It does not fetch an arbitrary replacement, delete MSI registry records or promise that a failed upgrade is resolved.

Both use the existing per-item, selected-item and all-supported-items plan/consent flow. Shared workflows run once per batch. All required preflight backups/checkpoints complete before any selected repair starts, including mixed service/Windows batches. System Restore throttling and disabled protection are respected: a failed new checkpoint blocks the batch. A restore point is not a personal-file backup or guaranteed rollback. Existing service-only batches retain the service-state backup described below.

**Validation:** simulated tests cover corruption/no-corruption decisions, missing sources, backup failures, mixed-batch gating, deduplication and post-check wording. No live DISM/SFC/MSI repair or System Restore creation has been run during development. Driver reinstall/update, missing-source recovery and Mozilla installer repair remain unsupported. DCOM permission changes are deliberately not a repair action.

References: [Microsoft system-file repair](https://support.microsoft.com/en-us/windows/experience/backup-recovery/using-system-file-checker-in-windows), [Windows restore checkpoints](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/checkpoint-computer?view=powershell-5.1), [Windows Installer](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec).

---

# The same repair experience on Windows and Linux

The shared dashboard now explains findings in plain English, with optional original light humor. Serious hardware/data warnings and permission prompts stay factual. It does not imitate a real comedian or call an online language model.

Each finding has either a checkbox and **Fix this** or **Show next steps**. **Fix selected** and **Fix all my stuff** prepare the same review screen. “All” means all currently supported repair candidates, not every warning in the logs. An inactive service is explicitly described as a possible normal condition, not proof of a fault.

## What happens after you click

1. The server creates a five-minute plan from the current findings. Arbitrary action names and commands are rejected.
2. Review each change, possible effects, backup scope and undo limits. Check the consent box and click **Back up & fix these items**.
3. Windows requests UAC approval; Linux requests administrator approval through the desktop's polkit agent (`pkexec`). The dashboard remains unprivileged. No password is collected by Lantern.
4. The separate helper rechecks service state. It exclusively creates a private backup directory and writes the states/settings of every selected service. File bytes are read back and verified; all backups must succeed before any service is started.
5. The helper starts each approved service, records the result and checks its new state. Each item shows **Fixed**, **Still needs attention**, or **Couldn’t complete**. “Fixed” means the service reached its running state; the user still needs to try printing or check time synchronization.
6. The dashboard displays the backup path and a **Check my device again** button. Backup records remain on disk. They are not uploaded or deleted automatically.

## Current automatic repair catalog

| Purpose | Windows | Linux |
|---|---|---|
| Start printing helper | Spooler | cups.service |
| Start clock syncing | W32Time | systemd-timesyncd.service |
| Start sound helper | Audiosrv | Guided user-session checks |
| Start sound-device helper | AudioEndpointBuilder | Guided user-session checks |
| Start Bluetooth helper | bthserv | bluetooth.service |

Only installed, inactive services with permitted startup states qualify. Disabled/masked services are excluded. Linux time repair is withheld if known alternative time services are active. Some distributions use chrony rather than systemd-timesyncd; those installations receive no time-start repair from this initial catalog. Non-systemd Linux installations retain diagnostics where supported but have no automatic service repair adapter yet.

These are service starts, not changes to startup configuration. Printing may process existing queued jobs and open configured listeners; clock syncing may contact its configured server and adjust the clock. The review screen explains these effects.

## Backup and rollback limits

This version makes a **service-state/settings snapshot**, not a personal-file backup, disk image, system restore point or complete Linux snapshot. These operations do not edit personal files or service configuration. Starting services can still have effects such as printing, clock changes or dependency activation. Saving their prior states does not reverse those effects.

Backups contain `before.json`, a SHA-256 manifest, and per-action intent/result files. Linux backups are root-only directories under `/var/lib/lantern-backup-*`. Windows backups are administrator/SYSTEM-only directories under the system drive's `ProgramData/Lantern-backup-*`. Administrative permission is required to inspect them. Backup creation, write, permission or verification failure stops the batch before repair. Results also remain in the current dashboard session.

No automatic rollback is offered yet. A technician can review the saved prior service state and decide whether stopping the service is appropriate. Never claim that a full machine backup has occurred. File edits, cleanup, package changes and driver repairs require their own verified backup and rollback adapters before inclusion in this catalog.

## Launch on Linux

From the extracted application folder:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
bash Start-Lantern.sh
```

Use a normal desktop user. Linux repair requires systemd, polkit's `pkexec`, and an active desktop authentication agent. If permission is declined or the agent/tool is missing, the dashboard reports the failure. It does not fall back to password collection or weaken permissions. Headless systems can still use the separate read-only health-check script.

The application source and installed bundle must be trusted because the helper runs that code with administrator rights after explicit approval. Do not elevate a modified/untrusted copy. The release roadmap still includes signed packages and a separately installed, administrator-owned helper.

## Packaging and validation

`bash scripts/build-linux.sh` creates the Linux tar bundle and Debian package on Linux. The included GitHub workflow can test/package Windows and Ubuntu when run in a repository; it has not been uploaded or executed here. No Linux binary was built on this Windows machine.

Tests use mocked services and temporary backups. They verify platform-parity finding metadata, unsupported/disabled actions, stale state, backup-before-mutation ordering, failed-backup blocking, result records and competing time-service checks. Existing API authentication and discovery-scope tests remain. Tests never start actual services or request administrator access.

Live Linux desktop, polkit, package installation, physical backup permissions and actual service repairs still require validation on Linux. Windows UAC/service mutation has likewise not been exercised on the user's device.

Native permission references: [polkit pkexec](https://polkit.pages.freedesktop.org/polkit/pkexec.1.html), [Microsoft Start-Process](https://learn.microsoft.com/powershell/module/microsoft.powershell.management/start-process).
