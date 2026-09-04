# Changes

## 0.2.0 — conditional Windows repairs

- Named application-crash groups instead of one generic crash card.
- Check-and-repair workflow for Windows component crashes, with corruption checks before repair and verification afterward.
- Registered Microsoft GameInput MSI repair when a valid Microsoft-signed installer source is available; clear explanation when unavailable.
- Newly created, verified Windows recovery checkpoints before either advanced workflow; a failed checkpoint blocks all selected repairs.
- Correlate shutdown records within the same boot window; distinguish network/update information from repair candidates.
- Show repair coverage and disable disconnected AI research controls.
- 44 unit tests pass; packaged Windows startup and conditional-plan creation tested. No live repair commands or restore-point creation tested. Linux installation remains untested.

Missing MSI-source recovery, driver reinstall/update and Mozilla installer repair remain future work. These workflows do not promise to resolve every crash or error.
