# Épreuve du niveau 1 : qualifier une application non documentée

Épreuve du niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**. Personne n'a décrit le portail-achats, le fil rouge de la
formation : vous lisez son code pour le classer, reprenez la fiche que son
agent de code a rédigée jusqu'à ce qu'elle dise ce que fait le code, puis
préparez et signez sa décision, et montrez que la barrière de la plateforme
reste fermée sans elle.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus et `ssh-keygen`, sans réseau, sans service d'IA |
| Durée | environ 90 minutes |
| Leçon associée | [Sécuriser et gouverner les applications générées par IA](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/) |
| Avant | `vc-classifier-applications`, `vc-contrat-applicatif` |
| Seuil | 70, les cinq critères critiques, aucun indice |

```bash
dsoxlab run vc-epreuve-classification
cd labs/vc-epreuve-classification/challenge/work
python3 classify.py
python3 plateforme/valider_fiche.py
python3 plateforme/barriere.py portail-achats
dsoxlab check vc-epreuve-classification
```

## Ce que mesure cette épreuve

- Classer une application d'après ce que fait son code, pas d'après ce qu'en
  dit sa demandeuse.
- Transformer le brouillon d'un agent en une fiche fidèle au code, qui passe
  le dépôt de politique.
- Préparer une décision signée, liée à une version de la fiche, en sachant
  que rien d'autre n'ouvre la barrière.
