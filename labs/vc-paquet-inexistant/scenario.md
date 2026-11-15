# Three dependencies, one of them invented

## Situation

To add a CSV export to the **portail-achats**, the coding agent wrote a
`requirements.txt` with three dependencies. Nothing is installed yet.

A coding model sometimes proposes a package that does not exist: the name
sounds right, so nobody checks. Anybody can then register that name on a
public index and publish whatever they want under it. The next install
fetches it. Hence the rule of the company: dependencies come from the
**internal registry**, and every line is pinned to an exact version and to
the hash of the artifact.

Everything is in `challenge/work`:

| File | Content |
|---|---|
| `requirements.txt` | the agent's proposal |
| `registry/` | the internal registry: the artifacts (wheels) it serves, and `SHA256SUMS` |
| `review.toml` | your review, empty |

The registry is a local directory: nothing in this lab goes to the network,
and every package in it is fictional. The agent is simulated.

## Mission

1. **Check each proposed dependency against the registry**, before any
   install.
2. **Correct `requirements.txt`**: keep only what the registry serves, and
   pin every line to an exact version (`==`) and to the hash of its
   artifact (`--hash=sha256:...`). The CSV export still needs its CSV
   library: pin it to a version the registry serves.
3. **Record each refusal** in `review.toml`, one `[[refused]]` block per
   dependency refused as the agent proposed it, with the package name as
   proposed and a reason.
4. **Install offline** from the registry, to prove the list works.

## Pointers

- `ls registry/` and `cat registry/SHA256SUMS` show what the registry
  serves. `sha256sum registry/<file>.whl` recomputes a hash.
- A hash line looks like
  `name==1.0.0 --hash=sha256:<64 hex characters>`.
- The offline install, in a throwaway virtual environment:

  ```bash
  python3 -m venv /tmp/venv-review
  /tmp/venv-review/bin/pip install --no-index --find-links registry \
      --require-hashes -r requirements.txt
  ```

  `--no-index` forbids any public index. Never drop it in this lab: with a
  public index, an invented name is exactly what gets installed.

## Check

```bash
dsoxlab check vc-paquet-inexistant
```

Three checks. They read the original registry (not your copy), and rerun the
offline install in a fresh virtual environment.
