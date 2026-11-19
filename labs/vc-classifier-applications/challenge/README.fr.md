# Challenge : Quatre demandes, une grille

## Situation

Quatre applications créées avec l'aide de l'IA demandent à être hébergées
sur la plateforme de l'entreprise. Chaque demande arrive avec la classe que
réclame son demandeur. C'est l'équipe plateforme qui classe, pas le
demandeur : une classe demandée est une demande, jamais une décision.

Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `demandes/*.md` | les quatre demandes, en anglais et en français |
| `grille.toml` | la grille de la formation : quatre critères notés de 0 à 3, la classe que donne chaque score, et ce qu'impose chaque classe |
| `classification.toml` | votre classification, à remplir |
| `classify.py` | calcule chaque classe à partir de vos critères et vérifie votre fichier (Python 3.11 ou plus, sans dépendance) |

La grille en une phrase : chaque critère (données, flux vers le SI,
utilisateurs, criticité métier) donne un score de 0 à 3, et **le critère le
plus élevé l'emporte**. Le score 0 donne C1, 1 donne C2, 2 donne C3, 3
donne C4. En cas de doute sur un critère, on retient le score supérieur.
Une classe peut toujours être relevée ; elle ne s'abaisse qu'avec une
décision humaine écrite, que ce lab n'a pas.

## Mission

Pour chacune des quatre applications, dans `classification.toml` :

1. **Lisez la demande** et donnez à chaque critère sa valeur, une clé de
   `grille.toml` (par exemple `donnees = "personnelles"`). Lisez ce que fait
   l'application, pas ce qu'en conclut le demandeur.
2. **Statuez sur la demande** : `decision_demande = "rejetee"` quand la
   classe demandée est sous ce que donne la grille, `"acceptee"` sinon.
   Laissez `classe_demandee` telle quelle : c'est la parole du demandeur.
3. **Retenez une classe** (`classe_retenue`).
4. **Appliquez la politique** de la classe retenue dans la table
   `[politique]` : les cinq champs de `[classes.Cn.impose]` de
   `grille.toml` (`deploiement_plateforme`, `controles`, `approbation`,
   `fiches_decision_signees`, `duree_autorisation_mois`). La durée est un
   maximum : tout nombre entier de mois de 1 jusqu'à lui convient, et 0
   pour une classe qui n'a pas d'autorisation.

## Pistes

- `python3 classify.py` affiche, pour chaque application, les classes
  demandée, calculée et retenue, et ce qui reste incohérent.
- Le script fait confiance à vos critères. Qu'ils correspondent à la
  demande, c'est votre part du travail, et le contrôle le vérifie.

## Vérification

```bash
dsoxlab check vc-classifier-applications
```

Trois contrôles. Ils relancent le `classify.py` d'origine sur votre
fichier, et comparent vos critères aux demandes.
