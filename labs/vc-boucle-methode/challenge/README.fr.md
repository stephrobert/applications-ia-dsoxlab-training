# Challenge : Deux changements de l'agent, une revue

## Situation

Le **portail-achats** est le portail d'achats d'une entreprise fictive. Il
a été généré avec un agent de code, et son module de commandes est
maintenant dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `SPEC.md` | la spécification : les exigences R1 à R3, et les critères d'acceptation reliés à des tests |
| `orders.py` | le module des commandes |
| `tests/test_orders.py` | la suite de tests |
| `agent/proposal-1.patch`, `agent/proposal-2.patch` | deux changements que l'agent propose |
| `decisions.yaml` | le journal de revue, vide |

L'équipe a demandé à l'agent d'implémenter **R3** (validation au-dessus de
5 000 EUR). Il revient avec deux patchs. Rien n'est appliqué. L'agent est
simulé : ses patchs sont des fichiers, rien n'appelle un service d'IA.

Un agent de code optimise ce que vous mesurez. Si vous ne vérifiez que
« la suite est verte », c'est ce que vous obtiendrez, par n'importe quel
moyen. Votre travail : relire ce que fait vraiment chaque patch, garder ce
qui respecte la spécification, et laisser une trace de chaque décision.

## Mission

1. **Lancez la suite** avant de toucher à quoi que ce soit, puis lisez
   chaque patch.
2. **Appliquez le changement conforme à la spécification**, et lui seul.
   Toute la suite du projet doit passer ensuite.
3. **Refusez l'autre** : ne l'appliquez pas, et consignez le refus dans
   `decisions.yaml`. La raison doit dire précisément ce que vous refusez,
   assez pour que l'auteur du patch le retrouve (quel fichier, quel test,
   quelle ligne).
4. **Rendez R3 vérifiable** : ajoutez à `SPEC.md` un critère d'acceptation
   pour R3, sous la même forme que les autres (`- AC-n [R3]: ...` et
   l'identifiant pytest du test entre accents graves). Le test cité doit
   exister, réussir, et échouer dès que R3 est cassée.

## Pistes

- Depuis `challenge/work` : `pytest` lance la suite (`pytest -v` nomme
  chaque test, `pytest -rs` dit pourquoi un test a été ignoré).
- `patch -p1 --dry-run < agent/proposal-1.patch` vérifie un patch sans
  l'appliquer ; sans `--dry-run`, il l'applique. `git apply` marche aussi.
- Une suite verte dit que rien n'a échoué. Elle ne dit pas que chaque test
  a tourné.

## Vérification

```bash
dsoxlab check vc-boucle-methode
```

Trois contrôles. Ils relancent eux-mêmes pytest sur votre projet, chargent
`orders.py` pour mesurer son comportement, et relisent `SPEC.md` et
`decisions.yaml`.
