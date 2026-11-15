# Four requests, one grid

## Situation

Four applications built with AI help ask to be hosted on the company
platform. Each request comes with the class its requester asks for. The
platform team classifies, not the requester: a requested class is a request,
never a decision.

Everything is in `challenge/work`:

| File | Content |
|---|---|
| `demandes/*.md` | the four requests, in English and in French |
| `grille.toml` | the course grid: four criteria scored 0 to 3, the class each score gives, and what each class imposes |
| `classification.toml` | your classification, to fill in |
| `classify.py` | computes each class from your criteria and checks your file (Python 3.11 or later, no dependency) |

The grid in one sentence: each criterion (data, flows to the information
system, users, business criticality) gives a score from 0 to 3, and **the
highest criterion wins**. Score 0 gives C1, 1 gives C2, 2 gives C3, 3 gives
C4. A class may go up one step without discussion; it only goes down with a
written human decision, which this lab does not have.

## Mission

For each of the four applications, in `classification.toml`:

1. **Read the request** and give each criterion its value, a key of
   `grille.toml` (for example `donnees = "personnelles"`). Read what the
   application does, not what the requester concludes.
2. **Decide on the request**: `decision_demande = "rejetee"` when the
   requested class is below what the grid gives, `"acceptee"` otherwise.
   Leave `classe_demandee` as it is: it is the requester's word.
3. **Retain a class** (`classe_retenue`).
4. **Apply the policy** of the retained class in the `[politique]` table:
   the five fields of `[classes.Cn.impose]` in `grille.toml`
   (`deploiement_plateforme`, `controles`, `approbation`,
   `fiches_decision_signees`, `duree_autorisation_mois`). The duration is a
   maximum: any whole number of months from 1 up to it is valid, and 0 for
   a class that gets no authorisation.

## Pointers

- `python3 classify.py` shows, for each application, the requested, computed
  and retained classes, and what is still inconsistent.
- The script trusts your criteria. Whether they match the request is your
  part of the work, and the check verifies it.

## Check

```bash
dsoxlab check vc-classifier-applications
```

Three checks. They rerun the original `classify.py` on your file, and compare
your criteria with the requests.
