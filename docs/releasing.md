# Releasing Niche Hunter

`develop` holds ongoing work. `master` is the tested public distribution source. Users follow `master` through their client's marketplace or pin an immutable `vMAJOR.MINOR.PATCH` tag. Do not move published tags or overwrite a release with different bytes; publish a new version for a correction.

## Version and package

The product release version is `plugin.json.version`. Mirror it in `.claude-plugin/plugin.json`; `scripts/release.py check` rejects a mismatch. Each release needs a matching section in `CHANGELOG.md`. The research JSON contract (`research.py`'s `VERSION`) is independent; change it only when the data contract changes, not for every plugin release.

Both marketplaces resolve the plugin at their own checked-out root (`./`). Do not replace that source with an unpinned remote `master` URL: it would let an old marketplace tag install a newer runtime and break rollback. Codex and Claude metadata differ, but `skills/niche-hunter/` is the only research implementation.

The release ZIP is built from an explicit runtime allowlist and normalized ZIP metadata. It includes the manifests/marketplaces, shared skill, README, public avatar, license and changelog. Contributor-only README links resolve to the corresponding versioned source on GitHub. Research exports, machine instructions, repository tests, bytecode and credentials are excluded. Runtime components have no filesystem links outside the package root. `SHA256SUMS` covers the ZIP. It is a consistency check, not a detached signature.

## Prepare a release on develop

1. Update both product manifest versions and add a dated changelog entry. Keep previous entries for users choosing a rollback tag.
2. Update README and the English development plan with actual capabilities and verification limits. Keep skill examples portable.
3. Run from the repository root:

```bash
python3 scripts/release.py check
python3 -m unittest discover -s tests -v
python3 scripts/release.py build --out dist
git diff --check
```

4. Validate with actual clients where available: `claude plugin validate .` checks marketplace metadata; validate `.claude-plugin/plugin.json` for the plugin manifest. Extract the ZIP to a temporary directory and validate that copy too. Exercise marketplace discovery/install/update/pinning with current Codex/Claude versions. Keep synthetic artifact transitions distinct from native client tests and real research.
5. Commit and push to `develop`. Wait for CI to pass on that exact commit before promoting it. Review PRs before merging; do not publish failing changes just because local checks passed.

CI runs the release checks and helper/artifact tests on Python 3.10 and 3.14. It does not establish provider access or model analysis quality. Configure branch protection/required CI checks in GitHub settings if administrative enforcement is desired; workflow files alone do not protect branches.

## Promote and publish

For the initial release use `v0.1.0`; substitute the new version below for later releases. Fetch remote state and ensure the local worktree is clean. A fast-forward promotion is appropriate when `master` is an ancestor of the tested `develop` commit; if histories differ, review/resolve the change instead of force-pushing.

```bash
git fetch origin
git switch master
git merge --ff-only develop
git push origin master
python3 scripts/release.py check --tag v0.1.0
git tag -a v0.1.0 -m "Niche Hunter v0.1.0"
git push origin v0.1.0
git switch develop
```

The tag-triggered `Release` workflow verifies the version/changelog, requires the tagged commit to be contained in `master`, reruns tests, builds the runtime ZIP/checksum, and creates a GitHub Release using that version's changelog notes. GitHub provides the workflow's repository token; maintainers do not commit a personal token or provider credentials.

Verify the Release workflow succeeded and that the [published release](https://github.com/roland19deschain/niche-hunter/releases) contains the expected tag, source commit, notes, ZIP and checksum. A successful `git push` alone is not proof of a published release. Download the asset and verify its checksum, then test the README's GitHub marketplace installation for both clients. New research outputs belong in the caller's working project.

If publication fails, inspect the workflow and correct the cause. A rerun can finish an interrupted job if no Release was created. If a Release already exists, inspect its assets before retrying; the workflow deliberately refuses to overwrite it. Do not delete/recreate published tags to make a failed release appear successful.

## Pinning, rollback and recovery

Use the README's [Rollback](../README.md#rollback) instructions to remove the active installation/source and reinstall from a published tag. A pinned marketplace stays at that version; refresh does not switch it to the stable branch. Returning to `master` is an explicit source change. Keep credentials in client facilities and reports/imports outside plugin caches.

For a problematic stable release, publish a new patch version containing the correction (or an intentional code revert with a new version). Communicate the issue and last known-good tag in the release notes. Product version, JSON schema version, actual provider coverage, and client compatibility should be recorded separately in bug reports.

## Official client references

- [Codex plugin manifests, marketplaces and refresh](https://developers.openai.com/plugins/build/plugins).
- [Claude Code plugin installation and updates](https://code.claude.com/docs/en/discover-plugins).
- [Claude Code marketplace sources and tags](https://code.claude.com/docs/en/plugin-marketplaces).
