# Version management: LG_3D

## Current authorities

Versions belong to the release units below. Equal numbers do not imply a shared release. Adoption preserves every existing version value; this document does not announce a release.

- `motion-studio-web`: `1.0.0` from `app/UI/MotionStudioWeb/package.json` (explicit opt-in edits).
  Frontend1.0.0 remains independent of desktop0.1.1.
  Verified mirrors: `app/UI/MotionStudioWeb/package-lock.json`, `app/UI/MotionStudioWeb/package-lock.json`.
- `motion-studio-desktop`: `0.1.1` from `app/UI/MotionStudioWeb/src-tauri/Cargo.toml` (explicit opt-in edits).
  Desktop0.1.1 stays separate from npm frontend1.0.0.
  Verified mirrors: `app/UI/MotionStudioWeb/src-tauri/Cargo.lock`, `app/UI/MotionStudioWeb/src-tauri/tauri.conf.json`.
- `api-service`: `0.1.0` from `app/Server/rust_api_service/Cargo.toml` (explicit opt-in edits).
  Verified mirrors: `app/Server/rust_api_service/Cargo.lock`.
- `image-service`: `0.1.0` from `app/Server/rust_image_service/Cargo.toml` (explicit opt-in edits).
  Verified mirrors: `app/Server/rust_image_service/Cargo.lock`.
- `service-monitor`: `1.0.0` from `app/UI/ServiceMonitor/pyproject.toml` (explicit opt-in edits).
  Independent Python distribution; no application imports or build backend execution.
- `coil-database-package`: `0.0.1` from `package/CoilDataBase/setup.cfg` (native read-only check). Read-only existing database client package version; database schema/migration numbers are never application versions.

## Safe local commands

Python 3.11 or newer is required. Both tools use only the standard library. They do not import the application, access devices or networks, install dependencies, run npm lifecycle hooks, build packages, commit, tag, publish, upload, or deploy.

```sh
python scripts/version_manager.py show
python scripts/version_manager.py check
python scripts/check_version_sources.py check
python -m unittest discover -s tests -p test_version_manager.py -v
python -m unittest discover -s tests -p test_version_sources.py -v
```

A bump or set previews the exact edits by default. Choose one unit explicitly; inspect the diff before opting in:

```sh
python scripts/version_manager.py bump patch --unit motion-studio-web
python scripts/version_manager.py bump patch --unit motion-studio-web --expect 1.0.0 --apply
python scripts/version_manager.py check
python scripts/check_version_sources.py check
git diff --check
git diff
```

The `1.0.0` value is an adoption-time example; replace it with the current value shown by `show`. A stale expectation is refused. `set` also previews by default and requires `--expect` with `--apply`. Review compatibility before selecting major/minor/prerelease changes. Use each ecosystem's existing build/test flow after an edit. Only explicitly listed local package lock entries are edited; registry dependencies are never version sources.

## Native and unversioned boundaries

The read-only native checker uses static parsing for CMake, setuptools INI, Python tuple-derived versions, C++ constants, and Windows resources. It never runs setup.py or evaluates arbitrary Python. For these sources, make a reviewed ecosystem-specific edit to the canonical field and its listed mirrors, then run both checks and the native build/package tests. Qt/QML import versions, database migrations, SDK/dependency versions, vendor trees, binaries, backups and Gitlinks are excluded.

- `coil-database-package`: Read-only native authority checked by scripts/check_version_sources.py. Read-only existing database client package version; database schema/migration numbers are never application versions.
  Scope: `package/CoilDataBase/setup.cfg`.
- `qt-motion-studio`: No project version in the CMake declaration; QML module1.0 is not a product release version.
  Scope: `app/UI/MotionStudio`.
- `git-submodules`: External submodules retain their exact Gitlink revisions and their own release authorities.
  Scope: `scripts/train/pytorch-image-models`.

## Source revision identity

Use `git rev-parse --verify HEAD` to record an immutable source revision for deployments. For unversioned components and datasets, include that revision with the component path and the reviewed configuration/data provenance. It is not a claim of a numbered product release.

## Release procedure

1. Select the actual release unit and inspect its existing version authority. Use source commit identity for unversioned operational components until an intentional baseline is agreed; do not label mature code 0.1.0 by guesswork.
2. Preview changes, apply only reviewed owned version fields, and run the read-only checks plus the component's normal tests/build. Review lockfile and native mirrors; keep unrelated versions unchanged.
3. Write truthful changes under `Unreleased` in `CHANGELOG.md`. Move entries into a dated release section only when a release actually occurs.
4. Review release artifacts, environment-specific configuration, compatibility, existing signing/SBOM policies and deployment approvals separately. Tags, releases, distribution and deployment are manual decisions outside this tooling.

## Adoption provenance

- Source base: [`2c2c5eba2ab18abbd727a412d0500a3f90ca8ce5`](https://github.com/a1112/LG_3D/commit/2c2c5eba2ab18abbd727a412d0500a3f90ca8ce5) from `deps/vite-6.4.4-security-20261011`.
- Observed default head: `b0af47a92bae33978ffda55b2c8a74c58ed69f05` on `main`. The default branch and prior repair refs are not changed.
- Review branch: `chore/version-management-20261012`.
- Repository tags/releases and the central R-Box-Releases identity map were checked during adoption. No central release was verified as this repository's application history. Existing source versions remain authoritative; absence of a GitHub release does not prove an application has never been delivered.
- Only version metadata, documentation, local tooling/tests and a read-only metadata CI workflow are introduced. Full native/runtime/device builds were not run for this adoption; local version-tool checks are not a product acceptance test.
