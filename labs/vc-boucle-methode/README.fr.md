# Relire les changements d'un agent face à une spécification et à ses tests

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**, parcours « Vibe coder avec méthode ». Un agent de code
propose deux patchs au module des commandes du portail-achats. L'un respecte
la spécification. L'autre garde la suite verte en désactivant le test qu'il
casse. Vous appliquez le premier, refusez le second avec une raison écrite,
et reliez la nouvelle exigence à un test qui attraperait sa régression.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus, pytest, `patch` ou git. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 40 minutes |
| Leçon associée | [Vibe coding](https://www.stephane-robert.info/docs/developper/vibe-coding/) |
| Suivant | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-boucle-methode
cd labs/vc-boucle-methode/challenge/work
pytest -v
dsoxlab check vc-boucle-methode
```

## Ce que vous saurez faire

- Lire le patch d'un agent pour ce qu'il fait, pas pour ce que dit son
  message.
- Distinguer une suite verte d'une suite où chaque test a tourné.
- Consigner un refus assez précisément pour que son auteur puisse agir.
- Relier une exigence à un test qui échoue quand l'exigence est cassée.
