# Common-problem expansion

## Implemented in this iteration

- Ten symptom workflows: sound, microphone, drivers, Bluetooth, printing, network, updates, slow performance, full storage and app/display crashes. Each includes plain-English checks, optional light humor and a way to verify the result.
- Additional reviewed Windows repairs: start inactive Windows Audio, Audio Endpoint Builder and Bluetooth Support services. Linux adds start of an inactive enabled Bluetooth service. Existing printing/time service repairs remain.
- Read-only Windows problem-device codes, installed audio/display/network/Bluetooth/USB driver information, cached Windows Update driver candidates and pending-restart markers.
- Read-only Linux PCI drivers, PipeWire mute/volume, current-user audio-service states, optional DKMS status and the Debian/Ubuntu reboot marker.
- Device errors, muted output, saved update candidates and pending restarts become plain-English findings. Disabled hardware is not automatically treated as broken.

Automatic service repairs use the existing reviewed plan, native permission prompt, verified service-state/settings snapshot, fixed allowlist, audit record and post-check. Disabled/masked services remain excluded. Starting Windows audio can restore sound only when the stopped service was the cause; it does not repair every sound failure.

## Deliberately visible capability boundaries

The ten symptom workflows are guided troubleshooting, not ten automatic repair routines. Linux user-session audio repair is guided, not run through the root service helper. Running a root PipeWire instance is not a substitute for repairing the logged-in user's audio session.

Driver dates are not compared with arbitrary age thresholds. A driver from an older date is not necessarily outdated. Windows Update information is read from its local cache (`Online=false`), can be absent or stale, and is labeled accordingly. No automatic online update scan occurs. Linux driver freshness is unknown until checked against the appropriate distribution/vendor sources. No universal “all drivers up to date” badge is produced.

Driver installs/reinstalls/rollbacks, print-queue deletion, update-cache deletion, network resets, package repair and personal-file cleanup are not automated in this build. Their guided routes are included. Before automating them, implement device/package-specific backup, a verified replacement, compatibility checks, recovery steps and post-reboot verification. A service snapshot cannot substitute for a driver-package backup or machine image.

## Repair-library priorities

1. **User-session sound adapter:** selected output, mute/volume snapshot, bounded-volume unmute and PipeWire/WirePlumber recovery under the original desktop user; test Windows endpoint controls separately. Verify with user confirmation of audible playback, not only service state.
2. **Printing:** targeted queue diagnosis, explicit job-loss warning, queue-file recovery strategy and a test page chosen by the user.
3. **Networking:** distinguish DNS, local link and upstream outage; offer targeted changes with saved settings. Keep VPN/static-IP changes out of broad resets.
4. **Driver packages:** identify exact device and current package; use Windows Update/OEM or distribution metadata; obtain and verify compatible replacements before removal; preserve existing package and document recovery if network/display disappears. Never use generic driver-updater download sites.
5. **OS updates and application repair:** detect exact package failure, establish free-space/reboot prerequisites, preserve recovery state, then apply the relevant OS/vendor-supported procedure.

## Research basis

Official troubleshooting documentation was used for repair guidance rather than copying commands from forum complaints. These sources establish recognizable problems and supported troubleshooting order; they are not evidence that the app fixes a measured majority of reported failures.

- [Microsoft: sound and audio troubleshooting](https://support.microsoft.com/en-gb/windows/fix-sound-or-audio-problems-in-windows-73025246-b61c-40fb-671a-2535c7cd56c8)
- [Ubuntu: cannot hear sound](https://help.ubuntu.com/stable/ubuntu-help/sound-nosound.html.en)
- [WirePlumber: current-user sound controls](https://pipewire.pages.freedesktop.org/wireplumber/daemon/getting_started.html)
- [Microsoft: recommended and optional driver updates](https://support.microsoft.com/en-us/windows/hardware/drivers/automatically-get-recommended-and-updated-hardware-drivers)
- [Microsoft: update-search online/offline property](https://learn.microsoft.com/en-us/windows/win32/wua_sdk/iupdatesearcher-properties)
- [Ubuntu: hardware and drivers](https://help.ubuntu.com/stable/ubuntu-help/hardware.html.en)
- [Microsoft: printer troubleshooting](https://support.microsoft.com/en-US/Windows/Hardware/Printer/fix-printer-connection-and-printing-problems-in-windows)
- [Microsoft: Wi-Fi troubleshooting](https://support.microsoft.com/en-us/windows/fix-wi-fi-connection-issues-in-windows-9424a1f7-6a3b-65a6-4d78-7f07eee84d2c)

## Validation

Automated tests cover driver-age non-inference, cached-update labeling, intentional disabled devices, unknown hardware cause, muted audio, pending restart, platform-specific guide steps and new repair descriptions. Real audio repair, Bluetooth reconnects, WMI/WUA data collection and Linux hardware collection still require target-machine validation. No device drivers were removed, installed or updated on the user's machine during development.
