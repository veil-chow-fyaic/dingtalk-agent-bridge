## Change

Describe the concrete problem and resulting behavior. Link the issue or acceptance criterion if one exists.

## Validation

List the commands actually run, platform/Python version, and results. Keep synthetic checks separate from any authorized real-client evidence. State checks that were not run.

## Review checklist

- [ ] This uses the official DWS path where available and keeps runtimes/organizations optional.
- [ ] Unknown delivery is reconciled using its original key, without blind retransmission.
- [ ] Public changes contain no credentials, real identities, private messages, logs, downloads, screenshots, or databases.
- [ ] Relevant documentation is indexed; the public handoff manifest and offline checks are current.
- [ ] Any new dependency or permission is explained; no implicit authentication repair or live business operation is added to CI.
