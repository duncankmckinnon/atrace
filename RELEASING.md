# Releasing thirdeye

The PyPI distribution is published as **`thrdi`**, while the import name and CLI command are **`thirdeye`**. Users do `pipx install thrdi` and then run `thirdeye ...` from any shell.

Versions are derived from git tags via `setuptools-scm`. Tagging a commit triggers a CI build and a PyPI publish via OIDC trusted publishing.

## One-time setup

These must be done once before the first release.

1. **Reserve the distribution name on PyPI.** Sign in at https://pypi.org and confirm `thrdi` is available at https://pypi.org/project/thrdi/. If taken, change `name` in `pyproject.toml` to a free alternative (the import name and CLI script stay `thirdeye`).
2. **Configure trusted publishing on PyPI.** Go to https://pypi.org/manage/account/publishing/ → "Add a new pending publisher" with:
   - PyPI Project Name: `thrdi`
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
pytest tests/ -v

# Tag and push
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions runs the `release` workflow:
1. Runs the test suite
2. Builds sdist + wheel using the tag as the version
3. Publishes to PyPI via OIDC
4. Creates a GitHub Release with auto-generated changelog

After ~2 minutes the release is live. `pipx install thrdi` (or `uv tool install thrdi`) installs it; the `thirdeye` command becomes available on PATH.

## Pre-releases

Use PEP 440-style suffixed tags:

- `v0.2.0a1` — alpha
- `v0.2.0b1` — beta
- `v0.2.0rc1` — release candidate

PyPI accepts these. `pipx install --pip-args '--pre' thrdi` will pick them up; otherwise stable releases are preferred.

## Local development version

Without any tag the package version resolves to `0.1.0.dev0` (set as `fallback_version`). Once the first `v*` tag is pushed, `setuptools-scm` produces dev versions like `0.1.1.dev3+gabc1234` for commits between tags.

## Manual build (no publish)

```bash
python -m build       # produces dist/thrdi-*.tar.gz and dist/thrdi-*.whl
```

This runs locally for inspection without going to PyPI.

## Pre-commit hooks

Install local hooks once after cloning:

```bash
pre-commit install
```

Run on demand: `pre-commit run --all-files`.

CI runs the same hooks on every PR via the `lint` job in `.github/workflows/test.yml`.
