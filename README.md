# TechOverFL downloads publisher

This repository is the shared release publisher for TechOverFL products. It
fetches exact Git commits, validates each configured release lane, builds
deterministic archives, and atomically updates
`https://downloads.techoverfl.com`.

Products and operating-system lanes are data-driven entries in `config.json`.
The current configuration defines:

```text
terminal/debian       -> /terminal/
terminal/ubuntu       -> /terminal/ubuntu/
terminal/macos        -> /terminal/macos/
node-adapters/debian  -> /node-adapters/
node-adapters/ubuntu  -> /node-adapters/ubuntu/
node-adapters/macos   -> /node-adapters/macos/
```

Each public path has its own manifest and immutable
`releases/<commit>/` tree. Publishing one lane cannot replace another lane's
pointer. Adding a future distribution normally requires:

1. a new product/lane entry with a unique public path;
2. an exact runtime profile and dependency lock;
3. native, VM, container, or CI qualification evidence for the target; and
4. a trusted candidate receipt when the publisher host is not the target.

The publisher fails closed when any of those inputs is absent. The Ubuntu lanes
are configured now, but the current product commits do not yet include their
Ubuntu runtime profiles, locks, or candidate receipts, so no Ubuntu release is
claimed until that evidence exists.

## Safety model

GitHub access uses the existing read-only SSH credential through
`ssh.github.com:443` and a dedicated known-hosts file. Repository code and
native tests run as `zachlp2016`. The service retains root only for final
promotion into the root-owned web directory.

A changed commit is fetched by exact SHA, scanned for credential patterns,
qualified in its declared lane, archived twice to prove deterministic output,
and staged with checksums and a release receipt. The manifest is switched last.
Failed qualification is recorded under
`/var/lib/techoverfl-publisher/failed/` and is retried only when the source
commit advances or an operator uses `--retry-failed`.

## Install or upgrade

```bash
sudo install -m 0755 tof-release-publisher \
  /usr/local/sbin/tof-release-publisher
sudo install -m 0644 config.json \
  /etc/techoverfl-publisher/config.json
sudo install -m 0644 README.md \
  /usr/local/share/doc/techoverfl-publisher/README.md
sudo install -m 0644 tof-release-publisher.service \
  /etc/systemd/system/tof-release-publisher.service
sudo install -m 0644 tof-release-publisher.timer \
  /etc/systemd/system/tof-release-publisher.timer

sudo install -d -m 0700 \
  /var/lib/techoverfl-publisher/candidates/terminal-macos \
  /var/lib/techoverfl-publisher/candidates/node-adapters-macos
sudo install -m 0600 candidates/terminal-macos/*.json \
  /var/lib/techoverfl-publisher/candidates/terminal-macos/
sudo install -m 0600 candidates/node-adapters-macos/*.json \
  /var/lib/techoverfl-publisher/candidates/node-adapters-macos/

sudo systemctl daemon-reload
sudo systemctl enable --now tof-release-publisher.timer
```

Candidate receipt directories are technical trust boundaries. Create an
equivalent root-owned, mode-`0700` directory and mode-`0600` receipt whenever a
future non-native lane is admitted.

## Operate

Inspect local and GitHub state:

```bash
sudo /usr/local/sbin/tof-release-publisher status --remote
systemctl status tof-release-publisher.timer
journalctl -u tof-release-publisher.service
```

Synchronize one lane explicitly:

```bash
sudo /usr/local/sbin/tof-release-publisher sync --product terminal-ubuntu
```

Qualify and build a lane without changing public files:

```bash
sudo /usr/local/sbin/tof-release-publisher sync \
  --product terminal-ubuntu \
  --dry-run
```

Retry a previously blocked commit only after its qualification inputs have been
corrected:

```bash
sudo /usr/local/sbin/tof-release-publisher sync \
  --product terminal-ubuntu \
  --retry-failed
```
