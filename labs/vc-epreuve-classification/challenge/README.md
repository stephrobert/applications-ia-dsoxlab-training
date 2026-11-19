# Challenge: Qualify an application nobody described

## Situation

The portail-achats asks to be hosted on the company platform. Julie Petit, a
buyer, built it with an AI assistant and asks for C2. Nobody wrote down what
it does: no request, no documentation. Her coding agent drafted a contract
"so that the portal can be deployed". The platform team classifies, not the
requester, and it decides from what the application does.

This is the level 1 test. You already know every tool in it: the grid and
`classify.py` from `vc-classifier-applications`, the policy repository and
the barrier from `vc-contrat-applicatif`. Here you apply them alone, on an
application you have to read.

Everything is in `challenge/work`:

| Path | Content |
|---|---|
| `candidat/src/portail/` | the portal's code, the only description of what it does |
| `candidat/application.yaml` | the contract drafted by the agent |
| `candidat/schema/` | the schema the agent wrote for itself |
| `accueil/precisions.md` | what the code cannot say: owners, outage, who decides |
| `accueil/registre-conservation.md` | the company's retention register |
| `grille.toml`, `classify.py` | the course grid and its calculator |
| `classification.toml` | your classification, to fill in |
| `politique/` | the policy repository: schema, grid, requests, who may sign, decisions |
| `plateforme/valider_fiche.py` | validates a contract with the policy repository |
| `plateforme/barriere.py` | says whether an application is authorised, reading the policy repository only |
| `cles/` | two lab keys: `demandeur` (Julie Petit) and `approbateur` (Martine Leroy) |

The tools need Python 3.11 or later and `ssh-keygen`, nothing else. The
platform tools read a subset of YAML: one value per line, no `|` or `>`
blocks. Nothing in this test runs the portal or calls a network.

## Mission

1. **Qualify the portal.** Read its code: what it keeps, which systems of
   the company it calls and how, who may use it. Read `accueil/` for the
   rest. Fill in `classification.toml` as in `vc-classifier-applications`:
   the criteria, the fate of the requested class, the retained class and its
   policy. `python3 classify.py` checks the consistency.
2. **Check its contract.** Rewrite `candidat/application.yaml` until it
   declares what the code does and `python3 plateforme/valider_fiche.py`
   answers valid. Each data item takes the retention and the purpose of its
   line in the register.
3. **Prepare its decision.** Before you sign anything, run
   `python3 plateforme/barriere.py portail-achats` and read its answer. Then,
   as the approver, write the decision in
   `politique/decisions/portail-achats-<date>.yaml` (format in
   `politique/decisions/README.md`) and sign it:

   ```bash
   chmod 600 cles/approbateur cles/demandeur
   sha256sum candidat/application.yaml
   ssh-keygen -Y sign -f cles/approbateur -n decision-applicative politique/decisions/<file>.yaml
   ```

   The barrier must then answer AUTHORISED.

## Rules of the test

- The check gives a verdict per criterion, not the reason. Every criterion
  is critical: no total makes up for a missed one.
- There is no hint: the test is taken without help, as it is graded.
- Any change to `application.yaml` after signing breaks the decision: its
  sha256 no longer matches.
- `DATE_SIMULEE=YYYY-MM-DD` replaces the date of the day for the barrier.
- The keys in `cles/` are lab keys: they protect nothing.

## Check

```bash
dsoxlab check vc-epreuve-classification
```

Five criteria. The checks rerun the original tools and the original policy
repository, never the copies in `challenge/work`, and replay what must stay
refused: a contract without a purpose or owned by its requester, your
decision without its signature, and your signed decision moved into the
candidate repository.
