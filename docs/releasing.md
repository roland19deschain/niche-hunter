# Releasing Niche Hunter

`develop` holds ongoing work. `master` is the tested public distribution source. Users follow `master` through their client's marketplace or pin an immutable `MAJOR.MINOR.PATCH` tag. Do not move published tags or overwrite a release with different bytes; publish a new version for a correction.

## Version and package

Release tags match the product version exactly, without a leading `v` (for example `0.2.0`). The archive is named `niche-hunter-MAJOR.MINOR.PATCH.zip`.

The product release version is `plugin.json.version`. Mirror it in `.claude-plugin/plugin.json` and `desktop/manifest.json`. The release check validates the plugin versions, and the Desktop build checks its version against the plugin. Each release needs a matching section in `CHANGELOG.md`. The research JSON contract (`research.py`'s `VERSION`) is independent; change it only when the data contract changes, not for every plugin release.

Both marketplaces resolve the plugin at their own checked-out root (`./`). Do not replace that source with an unpinned remote `master` URL: it would let an old marketplace tag install a newer runtime and break rollback. Codex and Claude metadata differ, but `skills/niche-hunter/` is the only research implementation.

The release ZIP is built from an explicit runtime allowlist and normalized ZIP metadata. It includes the manifests/marketplaces, client-specific MCP connection declarations, shared skill, README, privacy disclosure, public avatar, license and changelog, plus declared PDF requirements and licensed report fonts. Contributor-only README links resolve to the corresponding versioned source on GitHub. Research exports, machine instructions, repository tests, bytecode and credentials are excluded. Runtime components have no filesystem links outside the package root. The release also includes the Apple silicon `niche-hunter-desktop-MAJOR.MINOR.PATCH-macos-arm64.mcpb` and the uploadable `niche-hunter-skill-MAJOR.MINOR.PATCH.zip`. The published `SHA256SUMS` covers all three archives and verifies their contents against the published hashes.

## Prepare a release on develop

1. Update the product and Desktop manifest versions and add a dated changelog entry. Keep previous entries for users choosing a rollback tag.
2. Update README and the English development plan with actual capabilities and verification limits. Keep skill examples portable.
3. Run from the repository root:

```bash
python3 -m pip install -r skills/niche-hunter/requirements-pdf.txt pypdf
python3 scripts/release.py check
python3 -m unittest discover -s tests -v
python3 scripts/release.py build --out dist
git diff --check
```

4. Validate with actual clients where available: `claude plugin validate .` checks marketplace metadata; validate `.claude-plugin/plugin.json` for the plugin manifest. Extract the ZIP to a temporary directory and validate that copy too. Exercise marketplace discovery/install/update/pinning with current Codex/Claude versions. Keep synthetic artifact transitions distinct from native client tests and real research.
5. Commit and push to `develop`. Wait for CI to pass on that exact commit before promoting it. Review PRs before merging; do not publish failing changes just because local checks passed.

CI runs the release checks and helper/artifact tests on Python 3.10 and 3.14. It does not establish provider access or model analysis quality. Configure branch protection/required CI checks in GitHub settings if administrative enforcement is desired; workflow files alone do not protect branches.

## Promote and publish

The commands below illustrate `0.2.0`; substitute the agreed new version for later releases. Fetch remote state and ensure the local worktree is clean. A fast-forward promotion is appropriate when `master` is an ancestor of the tested `develop` commit; if histories differ, review/resolve the change instead of force-pushing.

```bash
git fetch origin
git switch master
git merge --ff-only develop
git push origin master
python3 scripts/release.py check --tag 0.2.0
git tag -a 0.2.0 -m "Niche Hunter 0.2.0"
git push origin 0.2.0
git switch develop
```

The tag-triggered `Release` workflow runs on an Apple silicon macOS runner. It verifies the version/changelog, requires the tagged commit to be contained in `master`, reruns the shared and Desktop tests, builds all three archives, and creates a GitHub Release using that version's changelog notes. GitHub provides the workflow's repository token; maintainers do not commit a personal token or provider credentials.

Verify the Release workflow succeeded and that the [published release](https://github.com/roland19deschain/niche-hunter/releases) contains the expected tag, source commit, notes, three archives and checksum file. Download the archives and verify them with `shasum -a 256 -c SHA256SUMS` from their shared directory. Test the marketplace installations and Claude Desktop's extension and skill upload paths separately. New research outputs belong in the caller's working project or the Desktop reports directory.

If publication fails, inspect the workflow and correct the cause. A rerun can finish an interrupted job if no Release was created. If a Release already exists, inspect its assets before retrying; the workflow deliberately refuses to overwrite it. Do not delete/recreate published tags to make a failed release appear successful.

## Pinning, rollback and recovery

Use the README's [Rollback](../README.md#rollback) instructions to remove the active installation/source and reinstall from a published tag. A pinned marketplace stays at that version; refresh does not switch it to the stable branch. Returning to `master` is an explicit source change. Keep credentials in client facilities and reports/imports outside plugin caches.

For a problematic stable release, publish a new patch version containing the correction (or an intentional code revert with a new version). Communicate the issue and last known-good tag in the release notes. Product version, JSON schema version, actual provider coverage, and client compatibility should be recorded separately in bug reports.

## Official client references

- [Codex plugin manifests, marketplaces and refresh](https://developers.openai.com/plugins/build/plugins).
- [Claude Code plugin installation and updates](https://code.claude.com/docs/en/discover-plugins).
- [Claude Code marketplace sources and tags](https://code.claude.com/docs/en/plugin-marketplaces).

## One-time tag migration — November 5, 2026

At the maintainer's explicit request, the initial `v0.1.0` and `v0.2.0` tag names were replaced with `0.1.0` and `0.2.0`. Their source commits are preserved. The corresponding Releases, ZIP names, packaged README links and checksums use the new names. Only the packaged README changed; runtime files are unchanged. This is an authorized migration before public adoption, not the procedure for future corrections. See development-plan section 20 for verification and asset hashes. Historical source snapshots and workflow runs predate this convention.
