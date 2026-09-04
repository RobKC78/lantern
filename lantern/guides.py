"""Human symptom workflows; links are fixed official support destinations."""
from .repairs import platform_key

SOUND_WINDOWS = 'https://support.microsoft.com/en-gb/windows/fix-sound-or-audio-problems-in-windows-73025246-b61c-40fb-671a-2535c7cd56c8'
SOUND_LINUX = 'https://help.ubuntu.com/stable/ubuntu-help/sound-nosound.html.en'
DRIVERS_WINDOWS = 'https://support.microsoft.com/en-us/windows/hardware/drivers/automatically-get-recommended-and-updated-hardware-drivers'
DRIVERS_LINUX = 'https://help.ubuntu.com/stable/ubuntu-help/hardware.html.en'


def guides(platform=None):
    windows = (platform or platform_key()) == 'windows'
    return [
        {'id': 'sound', 'title': 'I can’t hear anything', 'joke': 'Before we fire the sound driver, let’s check whether the speakers are on mute.',
         'steps': ['Turn the volume down first, then check mute, cables and the headset’s own volume.',
                   'Open Settings → System → Sound. Choose the speakers or headphones you actually want.' if windows else
                   'Open your desktop’s Sound settings. Choose the intended output and check its mute switch. Ubuntu/GNOME and KDE label these menus differently.',
                   'Try a familiar recording in another app. Check that app’s volume and selected output too.',
                   'If Lantern found an inactive sound helper, review its Fix this option.' if windows else
                   'Lantern reads PipeWire mute and user-service status when available. If the audio service is unavailable, save work and sign out/in; avoid running desktop audio services as root.',
                   'If sound broke immediately after a driver change, use the Drivers workflow before replacing anything else.'],
         'verify': 'Play the same recording through the intended output. A running service alone does not prove sound works.', 'url': SOUND_WINDOWS if windows else SOUND_LINUX},
        {'id': 'microphone', 'title': 'Nobody can hear me', 'joke': 'Your microphone may not be shy. It may just be the wrong microphone.',
         'steps': ['Check the physical mute switch on your headset.', 'Choose the intended microphone in Sound settings and in the calling app.',
                   'Check the microphone permission for that specific app. Only grant access to apps you trust.',
                   'Use the system’s input-level meter or the app’s microphone test.'],
         'verify': 'Record a short clip or use the app’s microphone test and play it back.', 'url': SOUND_WINDOWS if windows else SOUND_LINUX},
        {'id': 'drivers', 'title': 'A driver is broken—or needs an update', 'joke': 'An old date isn’t a diagnosis. Otherwise every family photo would need a repair ticket.',
         'steps': [
             'Review Lantern’s device findings. A disabled device can be intentional; an error code does not prove a reinstall is the answer.',
             'Open Settings → Windows Update → Advanced options → Optional updates → Driver updates. Check the device and offered driver.' if windows else
             'Open your distribution’s Software Updater. Linux drivers often arrive with kernel and firmware updates. On Ubuntu, check Software & Updates → Additional Drivers for supported proprietary drivers.',
             'If the problem began after an update, check Device Manager → affected device → Properties → Driver → Roll Back Driver, when available.' if windows else
             'If the problem began after an update, use the distribution’s documented recovery or previous-kernel option. Do not remove the only working kernel or use an unrelated driver installer.',
             'Before a reinstall, have the exact manufacturer-provided replacement and a tested recovery/backup plan ready. Network and display driver removal can take away the connection or screen you need to recover.',
             'Use the OS or hardware manufacturer’s supported installation procedure. Lantern does not yet install, delete or reinstall driver packages automatically.'],
         'verify': 'Restart only when requested, repeat the original task, and check the same device again. A successful installer does not prove the symptom is fixed.',
         'url': DRIVERS_WINDOWS if windows else DRIVERS_LINUX},
        {'id': 'bluetooth', 'title': 'My Bluetooth device won’t connect', 'joke': 'Both devices are waiting for the other one to say hello.',
         'steps': ['Charge the device and place it nearby. Check whether it is already connected to another phone or computer.',
                   'Open Bluetooth settings, check the radio and select the intended paired device.',
                   'If Lantern reports an inactive Bluetooth helper, review Fix this.',
                   'If reconnecting fails, follow the device maker’s pairing procedure. Removing a pairing means you will need to pair it again.'],
         'verify': 'Reconnect and try the actual task—play sound, type or move the pointer.',
         'url': 'https://help.ubuntu.com/stable/ubuntu-help/bluetooth-connect-device.html.en' if not windows else DRIVERS_WINDOWS},
        {'id': 'printing', 'title': 'My printer won’t print', 'joke': 'The printer has accepted the assignment. Delivery is apparently a separate department.',
         'steps': ['Check power, paper, displayed printer errors and that the correct printer is selected.',
                   'Open the printer’s queue. Look for paused jobs or an offline status.',
                   'If the print helper is inactive, review Lantern’s Fix this option.',
                   'Cancelling a stuck job discards that queued copy. Keep the original document so you can submit it again. Lantern does not clear queues automatically.'],
         'verify': 'Print one small test page, then the original document.',
         'url': 'https://support.microsoft.com/en-US/Windows/Hardware/Printer/fix-printer-connection-and-printing-problems-in-windows' if windows else 'https://help.ubuntu.com/stable/ubuntu-help/printing.html.en'},
        {'id': 'network', 'title': 'The internet is slow or missing', 'joke': 'The Wi-Fi bars are enthusiastic. They are not a promise.',
         'steps': ['Try another website and another device on the same network. This helps separate an app problem from a network outage.',
                   'Check airplane mode, Wi-Fi selection and cables. Notice whether a VPN is connected.',
                   'Use the system’s network troubleshooter or network settings to inspect the affected connection.',
                   'A network reset can remove saved settings and interrupt remote support. Record Wi-Fi/VPN details before considering it; Lantern does not reset networking automatically.'],
         'verify': 'Repeat the failed task on the same connection, then check a second website.',
         'url': 'https://support.microsoft.com/en-us/windows/fix-wi-fi-connection-issues-in-windows-9424a1f7-6a3b-65a6-4d78-7f07eee84d2c' if windows else 'https://help.ubuntu.com/stable/ubuntu-help/net-wireless-troubleshooting.html.en'},
        {'id': 'updates', 'title': 'Updates keep failing', 'joke': '“Almost done” has been doing a lot of overtime.',
         'steps': ['Save work and check whether Lantern reports a pending restart.', 'Check free storage and whether the connection works.',
                   'Open the operating system’s updater and note the exact failed update and error message.',
                   'Use its supported troubleshooter/recovery guidance. Lantern does not delete update caches or force package repairs automatically.'],
         'verify': 'The updater should confirm the specific update installed after any required restart.', 'url': DRIVERS_WINDOWS if windows else DRIVERS_LINUX},
        {'id': 'slow', 'title': 'Everything feels slow', 'joke': 'Let’s find who is eating the snacks before we replace the whole kitchen.',
         'steps': ['Check Lantern’s memory, free-storage and process details while the slowdown is happening.',
                   'Save work, then close an app you recognize that is using unusually high resources.',
                   'Review startup apps using system settings. Keep security, accessibility and hardware-control tools unless you understand their purpose.',
                   'Avoid one-click “registry cleaners” or mass service disabling. These do not establish the cause.'],
         'verify': 'Repeat the same task and compare responsiveness and resource usage.', 'url': None},
        {'id': 'storage', 'title': 'I’m running out of space', 'joke': 'The drive has been treating “keep everything” as a long-term strategy.',
         'steps': ['Use system Storage settings to see which categories take space.', 'Back up important files to another destination and verify they open there.',
                   'Review downloads and trash before deleting anything. Keep application files in locations supported by that application.',
                   'Lantern does not automatically delete personal files, print jobs or caches.'],
         'verify': 'Check free space on the same volume and retry the failed operation.', 'url': None},
        {'id': 'crash', 'title': 'An app crashes or the screen glitches', 'joke': 'One app leaving the party is different from the whole house losing power.',
         'steps': ['Record which app and what you were doing. Check whether other apps have the same problem.',
                   'Save work, restart the app and check its supported update/repair option.',
                   'If this began after a graphics-driver update, use the Drivers workflow and consider the supported rollback path.',
                   'Repeated hardware errors, unexplained shutdowns or storage errors need investigation beyond an app reinstall.'],
         'verify': 'Repeat the same task and check for new—not just historical—errors.', 'url': DRIVERS_WINDOWS if windows else DRIVERS_LINUX},
    ]
