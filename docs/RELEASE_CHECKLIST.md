# Release checklist — NOT YET APPROVED

## Before GitHub creation
- [ ] Confirm new repository owner/name. Proposed: `MasterLuke2020/home-assistant-opcua-asyncua`
- [ ] Approve publication license. Proposed MIT; review `LICENSE.DRAFT`, then rename it to `LICENSE` if approved
- [ ] Ensure no passwords, tokens, local production config, or private IP addresses are included in tracked files
- [ ] Set repository description, GitHub topics, and enable Issues
- [ ] Keep existing integration domain `asyncua` (YAML and Entity-ID compatibility)

## Runtime verification
- [ ] Start completely separate HA Docker container with its own writable config and port
- [ ] Connect read-only test variables on the PLC; verify startup, subscriptions, and reconnect
- [ ] Test safe non-actuating BOOL variable if write tests are required
- [ ] Confirm no logger errors or entity registry conflicts
- [ ] Verify HACS installation into a separate HA test container

## GitHub verification
- [ ] Create separate `develop` branch for further changes
- [ ] Push source and documentation
- [ ] Let offline-regression, HACS action, and hassfest pass
- [ ] Resolve any issues HACS/hassfest reports
- [ ] Add integration icon (required for HACS default listing; use accepted Home Assistant branding process)
- [ ] Once verified, bump manifest to a new patch release (proposed `1.0.4`) and update changelog
- [ ] Tag and publish a full GitHub Release (not only a tag)
- [ ] Submit default repository PR to `hacs/default` only after checks pass

**No production deployment, public repository or release has been performed by this staging package.**
