import importlib.machinery
import importlib.util
import json
import os
import pwd
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
loader = importlib.machinery.SourceFileLoader(
    "tof_release_publisher", str(ROOT / "tof-release-publisher")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
publisher_module = importlib.util.module_from_spec(spec)
loader.exec_module(publisher_module)


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.public = self.root / "public"
        self.ssh_key = self.root / "key"
        self.known_hosts = self.root / "known_hosts"
        self.public.mkdir()
        self.ssh_key.write_text("fixture\n", encoding="utf-8")
        self.known_hosts.write_text("fixture\n", encoding="utf-8")
        os.chmod(self.ssh_key, 0o600)
        user = pwd.getpwuid(os.geteuid()).pw_name
        self.config = {
            "state_root": str(self.state),
            "public_root": str(self.public),
            "run_as_user": user,
            "ssh_key": str(self.ssh_key),
            "known_hosts": str(self.known_hosts),
            "node_binary": "/usr/bin/false",
            "products": {
                "terminal": {
                    "product": "terminal",
                    "qualification_lane": "debian",
                    "qualification_mode": "publisher_native",
                    "qualification_label": "Debian 13 amd64",
                    "repository_ssh": "git@example/terminal",
                    "repository_https": "https://example/terminal",
                    "ref": "refs/heads/main",
                    "public_path": "terminal",
                    "archive_prefix": "tof-terminal",
                    "runtime": {
                        "profile_id": "debian-13-amd64-python3.13",
                        "profile_path": "runtime/debian-13-amd64.json",
                        "python_lock_path": "runtime/python.lock",
                        "expected_platform": {
                            "os_release_id": "debian",
                            "os_release_version_id": "13",
                        },
                    },
                },
                "terminal-macos": {
                    "product": "terminal",
                    "qualification_lane": "macos",
                    "qualification_mode": "trusted_candidate",
                    "qualification_label": "macOS 26 arm64",
                    "repository_ssh": "git@example/terminal",
                    "repository_https": "https://example/terminal",
                    "ref": "refs/heads/main",
                    "public_path": "terminal/macos",
                    "archive_prefix": "tof-terminal",
                    "runtime": {
                        "profile_id": "macos-26-arm64-python3.14",
                        "profile_path": "runtime/macos-26-arm64.json",
                        "python_lock_path": "runtime/python-macos.lock",
                        "expected_platform": {
                            "os_release_id": "macos",
                            "os_release_version_id": "26",
                        },
                    },
                },
                "node-adapters-macos": {
                    "product": "node-adapters",
                    "qualification_lane": "macos",
                    "qualification_mode": "trusted_candidate",
                    "qualification_label": "macOS 26 arm64",
                    "repository_ssh": "git@example/node",
                    "repository_https": "https://example/node",
                    "ref": "refs/heads/main",
                    "public_path": "node-adapters/macos",
                    "archive_prefix": "tof-agent-node",
                    "terminal_public_path": "terminal/macos",
                    "terminal_profile_id": "macos-26-arm64-python3.14",
                },
                "terminal-ubuntu": {
                    "product": "terminal",
                    "qualification_lane": "ubuntu",
                    "qualification_mode": "trusted_candidate",
                    "qualification_label": "Ubuntu 24.04 LTS amd64",
                    "repository_ssh": "git@example/terminal",
                    "repository_https": "https://example/terminal",
                    "ref": "refs/heads/main",
                    "public_path": "terminal/ubuntu",
                    "archive_prefix": "tof-terminal",
                    "runtime": {
                        "profile_id": "ubuntu-24.04-amd64-python3.12",
                        "profile_path": "runtime/ubuntu-24.04-amd64.json",
                        "python_lock_path": "runtime/python-ubuntu.lock",
                        "expected_platform": {
                            "os_release_id": "ubuntu",
                            "os_release_version_id": "24.04",
                        },
                    },
                },
            },
        }
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(self.config), encoding="utf-8")
        self.publisher = publisher_module.Publisher(config_path)

    def tearDown(self):
        self.temporary.cleanup()

    def test_configuration_accepts_new_lanes_and_rejects_path_collisions(self):
        self.assertIn("terminal-ubuntu", self.publisher.products)
        broken = json.loads(json.dumps(self.config))
        broken["products"]["terminal-ubuntu"]["public_path"] = "terminal"
        path = self.root / "broken.json"
        path.write_text(json.dumps(broken), encoding="utf-8")
        with self.assertRaisesRegex(
            publisher_module.PublisherError, "duplicates public path"
        ):
            publisher_module.Publisher(path)

    def test_native_candidate_is_exact_commit_and_private_file(self):
        commit = "a" * 40
        candidate_dir = self.state / "candidates" / "terminal-macos"
        candidate_dir.mkdir(parents=True)
        candidate = candidate_dir / f"{commit}.json"
        candidate.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "qualified_candidate",
                    "product": "terminal",
                    "qualification_lane": "macos",
                    "source_commit": commit,
                    "qualification": {"status": "passed"},
                }
            ),
            encoding="utf-8",
        )
        os.chmod(candidate, 0o600)
        admitted = self.publisher.candidate_gate(
            "terminal-macos",
            self.publisher.products["terminal-macos"],
            commit,
        )
        self.assertRegex(admitted["_candidate_sha256"], r"^[0-9a-f]{64}$")
        altered = json.loads(candidate.read_text(encoding="utf-8"))
        altered["source_commit"] = "b" * 40
        candidate.write_text(json.dumps(altered), encoding="utf-8")
        with self.assertRaisesRegex(
            publisher_module.QualificationError, "mismatch for source_commit"
        ):
            self.publisher.candidate_gate(
                "terminal-macos",
                self.publisher.products["terminal-macos"],
                commit,
            )

    def test_mac_installer_uses_mac_base_and_native_checksum_fallback(self):
        template = self.root / "install.sh"
        template.write_text(
            """#!/usr/bin/env bash
readonly BASE_URL="https://downloads.techoverfl.com/terminal"
readonly RELEASE_COMMIT="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
readonly RELEASE_SHORT="aaaaaaaaaaaa"
readonly ARCHIVE_SHA256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
for required_command in curl sha256sum tar mktemp awk; do
  :
done
printf '%s  %s\\n' "${ARCHIVE_SHA256}" "${archive_path}" | sha256sum --check --status
""",
            encoding="utf-8",
        )
        rendered = self.publisher.installer_for(
            template,
            "b" * 40,
            "c" * 64,
            base_url="https://downloads.techoverfl.com/terminal/macos",
            portable_checksum=True,
        ).decode()
        self.assertIn(
            'readonly BASE_URL="https://downloads.techoverfl.com/terminal/macos"',
            rendered,
        )
        self.assertIn("command -v shasum", rendered)
        self.assertIn("printf '%s  %s\\n'", rendered)
        self.assertNotIn("curl sha256sum tar", rendered)

    def test_shared_installer_template_is_a_file_path(self):
        product = self.publisher.products["terminal-macos"]
        product["installer_template_public_path"] = "terminal/install.sh"
        self.assertEqual(
            self.publisher.installer_template_path(product),
            self.public / "terminal" / "install.sh",
        )

    def test_mac_promotion_cannot_change_debian_pointer(self):
        commit = "d" * 40
        debian_manifest = self.public / "terminal" / "manifest.json"
        debian_manifest.parent.mkdir()
        debian_bytes = b'{"commit":"debian-sentinel"}\n'
        debian_manifest.write_bytes(debian_bytes)
        staging = self.root / "staging"
        staging.mkdir()
        archive_name = "tof-terminal-dddddddddddd.tar.gz"
        archive = staging / archive_name
        archive.write_bytes(b"archive")
        manifest = {
            "archive": {
                "filename": archive_name,
                "sha256": publisher_module.sha256_file(archive),
            }
        }
        self.publisher.promote(
            self.publisher.products["terminal-macos"],
            commit,
            staging,
            manifest,
            b"#!/usr/bin/env bash\n",
            b"Mac lane\n",
        )
        self.assertEqual(debian_manifest.read_bytes(), debian_bytes)
        self.assertTrue(
            (self.public / "terminal" / "macos" / "manifest.json").is_file()
        )
        self.assertTrue(
            (
                self.public
                / "terminal"
                / "macos"
                / "releases"
                / commit
                / archive_name
            ).is_file()
        )

    def test_mac_terminal_documents_are_lane_bound_and_include_aider_lock(self):
        staging = self.root / "documents"
        staging.mkdir()
        profile_path = self.root / "macos-26-arm64.json"
        lock_path = self.root / "python.lock"
        aider_lock_path = self.root / "aider.lock"
        profile_path.write_text('{"profile":"macos-26-arm64-python3.14"}\n')
        lock_path.write_text("terminal==1 --hash=sha256:" + "a" * 64 + "\n")
        aider_lock_path.write_text("aider-chat==0.86.2 --hash=sha256:" + "b" * 64 + "\n")
        archive = {
            "filename": "tof-terminal-aaaaaaaaaaaa.tar.gz",
            "bytes": 7,
            "sha256": "c" * 64,
            "root_directory": "tof-terminal-aaaaaaaaaaaa",
        }
        validation = {
            "python": "3.14",
            "pytest": {"passed": 1, "failed": 0, "skipped": 0},
            "profile": {
                "profile": "macos-26-arm64-python3.14",
                "playwright": {"version": "1", "artifacts": []},
            },
            "profile_path": profile_path,
            "profile_relative_path": "runtime/macos-26-arm64.json",
            "lock_path": lock_path,
            "lock_relative_path": "runtime/python-macos26-arm64-py314.lock",
            "aider_lock_path": aider_lock_path,
            "aider_lock_relative_path": "runtime/aider-macos-arm64-py312.lock",
            "aider_lock": {"package_count": 1},
            "candidate": {"_candidate_sha256": "d" * 64},
            "python_hash_lock_dry_run": "passed",
            "aider_hash_lock_dry_run": "passed",
            "external_payload_hashes_verified": "passed",
            "playwright": {"version": "1", "artifacts": []},
        }
        receipt, manifest, _ = self.publisher.terminal_documents(
            self.publisher.products["terminal-macos"],
            "a" * 40,
            archive,
            10,
            validation,
            staging,
            "2026-07-23T00:00:00Z",
        )
        prefix = "https://downloads.techoverfl.com/terminal/macos/releases/"
        self.assertTrue(manifest["archive"]["url"].startswith(prefix))
        self.assertEqual(
            manifest["runtime_profiles"][0]["qualification_lane"],
            "macos",
        )
        self.assertIn("runtime", receipt)
        self.assertTrue(
            (staging / "runtime" / "aider-macos-arm64-py312.lock").is_file()
        )

    def test_mac_node_documents_bind_the_mac_terminal_lane(self):
        archive = {
            "filename": "tof-agent-node-aaaaaaaaaaaa.tar.gz",
            "bytes": 7,
            "sha256": "c" * 64,
            "root_directory": "tof-agent-node-aaaaaaaaaaaa",
        }
        validation = {
            "node": "22.22.2",
            "tests": {"passed": 1, "failed": 0, "skipped": 0},
            "candidate": {"_candidate_sha256": "d" * 64},
            "terminal_binding": {
                "qualification_lane": "macos",
                "commit": "e" * 40,
                "archive_sha256": "f" * 64,
                "runtime_profile_sha256": "1" * 64,
                "python_lock_sha256": "2" * 64,
                "installed": False,
                "query_ready": False,
                "build_ready": False,
            },
        }
        receipt, manifest, _ = self.publisher.node_documents(
            self.publisher.products["node-adapters-macos"],
            "a" * 40,
            archive,
            10,
            validation,
            "2026-07-23T00:00:00Z",
        )
        self.assertTrue(
            manifest["archive"]["url"].startswith(
                "https://downloads.techoverfl.com/node-adapters/macos/releases/"
            )
        )
        self.assertEqual(
            manifest["component_bindings"]["tof-terminal"]["qualification_lane"],
            "macos",
        )
        self.assertEqual(receipt["qualification"]["lane"], "macos")


if __name__ == "__main__":
    unittest.main()
