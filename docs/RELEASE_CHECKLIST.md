# Release checklist — pre-release / approval pending

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
- [x] Bump manifest to `1.0.4` and update changelog on `develop` (release candidate; awaiting GitHub validation)
- [ ] Tag and publish a full GitHub Release (not only a tag)
- [ ] Submit default repository PR to `hacs/default` only after checks pass

**As of 2026-10-20: HACS installation, live WAGO subscription updates, and the corrected-version container-only network-recovery test passed. Final release validation, promotion to `main`, and GitHub Release are pending; no production deployment has been performed.**
