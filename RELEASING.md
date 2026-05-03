# Releasing thirdeye

Versions are derived from git tags via `setuptools-scm`. Tagging a commit triggers a CI build and a PyPI publish via OIDC trusted publishing.

## One-time setup

These must be done once before the first release.

1. **Reserve the package name on PyPI.** Sign in at https://pypi.org and confirm `thirdeye` (or your chosen distribution name) is available. If it's taken, change `name` in `pyproject.toml` to a free alternative (the console script `thirdeye` stays the same).
2. **Configure trusted publishing on PyPI.** Go to https://pypi.org/manage/account/publishing/ → "Add a new pending publisher" with:
   - PyPI Project Name: `thirdeye`
   - Owner: `duncankmckinnon`
   - Repository: `thirdeye`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
3. **Create the `pypi` environment in GitHub.** Repo settings → Environments → New environment named `pypi`. Optionally add a required reviewer for an extra confirmation gate before publish.
4. **(Optional) Add a Codecov token.** For private repos or higher rate limits, add `CODECOV_TOKEN` as a repository secret.

## Cutting a release

```bash
# Make sure main is green
git checkout main && git pull
uv run pytest -v

# Tag and push
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions runs the `release` workflow:
1. Builds sdist + wheel using the tag as the version
2. Runs the test suite against the built code
3. Publishes to PyPI via OIDC

After ~2 minutes the release is live. `pipx install thirdeye` (or `uv tool install thirdeye`) installs it.

## Pre-releases

Use PEP 440-style suffixed tags:

- `v0.2.0a1` — alpha
- `v0.2.0b1` — beta
- `v0.2.0rc1` — release candidate

PyPI accepts these. `pipx install --pip-args '--pre' thirdeye` will pick them up; otherwise stable releases are preferred.

## Local development version

Without any tag the package version resolves to `0.1.0.dev0` (set as `fallback_version`). Once the first `v*` tag is pushed, `setuptools-scm` produces dev versions like `0.1.1.dev3+gabc1234` for commits between tags.

## Manual build (no publish)

```bash
uv build              # produces dist/thirdeye-*.tar.gz and dist/thirdeye-*.whl
```

This runs locally for inspection without going to PyPI.

## Pre-commit hooks

Install local hooks once after cloning:

```bash
uv run pre-commit install
```

Run on demand: `uv run pre-commit run --all-files`.

CI runs the same hooks on every PR via the `pre-commit` job in `.github/workflows/test.yml`.
