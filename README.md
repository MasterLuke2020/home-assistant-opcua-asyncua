# AsyncUA OPC-UA for Home Assistant

Custom integration for connecting Home Assistant to OPC UA compatible PLCs, originally developed and tested with a WAGO PLC.

> **Pre-release development build.** The public GitHub repository passes automated validation. Both a manually staged Home Assistant instance and a separate HACS-installed instance successfully read a plausible temperature value from a WAGO PLC and received automatic OPC UA subscription updates. Controlled connection-loss/recovery has also passed after a targeted reconnect fix; live switch/button writes have also been confirmed on an operator-approved edge-triggered WAGO control input. **Do not replace a working production integration with this development build.**

## Existing features (unchanged)

- Local OPC UA communication using the pinned `asyncua` Python library
- OPC UA subscriptions for sensor and binary sensor state updates
- Persistent BOOL switches (TRUE/FALSE)
- Momentary BOOL buttons (TRUE for approximately 500 ms, then FALSE)
- Fallback polling, keepalive, and connection recovery
- YAML-based configuration; no UI config flow

No features have been added in this preparation. The test candidate includes narrowly scoped bug fixes and a targeted reconnect stabilization described in `CHANGELOG.md`.

## Requirements

- Home Assistant with support for custom integrations
- OPC UA server reachable from Home Assistant (for example, a WAGO PLC)
- Valid OPC UA Node IDs and read/write permissions
- Python package `asyncua==1.2b2` (installed by Home Assistant as defined in the manifest)

No specific minimum Home Assistant version is claimed until the HA runtime tests have passed.

## Installation

**Via HACS (custom repository):** Open HACS, add `https://github.com/MasterLuke2020/home-assistant-opcua-asyncua` as a **custom repository** of category **Integration**, install **AsyncUA OPC-UA**, and restart Home Assistant. Inclusion in the default HACS catalog requires a separate submission and approval.

**Manually:** Copy `custom_components/asyncua/` to `<HA_CONFIG>/custom_components/asyncua/` and restart Home Assistant.

**Migration:** Existing installation must be backed up before changing any files. The internal integration domain remains `asyncua` to preserve the existing YAML structure and entity IDs. This is not a guarantee of compatibility with every setup; verify in a test HA instance first.

## YAML configuration

Put the following settings in `configuration.yaml` (or your included YAML files), replacing the example PLC URL and OPC UA Node IDs with your own values.

```yaml
asyncua:
  - name: wago
    url: "opc.tcp://192.0.2.10:4840"
    scan_interval: 30

sensor:
  - platform: asyncua
    nodes:
      - name: "PLC temperature"
        unique_id: wago_temperature
        hub: wago
        nodeid: "ns=4;s=|var|Example.Temperature"
        unit: "°C"
        device_class: temperature
        state_class: measurement

binary_sensor:
  - platform: asyncua
    nodes:
      - name: "PLC input"
        unique_id: wago_input
        hub: wago
        nodeid: "ns=4;s=|var|Example.DigitalInput"

switch:
  - platform: asyncua
    nodes:
      - name: "PLC switch"
        unique_id: wago_switch
        hub: wago
        nodeid: "ns=4;s=|var|Example.Switch"

button:
  - platform: asyncua
    nodes:
      - name: "PLC pulse"
        unique_id: wago_pulse
        hub: wago
        nodeid: "ns=4;s=|var|Example.Trigger"
```

**Important:** The PLC URL and Node IDs above are illustrative and are not intended to match a real installation. Buttons and switches **write to the PLC**: do not test those entities against any live or safety-relevant actuator without appropriate safeguards.

### Current configuration details

- The `hub` string must match the corresponding `asyncua[].name`.
- `sensor`/`binary_sensor`: `unique_id` is optional; keys are based on `name` in the existing implementation. Keep names unique **per PLC across data entities** to avoid collisions.
- `button`/`switch`: `unique_id` is required.
- Current fallback polling uses a minimum interval of 30 seconds, even if `scan_interval` is shorter.
- The existing button pulse duration is fixed at 0.5 seconds.
- This integration currently does not provide a UI-based setup (config flow).

## Testing and development

Regression tests require only Python and pytest:

```bash
python -m pip install pytest
python -m pytest tests -q
```

These tests use mock classes to exercise actual coordinator and button code. Read-only WAGO communication and automatic subscription updates passed in two separate Home Assistant containers, including one installation through HACS as a custom repository. A controlled 75-second loss-of-network test, automatic reconnection, and resumed subscription updates passed with the targeted fix. Both switch and momentary-button write functions were confirmed working in the isolated HA test instance using an operator-approved WAGO BOOL input. This test input controls an office light on rising edges and is not an inert test node. See `docs/TESTPLAN.md`.

## Problems and contributing

Use [GitHub Issues](https://github.com/MasterLuke2020/home-assistant-opcua-asyncua/issues) to report problems. Please do not include passwords, tokens, internal IP addresses, or sensitive PLC configuration in public issues.

## License

This project is distributed under the [MIT License](LICENSE).
