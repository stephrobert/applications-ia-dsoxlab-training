# Classer quatre applications créées avec l'IA et appliquer la politique de leur classe

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**. Quatre demandes, dont le portail-achats, l'exemple fil
rouge de la formation, demandent à être hébergées. Vous lisez chacune avec
la grille de la formation, rejetez les demandes qui réclament moins que ce
que donne la grille, et appliquez à chaque application la politique
qu'impose sa classe.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus, sans dépendance, sans réseau, sans service d'IA |
| Durée | environ 45 minutes |
| Leçon associée | [Classer une application](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/classer-une-application/) |
| Suivant | `vc-boucle-methode` |

```bash
dsoxlab run vc-classifier-applications
cd labs/vc-classifier-applications/challenge/work
python3 classify.py
dsoxlab check vc-classifier-applications
```

Les valeurs de la grille vivent dans `grille.toml` seul, et les contrôles
les y lisent : un changement de seuil ne touche que ce fichier.

## Ce que vous saurez faire

- Noter une application sur les données, les flux vers le SI, les
  utilisateurs et la criticité métier, d'après ce qu'elle fait et non
  d'après ce qu'en dit son demandeur.
- Appliquer la règle « le critère le plus élevé l'emporte », même à une
  équipe de trois personnes.
- Rejeter une classe sous-évaluée sans en débattre.
- Relier chaque classe à ses contrôles, son approbation et sa durée
  d'autorisation.
