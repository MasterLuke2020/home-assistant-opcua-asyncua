# Release checklist — v1.0.4 published / HACS catalog approved

## Repository and licensing
- [x] Public repository: `MasterLuke2020/home-assistant-opcua-asyncua`
- [x] Owner approved MIT license; license is now `LICENSE`
- [x] Reviewed 19 public text files for private host/node identifiers and credential patterns; no matching sensitive literals found (2026-10-20)
- [x] Repository description, valid GitHub topics, and Issues in place
- [x] Existing integration domain `asyncua` preserved (YAML and Entity-ID compatibility)

## Runtime verification
- [x] Start completely separate HA Docker container with its own writable config and port
- [x] Verify startup, initial real PLC temperature value, and automatic subscription updates
- [x] Verify reconnect after 75-second container-only network interruption: automatic reconnection, subscription re-creation, and live sensor updates resumed with fix `0106815`
- [x] Test switch and button BOOL writes on operator-approved edge-triggered WAGO office-light input (physical output may respond); both controls confirmed working on HA test port 8124
- [ ] Confirm no logger errors or entity registry conflicts
- [x] Verify HACS installation into a separate HA test container with live read-only WAGO temperature and subscription updates

## GitHub verification
- [x] Create separate `develop` branch for further changes
- [x] Push source and documentation
- [x] Offline-regression, HACS action, and Hassfest all pass on `develop`
- [x] Resolve HACS/Hassfest validation errors
- [x] Add local integration icon at `custom_components/asyncua/brand/icon.png`
- [x] Bump manifest to `1.0.4`, update changelog, and pass validation on `develop` and `main` (pre-release commit)
- [x] Published full GitHub Release [v1.0.4](https://github.com/MasterLuke2020/home-assistant-opcua-asyncua/releases/tag/v1.0.4) on 2026-10-20
- [x] Submitted and merged [hacs/default#12310](https://github.com/hacs/default/pull/12310) into the official HACS catalog on 2026-11-04
- [x] Completed production upgrade to 1.0.4 and smoke-tested PLC connectivity and entity operation; kept a 1.0.3 rollback backup

**Status as of 2026-11-05:** v1.0.4 is released, the official HACS catalog PR is merged, and a production upgrade was verified by the operator. The test containers were removed after validation. The outstanding general logger/entity-registry audit item above remains open; it is not a release blocker, and the successful smoke tests are not a guarantee against future faults.
