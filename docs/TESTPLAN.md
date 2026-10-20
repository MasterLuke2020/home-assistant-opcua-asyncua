# Test plan — isolated Home Assistant and WAGO PLC

## Safety

Do not copy files into the production Home Assistant container and do not restart that container. Create a separate HA instance with its own writable configuration directory and a different exposed HTTP port. Do not copy production `secrets.yaml`, `.storage`, database, tokens, or users into the test instance. Start with read-only sensors. Test buttons/switches only on a dedicated, safe PLC test variable—not a physical actuator.

## Required acceptance checks

| Test | Method | Pass condition |
|---|---|---|
| Basic setup | Start isolated HA with YAML `asyncua` and one read-only OPC UA Node ID | Integration loads without import or config errors |
| Initial values | Compare sensor value to known PLC status | Correct value appears |
| Subscription updates | Change a safe read-only test variable on the PLC | HA state updates without manual refresh |
| Connection loss | Temporarily disable OPC-UA test endpoint / connection *without affecting production controls* | Logs show recovery after the link returns |
| Recovery after connection restored | Restore test endpoint | Subscriptions resume and values are current |
| Multiple entities | Configure more than one Node ID | Values map to the correct entities |
| Optional write smoke test | Use dedicated non-actuating BOOL test node | Button writes TRUE/FALSE and switch persists TRUE/FALSE |
| Shutdown | Stop test HA instance | No dangling writes; no production impact |
| HACS install | After repo exists, add as custom repository to test HA HACS | Files installed under `custom_components/asyncua` |

## Validation status as of 2026-10-20

- Offline pytest regression suite: PASS (9 tests, including targeted reconnect regressions, on the 1.0.4 candidate through GitHub Actions)
- Manifest JSON and Python syntax: PASS
- Separate Home Assistant Docker instance with YAML configuration: PASS
- Read-only WAGO PLC temperature: PASS (plausible value)
- Automatic subscription updates from WAGO: PASS (observed without manual refresh)
- GitHub Actions: regression tests, Hassfest, and HACS validation: PASS on `develop`
- Controlled connection interruption/reconnection: PASS after targeted fix `0106815` in the first isolated HA test container (port 8124). Docker network disconnected for 75 seconds, restored without a container restart. Temporary network-unreachable errors were handled; the OPC UA subscription was re-created and the temperature resumed updating automatically. No unhandled background-task exception or post-recovery subscribe failure was observed in this retest. The original HACS-installed test container (port 8125) was not modified.
- PLC write smoke test: PASS per operator's confirmation in isolated HA on port 8124, using an explicitly approved, existing WAGO BOOL input. Both a persistent switch (TRUE/FALSE) and a momentary button worked. This input triggers office-light actions on rising edges; it was **not** a non-actuating variable. No concurrent operation was needed and no general safety guarantee is implied.
- Installation through HACS custom repository: PASS (isolated HA instance on port 8125; manifest version 1.0.3; live WAGO temperature and subscription updates)
- Observation: HACS initially failed to fetch a zipball, fell back to individual files, then completed the installation

## Isolated Docker instance (example; manual configuration required)

On the server, create a separate folder (for example `/srv/containers/ha-opcua-test`) with `config/custom_components/asyncua` and a minimal `config/configuration.yaml`. Add a safe PLC Node ID and URL manually. Do not reuse your production HA config directory.

```bash
cd /srv/containers/ha-opcua-test
docker compose -f compose.yaml up -d
docker compose -f compose.yaml logs --tail 100
```

Open `http://SERVER-IP:8124` for the test instance. Port 8124 is only an example and must be free on the host. To stop and remove the test container without deleting the test configuration:

```bash
cd /srv/containers/ha-opcua-test
docker compose -f compose.yaml down
```

For a suggested Compose file see `docs/compose.test.example.yaml`. Never mount the production config path into the test container.

### Faster preparation

After copying the staging ZIP to the server and extracting it into a new directory, run from the extracted root:

```bash
bash scripts/prepare_ha_test.sh
```

The script refuses to overwrite an existing test directory. It copies only the seven integration source files into the **separate** test tree; it deliberately **does not start** Home Assistant. Edit the test `configuration.yaml` with safe read-only node data before running Compose.
