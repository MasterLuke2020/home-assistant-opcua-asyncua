# Changelog

## 1.0.4 — release candidate (2026-10-20)

- Repackaged the existing integration into a HACS-compatible repository layout; no functionality added.
- Serialized simultaneous momentary button writes targeting the same OPC UA Node ID.
- Preserved subscription callbacks received while initial node values are loaded.
- Restarted subscriptions after a successful read-triggered reconnect.
- Preserved domain `asyncua`, YAML configuration, and established entity IDs; raised the manifest version from 1.0.3 to 1.0.4 for release.
- Added offline regression tests and prepared GitHub validation workflows.

### Verification (2026-10-20)

- Offline regression suite: 9/9 passed after the reconnect fix.
- Isolated Home Assistant container: started successfully with the custom integration.
- Real WAGO PLC: OPC UA connection, plausible temperature readout, and automatic subscription updates verified.
- GitHub Actions: regression tests, Hassfest, and HACS validation passed on `develop`.
- Installation via a HACS custom repository in a separate Home Assistant container: PASS (download, integration load, live WAGO read and subscription updates).
- HACS logged an initial zipball download failure but successfully downloaded the individual integration files and completed installation.
- Controlled 75-second network isolation on the HACS test container exposed overlapping reconnect attempts, an unhandled background task exception, and a subscription error ("Connection is not open"). Recovery of automatic sensor updates was not yet confirmed.
- Implemented a targeted reconnect fix on `develop`: background errors are handled, duplicate status-triggered reconnect tasks are coalesced, stale pending reconnects no longer tear down a fresh connection, and reconnect teardown waits for ongoing subscription setup.
- Expanded offline regression checks to 9 tests; all pass locally.
- Corrected-version field retest on isolated HA instance (2026-10-20): 75-second Docker network isolation, automatically handled temporary network errors, self-reconnection, subscription re-creation, and resumed live WAGO temperature updates all PASS without restarting the container. The prior unhandled background-task exception and post-reconnect subscribe race were not observed in the retest.
- Live write verification (2026-10-20): operator confirmed both switch TRUE/FALSE and 500-ms button behavior worked against explicitly approved edge-triggered WAGO office-light input using isolated HA test port 8124. This was a real control input, not an inert test variable. The private PLC node identifier is intentionally omitted from public documentation.
- Still pending before first release: final review of repository contents, release version and metadata, and approval.

**Release status:** The 1.0.4 manifest is prepared on `develop`. No GitHub Release or production deployment has been performed yet. Final GitHub Actions, branch promotion, and release publication are still required.
