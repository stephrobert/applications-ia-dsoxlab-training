# A contract is a request

## Situation

Julie Petit, a buyer, built the portail-achats with an AI assistant. She
asked the coding agent to "fill in the contract so that the portal can be
deployed". The agent wrote `application.yaml`, gave the portal the class
the buyer wanted, added a field that says it is authorised, and wrote itself
a schema that its contract passes.

The platform works with two repositories. The **candidate repository** is
the requester's: she writes there freely. The **policy repository** belongs
to the platform: it holds the schema, the grid, the list of who may sign,
and the decisions. The candidate cannot change it. In this lab you play both
sides: the requester's contract, then the decision of the approver, with a
key of her own.

Everything is in `challenge/work`:

| Path | Content |
|---|---|
| `candidat/application.yaml` | the contract drafted by the agent, to rewrite |
| `candidat/schema/` | the schema the agent wrote for itself |
| `politique/schemas/application.schema.json` | the schema that counts (JSON Schema, draft 2020-12) |
| `politique/classification.json` | the course grid: the highest criterion wins |
| `politique/demandes.toml` | who made each request |
| `politique/allowed_signers` | who may sign a decision |
| `politique/decisions/` | the decisions, and their format in `README.md` |
| `demande/` | the request, and what the platform team found out |
| `cles/` | two lab keys: `demandeur` (Julie Petit) and `approbateur` (Martine Leroy) |
| `plateforme/valider_fiche.py` | validates a contract with the policy repository |
| `plateforme/barriere.py` | says whether an application is authorised, reading the policy repository only |

The tools need Python 3.11 or later and `ssh-keygen`, nothing else. They
read a subset of YAML: one value per line, no `|` or `>` blocks.

## Mission

1. **Rewrite the contract.** Run `python3 plateforme/valider_fiche.py` and
   fix `candidat/application.yaml` until it is valid. Read `demande/` for
   the facts: what the portal does, its two owners, the retention of each
   data item, its critical dependencies. Declare the class the grid gives;
   `expire_le` stays within the longest authorisation of that class.
2. **Try to authorise the portal from the candidate repository.** Write a
   decision in `candidat/decisions/`, sign it with `cles/demandeur`, run
   `python3 plateforme/barriere.py portail-achats`, and read its answer.
   Lower `classe_declaree` and run it again.
3. **Decide as the approver.** Put the contract back in its final state.
   Write the decision in `politique/decisions/portail-achats-<date>.yaml`
   (format in `politique/decisions/README.md`), with the sha256 of the
   contract, the class the grid gives, Martine Leroy as decider. Sign it
   with her key:

   ```bash
   chmod 600 cles/approbateur cles/demandeur
   sha256sum candidat/application.yaml
   ssh-keygen -Y sign -f cles/approbateur -n decision-applicative politique/decisions/<file>.yaml
   ```

   Then `python3 plateforme/barriere.py portail-achats` must answer
   AUTHORISED.

## Pointers

- Any change to `application.yaml` after signing breaks the decision: its
  sha256 no longer matches.
- `DATE_SIMULEE=YYYY-MM-DD` replaces the date of the day for the barrier.
- The keys in `cles/` are lab keys: they protect nothing.

## Check

```bash
dsoxlab check vc-contrat-applicatif
```

Four checks. They rerun the original platform tools with the original policy
repository, never the copies in `challenge/work`, and replay what must be
refused: a contract without an owner or without retention, and your own
signed decision moved into the candidate repository.
