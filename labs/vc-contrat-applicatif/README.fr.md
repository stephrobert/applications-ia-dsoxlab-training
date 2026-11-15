# Rédiger la fiche applicative d'une application créée avec l'IA sans laisser le dépôt candidat s'autoriser

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**. L'agent de code a rédigé la fiche du portail-achats,
l'exemple fil rouge de la formation, pour qu'il « puisse être déployé ».
Vous reprenez `application.yaml` jusqu'à ce qu'elle passe le schéma du dépôt
de politique, signez la décision en approbatrice, et vérifiez que la même
décision posée dans le dépôt candidat n'autorise rien.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus et `ssh-keygen`, sans réseau, sans service d'IA |
| Durée | environ 45 minutes |
| Leçon associée | [Contrat applicatif](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/contrat-applicatif/) |
| Suivant | `vc-boucle-methode` |

```bash
dsoxlab run vc-contrat-applicatif
cd labs/vc-contrat-applicatif/challenge/work
python3 plateforme/valider_fiche.py
python3 plateforme/barriere.py portail-achats
dsoxlab check vc-contrat-applicatif
```

Le schéma vit dans `politique/schemas/application.schema.json` seul, et les
contrôles l'y lisent : une règle qui change ne touche que ce fichier.

## Ce que vous saurez faire

- Rédiger une fiche applicative qui nomme ses propriétaires, ses données et
  leur durée de conservation, ses flux et ses dépendances critiques.
- La valider avec le schéma du dépôt de politique, jamais avec un schéma
  qu'apporte le dépôt candidat.
- Expliquer pourquoi une décision posée dans le dépôt candidat n'autorise
  rien.
- Signer une décision avec `ssh-keygen -Y sign` et la lier à une version de
  la fiche par son empreinte sha256.
