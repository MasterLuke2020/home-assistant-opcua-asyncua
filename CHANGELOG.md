# Changelog

## Unreleased — HACS preparation / test candidate

- Repackaged the existing integration into a HACS-compatible repository layout; no functionality added.
- Serialized simultaneous momentary button writes targeting the same OPC UA Node ID.
- Preserved subscription callbacks received while initial node values are loaded.
- Restarted subscriptions after a successful read-triggered reconnect.
- Preserved domain `asyncua`, YAML configuration, established entity IDs, and existing version label 1.0.3 during testing.
- Added offline regression tests and prepared GitHub validation workflows.

**Note:** These are not published release notes. Assign a new patch version only after verification on a full Home Assistant installation.
