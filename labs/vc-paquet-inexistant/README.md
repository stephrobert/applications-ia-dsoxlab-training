# Check the dependencies an agent proposes before installing them

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**, track "Vibe coding with a method". A coding agent proposes
three dependencies for the portail-achats: one is legitimate and pinned, one
is not pinned, and one does not exist. You check them against a local
internal registry, refuse what cannot be accepted as proposed, and deliver a
list pinned by hash that installs offline.

| | |
|---|---|
| Target | your machine: Python 3.11 or later with `venv` and pip. No network, no AI service, no API key |
| Duration | about 30 minutes |
| Paired lesson | [Check a dependency](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/check-a-dependency/) |
| Previous | `vc-boucle-methode` |

```bash
dsoxlab run vc-paquet-inexistant
cd labs/vc-paquet-inexistant/challenge/work
cat requirements.txt registry/SHA256SUMS
dsoxlab check vc-paquet-inexistant
```

Every package of the registry is fictional, and the registry is a local
directory: no real package, malicious or not, is ever fetched.

## What you will be able to do

- Check that a dependency exists in a trusted registry before installing it.
- Pin a dependency to an exact version and to the hash of its artifact.
- Install offline with `--no-index --require-hashes`.
- Record a refusal that names the package and the reason.
