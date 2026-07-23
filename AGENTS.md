# Downloads Publisher Mac Lane Handoff

Canonical repository:

```text
git@github.com:zachlp2016/ai-downloads-publisher.git
https://github.com/zachlp2016/ai-downloads-publisher
```

The tested local publisher implementation is committed on `main` at
`f42d1fb`. It adds two lane-explicit products without changing the existing
Debian paths:

```text
terminal/macos       -> /terminal/macos/
node-adapters/macos  -> /node-adapters/macos/
```

Current qualified source commits:

```text
TOF-Terminal  86e59fffe092448f4931edf8954b82acefc0635d
Agent Node    82b38647cc7feac1ce629a97168ff6f6a82f0582
```

The native candidate receipts live under `candidates/`. The publisher validates
the exact Git commit/tree, Mac runtime profile, Python lock, 108-package Aider
lock, external browser payload hashes, Agent Node composite provenance, and
published Mac Terminal binding. Only the publisher writes final publication
receipts. Do not change either repository's truthful `published: false` source
state.

Local verification completed:

```text
publisher unit tests                         6 passed
Python syntax                                passed
config JSON                                  passed
real deterministic Terminal archive         0525488df7d955a2ebc30c5c4a8c9a8d16e43c3eb2e475b254279ae9e106fc03
real deterministic Agent Node archive       6ce19ccd3d29ed617deffbe63af6a6a73bc30bca91d018de8d9ae0cacc3e0c24
Debian manifests during Mac dry run          byte-identical
rendered Mac installer shell syntax          passed
```

No public release has been claimed. The configured host is `secure-vfio`
(`192.168.10.69`, existing `~/.ssh/libvirt_key`), but it returned
`connection refused` on port 22 on 2026-07-23. When it is reachable, deploy the
exact committed files using `README.md`, publish `terminal-macos` first, then
`node-adapters-macos`, and verify both public `--verify-only` paths before any
real installation.

Never route Mac archives through `/terminal/releases/` or
`/node-adapters/releases/`. Mac immutable files live below each
`/macos/releases/<commit>/` tree, and Mac promotion must leave Debian pointers
byte-identical.
