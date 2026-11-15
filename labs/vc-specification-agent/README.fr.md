# Transformer une demande métier en critères vérifiables et la faire implémenter par un agent

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**, parcours « Vibe coder avec méthode ». La responsable des
achats demande, en prose, une règle de validation dans le portail-achats.
Vous écrivez les exigences, les critères d'acceptation et les tests, puis un
plan qui dit quels fichiers un agent de code peut modifier. Un agent simulé
implémente le changement et tente de contourner les règles : votre
spécification, vos tests et le reste du projet doivent en sortir inchangés.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus, pytest. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 50 minutes |
| Leçon associée | [Applications générées par IA](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/) |
| Suivant | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-specification-agent
cd labs/vc-specification-agent/challenge/work
pytest -v
python3 agent/agent.py --dry-run
dsoxlab check vc-specification-agent
```

## Ce que vous saurez faire

- Trouver dans une demande en prose les règles qu'elle énonce, et celle
  qu'elle ne fait que sous-entendre.
- Écrire chaque règle en exigence, et chaque exigence en critères reliés à
  des tests.
- Écrire des tests qui échouent avant l'implémentation et qui attrapent une
  implémentation cassée.
- Borner ce qu'un agent peut modifier par un plan, et vérifier par ses
  empreintes qu'il n'a touché ni à la spécification ni aux tests.

## Ce qui le distingue de `vc-boucle-methode`

Dans `vc-boucle-methode`, la spécification est donnée : vous reliez des
critères existants à des tests et refusez un mauvais patch. Ici, vous partez
de la demande et écrivez vous-même les critères, le plan et la liste des
fichiers autorisés. C'est cette traduction que les contrôles notent.
