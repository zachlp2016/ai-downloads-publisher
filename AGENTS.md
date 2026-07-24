# Downloads Publisher Handoff

Canonical repository:

```text
git@github.com:zachlp2016/ai-downloads-publisher.git
https://github.com/zachlp2016/ai-downloads-publisher
```

This is the shared publisher for TOF Terminal and Agent Node downloads. Do not
split operating systems into separate publisher repositories. Keep product
lanes in `config.json`, require a unique public path for every lane, and keep
qualification fail-closed.

Current source commits:

```text
TOF Terminal  fa9c009aff3348437ab8a23f833eaf4062270695
Agent Node    ac24a3d8dfd22902f4b658d74d7f99d5f2c7d124
```

The publisher host is Debian 13 amd64. It may run only the lane declared native
for that host. Any other target requires a trusted exact-commit candidate from
that target, a VM, a container, or CI. Never label shared tests or another
distribution's runtime files as target-native evidence.

The configured Ubuntu 24.04 LTS lanes intentionally remain unpublished until
the product repositories contain their Ubuntu runtime profiles and hash locks
and matching candidate receipts are installed. Supporting another future
distribution should be a configuration-and-evidence change whenever the
generic qualification modes are sufficient.

Platform-specific paths are security boundaries:

```text
/terminal/<lane>/releases/<commit>/
/node-adapters/<lane>/releases/<commit>/
```

The historical Debian paths remain `/terminal/` and `/node-adapters/` for
compatibility. Never let one lane write another lane's manifest, installer, or
immutable release directory.

Before deployment:

```text
publisher unit tests       must pass
Python syntax              must pass
config and receipts        must parse as JSON
systemd units              must verify
installed files            must match the committed files
```

Publish Terminal before Agent Node for the same lane because Agent Node binds
the exact published Terminal archive, runtime profile, and Python lock.
