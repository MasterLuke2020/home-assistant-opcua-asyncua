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

- Offline pytest regression suite: PASS (6 tests)
- Manifest JSON and Python syntax: PASS
- Separate Home Assistant Docker instance with YAML configuration: PASS
- Read-only WAGO PLC temperature: PASS (plausible value)
- Automatic subscription updates from WAGO: PASS (observed without manual refresh)
- GitHub Actions: regression tests, Hassfest, and HACS validation: PASS on `develop`
- Controlled connection interruption and reconnection: NOT YET TESTED
- Safe non-actuating PLC write test: NOT YET TESTED
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
