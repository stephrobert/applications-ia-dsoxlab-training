# Write the contract of an AI-built application and keep the candidate repository from authorising itself

Level 1 lab of the course **Governing and Securing AI-Generated
Applications**. The coding agent drafted the contract of the portail-achats,
the running example of the course, so that it "can be deployed". You rewrite
`application.yaml` until it passes the schema of the policy repository, then
sign the decision as the approver, and check that the same decision placed
in the candidate repository authorises nothing.

| | |
|---|---|
| Target | your machine: Python 3.11 or later and `ssh-keygen`, no network, no AI service |
| Duration | about 45 minutes |
| Paired lesson | [Application contract](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/application-contract/) |
| Next | `vc-boucle-methode` |

```bash
dsoxlab run vc-contrat-applicatif
cd labs/vc-contrat-applicatif/challenge/work
python3 plateforme/valider_fiche.py
python3 plateforme/barriere.py portail-achats
dsoxlab check vc-contrat-applicatif
```

The schema lives in `politique/schemas/application.schema.json` alone, and
the checks read it from there: a rule that changes touches that file only.

## What you will be able to do

- Write an application contract that names its owners, its data with their
  purpose and retention, its flows and its critical dependencies.
- Validate it with the schema of the policy repository, never with a schema
  the candidate repository brings.
- Explain why a decision in the candidate repository authorises nothing.
- Sign a decision with `ssh-keygen -Y sign` and tie it to one version of the
  contract by its sha256.
