# Classify four AI-built applications and apply the policy of their class

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**. Four requests, including the portail-achats, the running
example of the course, ask to be hosted. You read each one against the
course grid, reject the requests that ask for less than the grid gives, and
apply to each application the policy its class imposes.

| | |
|---|---|
| Target | your machine: Python 3.11 or later, no dependency, no network, no AI service |
| Duration | about 45 minutes |
| Paired lesson | [Classify an application](https://www.stephane-robert.info/en/docs/ia/applications-generees-par-ia/classer-une-application/) |
| Next | `vc-boucle-methode` |

```bash
dsoxlab run vc-classifier-applications
cd labs/vc-classifier-applications/challenge/work
python3 classify.py
dsoxlab check vc-classifier-applications
```

The grid's values live in `grille.toml` alone, and the checks read them
from there: a change of threshold touches that file only.

## What you will be able to do

- Score an application on data, flows to the information system, users and
  business criticality, from what it does rather than from what its
  requester says.
- Apply the rule "the highest criterion wins", even to a team of three.
- Reject an underestimated class without arguing about it.
- Tie each class to its controls, approval and authorisation length.
