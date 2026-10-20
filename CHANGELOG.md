# Changelog

## Unreleased — HACS release preparation

- Repackaged the existing integration into a HACS-compatible repository layout; no functionality added.
- Serialized simultaneous momentary button writes targeting the same OPC UA Node ID.
- Preserved subscription callbacks received while initial node values are loaded.
- Restarted subscriptions after a successful read-triggered reconnect.
- Preserved domain `asyncua`, YAML configuration, established entity IDs, and existing version label 1.0.3 during testing.
- Added offline regression tests and prepared GitHub validation workflows.

### Verification (2026-10-20)

- Offline regression suite: 6/6 passed.
- Isolated Home Assistant container: started successfully with the custom integration.
- Real WAGO PLC: OPC UA connection, plausible temperature readout, and automatic subscription updates verified.
- GitHub Actions: regression tests, Hassfest, and HACS validation passed on `develop`.
- Still pending before first release: safe write tests, connection-loss/recovery test, and actual HACS installation verification.

**Note:** No release or version bump has been published. Keep manifest version `1.0.3` until the remaining release checks are completed; a patch version can then be assigned.
