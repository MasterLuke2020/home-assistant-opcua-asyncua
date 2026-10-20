# Release checklist — pre-release / approval pending

## Repository and licensing
- [x] Public repository: `MasterLuke2020/home-assistant-opcua-asyncua`
- [x] Owner approved MIT license; license is now `LICENSE`
- [ ] Final review for secrets, tokens, sensitive examples, and publication metadata
- [x] Repository description, valid GitHub topics, and Issues in place
- [x] Existing integration domain `asyncua` preserved (YAML and Entity-ID compatibility)

## Runtime verification
- [x] Start completely separate HA Docker container with its own writable config and port
- [x] Verify startup, initial real PLC temperature value, and automatic subscription updates
- [ ] Verify reconnect after controlled, production-safe link interruption
- [ ] Test safe non-actuating BOOL variable if write tests are required
- [ ] Confirm no logger errors or entity registry conflicts
- [x] Verify HACS installation into a separate HA test container with live read-only WAGO temperature and subscription updates

## GitHub verification
- [x] Create separate `develop` branch for further changes
- [x] Push source and documentation
- [x] Offline-regression, HACS action, and Hassfest all pass on `develop`
- [x] Resolve HACS/Hassfest validation errors
- [x] Add local integration icon at `custom_components/asyncua/brand/icon.png`
- [ ] Once verified, bump manifest to a new patch release (proposed `1.0.4`) and update changelog
- [ ] Tag and publish a full GitHub Release (not only a tag)
- [ ] Submit default repository PR to `hacs/default` only after checks pass

**As of 2026-10-20: the repository is public, HACS installation and live read-only PLC subscription checks passed in an isolated test container; no production deployment or GitHub Release has been performed.**
