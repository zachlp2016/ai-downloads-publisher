# TechOverFL download publisher

This host-side publisher keeps the public URLs on
`https://downloads.techoverfl.com` while fetching source commits from GitHub
over the existing read-only SSH credential. GitHub SSH is pinned to
`ssh.github.com:443` with a dedicated known-hosts file so intermittent filtering
of the normal SSH port cannot stall the timer.

The systemd timer polls four explicit product/lane pairs every ten minutes:

```text
terminal/debian       -> /terminal/
node-adapters/debian  -> /node-adapters/
terminal/macos        -> /terminal/macos/
node-adapters/macos   -> /node-adapters/macos/
```

A changed commit is fetched by exact SHA into a private work directory,
scanned for credential patterns, qualified in its declared lane, archived
twice to prove deterministic output, and staged with checksums and a release
receipt. Only then is the lane's immutable release directory promoted and its
manifest atomically switched last. A Mac publication never writes either
Debian manifest.

Repository code and Debian tests run as `zachlp2016`. The service retains root
only for final promotion into the root-owned web directory. The Debian
publisher never pretends to execute native macOS tests. A Mac release instead
requires an exact-commit, private native candidate at:

```text
/var/lib/techoverfl-publisher/candidates/<product-lane>/<commit>.json
```

Candidate examples for the current Mac commits are included in `candidates/`.
Copy them with mode `0600`; publish Terminal first, then Agent Node. The
publisher re-verifies the Git tree, runtime profile, Python lock, Aider lock,
external browser payload hashes, Agent Node provenance, and the already
published Terminal binding.

Repository `published: false` remains correct for source synchronization. Only
the publisher writes the final public release receipt and manifest.

Install this patch on the publisher host:

```bash
sudo install -m 0755 tof-release-publisher /usr/local/sbin/tof-release-publisher
sudo install -m 0644 config.json /etc/techoverfl-publisher/config.json
sudo install -m 0644 README.md /usr/local/share/doc/techoverfl-publisher/README.md
sudo install -d -m 0700 /var/lib/techoverfl-publisher/candidates/terminal-macos
sudo install -d -m 0700 /var/lib/techoverfl-publisher/candidates/node-adapters-macos
sudo install -m 0600 candidates/terminal-macos/*.json \
  /var/lib/techoverfl-publisher/candidates/terminal-macos/
sudo install -m 0600 candidates/node-adapters-macos/*.json \
  /var/lib/techoverfl-publisher/candidates/node-adapters-macos/
```

A failed qualification is written to
`/var/lib/techoverfl-publisher/failed/<product>.json`. The timer skips that same
commit on later polls and tries again when GitHub advances. To explicitly retry:

```bash
sudo /usr/local/sbin/tof-release-publisher sync \
  --product terminal-macos --retry-failed

sudo /usr/local/sbin/tof-release-publisher sync \
  --product node-adapters-macos --retry-failed
```

Inspect local and GitHub state:

```bash
sudo /usr/local/sbin/tof-release-publisher status --remote
systemctl status tof-release-publisher.timer
journalctl -u tof-release-publisher.service
```
