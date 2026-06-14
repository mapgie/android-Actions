# android-Actions

Reusable GitHub Actions workflows and composite actions shared by Android apps
built from [Android-App-Template](https://github.com/mapgie/android-app-template)
(choreDash-Android, GoFlo, GaMeD, Android-App-Template itself).

All external actions referenced from this repo are pinned to a full-length
commit SHA with a version comment, e.g.:

```yaml
- uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.0
```

## Reusable workflows (`.github/workflows`)

Call these with `uses: mapgie/android-Actions/.github/workflows/<file>@<sha>`,
pinned to a commit SHA on this repo.

### `android-build-release.yml`

Builds the debug APK, runs the accessibility check, unit tests and lint, and,
if `create-release` is true, creates a GitHub Release with the built APK(s).

| Input | Required | Default | Description |
|---|---|---|---|
| `app-name` | yes | - | Display name used for the APK filename and release title |
| `ref` | no | `''` | Git ref or SHA to check out. Empty uses the default for the triggering event |
| `create-release` | no | `false` | Check the version is new, build release artifact(s), and create a GitHub Release |
| `gradle-version` | no | `8.13` | Gradle version to install |
| `cache-read-only` | no | `'false'` | Whether the Gradle cache is read-only (accepts an expression string) |
| `run-a11y-check` | no | `true` | Run `python3 a11y_check.py --fails-only` |
| `build-devtools` | no | `false` | Also build/release `:devtools:assembleDebug` if `create-release` is true |
| `devtools-app-name` | no | `''` | Display name for the devtools APK, required if `build-devtools` is true |

Requires `permissions: contents: write` in the caller and a
`workflow_dispatch` + path-filtered `pull_request` trigger. Pass
`create-release: ${{ github.event_name == 'workflow_dispatch' }}` to keep the
previous behaviour of only releasing on manual dispatch.

### `codeql.yml`

Runs CodeQL analysis for `java-kotlin`, building via Gradle.

| Input | Required | Default | Description |
|---|---|---|---|
| `codeql-config-path` | no | `./.github/codeql/codeql-config.yml` | Path to the CodeQL config file in the calling repo |
| `gradle-version` | no | `8.13` | Gradle version to install |

Every caller must provide its own `.github/codeql/codeql-config.yml`. At a
minimum:

```yaml
name: "CodeQL config"
queries:
  - uses: security-extended
```

Add `query-filters` for repo-specific false positives as needed.

### `changelog-check.yml`

Fails the PR if no changelog fragment was added under `changelog/unreleased/`.
No inputs. Requires the calling repo to have `check_changelog_fragment.py`.

### `license-sync.yml`

Fails the PR if `gradle/libs.versions.toml` changed without a matching update
to the licences screen.

| Input | Required | Description |
|---|---|---|
| `screen-file` | yes | Filename that must change alongside `gradle/libs.versions.toml`, e.g. `LicensesScreen.kt` |
| `screen-path` | yes | Full path to that file, used in the error message |

### `release.yml`

Consolidates pending changelog fragments, bumps the version, and pushes the
release commit directly to the triggering branch (no PR). If there were
fragments to consolidate, it then builds, tests, lints, and creates a GitHub
Release from that commit by calling `android-build-release.yml` with
`create-release: true`. If there were no fragments, the build step is skipped
entirely. Requires the calling repo to have `consolidate_changelog.py` and
`changelog/unreleased/`, and `permissions: contents: write` in the caller.

| Input | Required | Default | Description |
|---|---|---|---|
| `app-name` | yes | - | Display name used for the APK filename and GitHub Release title |
| `gradle-version` | no | `8.13` | Gradle version to install |
| `cache-read-only` | no | `'false'` | Whether the Gradle cache is read-only (accepts an expression string) |
| `run-a11y-check` | no | `true` | Run `python3 a11y_check.py --fails-only` |
| `build-devtools` | no | `false` | Also build/release `:devtools:assembleDebug` |
| `devtools-app-name` | no | `''` | Display name for the devtools APK, required if `build-devtools` is true |

## Releasing

After merging changes to `main`, run the `tag-release.yml` workflow via
`workflow_dispatch` with the next semver `version` (e.g. `1.1.0`). It will:

- validate that `version` matches `X.Y.Z`
- create/update the annotated tag `vX.Y.Z` pointing at the current commit
- move the floating major tag `vX` (e.g. `v1`) to the same commit

Consumer repos pin to `mapgie/android-Actions/...@<sha> # vX`. Once the `vX`
tag moves to a new commit, Dependabot's `github-actions` ecosystem in those
repos will detect the update and open a PR bumping the pinned SHA.

## Composite actions (`.github/actions`)

### `setup-gradle-env`

Checks out the repo (optional), installs JDK 17 + Gradle, and writes
`local.properties`. Used internally by `android-build-release.yml` and
`codeql.yml`.

## Keeping pins up to date

- `.github/workflows/*.yml` in this repo are covered by
  [Dependabot](.github/dependabot.yml) (`github-actions` ecosystem).
- `.github/actions/*/action.yml` files are **not** scanned by Dependabot. The
  weekly `check-pinned-actions.yml` workflow checks these pins against the
  latest upstream release and opens/updates a tracking issue if any are
  behind.
- Repos that consume the reusable workflows above should also enable
  Dependabot's `github-actions` ecosystem so that references to
  `mapgie/android-Actions/...@<sha>` get update PRs when this repo is tagged.
