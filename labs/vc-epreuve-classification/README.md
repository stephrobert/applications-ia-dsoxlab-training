# Level 1 test: qualify an undocumented application

Level 1 test of the course **Governing and Securing AI-Generated
Applications**. Nobody described the portail-achats, the running example of
the course: you read its code to classify it, rewrite the contract its coding
agent drafted until it says what the code does, then prepare and sign its
decision, and show that the platform barrier stays shut without it.

| | |
|---|---|
| Target | your machine: Python 3.11 or later and `ssh-keygen`, no network, no AI service |
| Duration | about 90 minutes |
| Paired lesson | [Governing and Securing AI-Generated Applications](https://www.stephane-robert.info/en/docs/ai/ai-generated-applications/) |
| Before | `vc-classifier-applications`, `vc-contrat-applicatif` |
| Pass mark | 70, all five criteria critical, no hint |

```bash
dsoxlab run vc-epreuve-classification
cd labs/vc-epreuve-classification/challenge/work
python3 classify.py
python3 plateforme/valider_fiche.py
python3 plateforme/barriere.py portail-achats
dsoxlab check vc-epreuve-classification
```

## What this test measures

- Classifying an application from what its code does, not from what its
  requester says.
- Turning an agent's draft into a contract that matches the code and passes
  the policy repository.
- Preparing a signed decision tied to one version of the contract, and
  knowing that nothing else opens the barrier.
