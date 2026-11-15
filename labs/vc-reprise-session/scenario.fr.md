# Reprendre une tranche qu'une session a laissée à moitié faite

## Situation

Hier, un agent de code a travaillé sur le **portail-achats**, le portail
d'achats d'une entreprise fictive. Sa tâche : le cycle de vie des commandes
décrit dans `SPEC.md`, une tranche à la fois. Il a terminé les tranches S1
et S2, commencé S3 (critères AC-4 et AC-5), et la session s'est arrêtée :
le contexte était plein.

Aujourd'hui commence une nouvelle session, la vôtre. Elle ne se souvient de
rien. Il reste le dépôt : les commits, les fichiers que personne n'a
commités, et `PROGRESS.md`, le journal que la session précédente tenait pour
la suivante. Ce journal a été écrit par la session qui s'est arrêtée.
Vérifiez-le avec Git avant de le croire.

Tout est dans `challenge/work` :

| Chemin | Contenu |
|---|---|
| `portail-achats/` | le projet, un dépôt Git : travaillez depuis ce répertoire |
| `portail-achats/SPEC.md` | les exigences R1 à R4, les critères AC-1 à AC-7 et les tranches |
| `portail-achats/PROGRESS.md` | le journal de la session précédente |
| `portail-achats/orders.py` | le module, implémenté critère par critère |
| `portail-achats/tests/` | un fichier de tests par tranche |
| `.git-portail-achats/` | la base Git du projet. `portail-achats/.git` est un fichier qui la désigne. N'y touchez pas et utilisez `git` depuis `portail-achats/` |

Les fichiers du projet sont en anglais, comme le code.

## Mission

1. **Reconstituez l'état réel.** `git log --oneline`, `git status`, puis
   `git diff` fichier par fichier, puis `pytest -v`. Notez ce qui est
   commité, ce qui ne l'est pas, et ce qui passe. Comparez avec
   `PROGRESS.md`.
2. **Triez le travail non commité**, fichier par fichier : gardez-le (il
   finit dans un commit) ou écartez-le (`git restore <fichier>` pour un
   fichier modifié). Un fichier gardé peut être corrigé avant d'être
   commité.
3. **Ne modifiez jamais `SPEC.md` ni les tests des critères déjà faits**
   (AC-1 à AC-3). Si l'un de ces tests échoue, c'est le code qui a tort, pas
   le test.
4. **Terminez la tranche S3** : AC-4 et AC-5 tels que `SPEC.md` les
   formule, chacun avec le test que `SPEC.md` cite, sous ce nom exact. Toute
   la suite doit passer.
5. **Commitez par-dessus l'historique existant.** Ajoutez des commits ; ne
   faites ni amend, ni reset, ni rebase des commits déjà présents.
6. **Mettez `PROGRESS.md` à jour** pour la session suivante, puis
   commitez-le :
   - chaque critère du tableau reçoit son état réel (`done`, `in progress`,
     `to do`) et, s'il est fait, le hash court du premier commit où il
     passe ;
   - la ligne `Next action:` nomme un critère qui n'est pas encore fait ;
   - dans le journal de session, une ligne par fichier non commité trouvé au
     départ, avec votre décision et sa raison :
     `- orders.py: kept ...` ou `- tests/test_x.py: discarded ...`.

   À la fin, `git status` n'affiche rien.

## Repères

- Git a besoin d'une identité pour commiter. Si `git commit` en réclame
  une : `git config user.name "Votre nom"` et
  `git config user.email "vous@example.org"`, depuis `portail-achats/`.
- `git diff <fichier>` montre ce qui a changé dans un fichier ; `git status`
  liste les fichiers nouveaux que Git ne suit pas encore.
- Un commit ne peut pas contenir son propre hash. Commitez d'abord le code,
  puis `PROGRESS.md` dans un second commit qui cite le premier.
- Le tableau et les lignes de `PROGRESS.md` peuvent s'écrire en français :
  `fait`, `en cours`, `à faire`, `Prochaine action :`, `gardé`, `écarté`.

## Vérification

```bash
dsoxlab check vc-reprise-session
```

Quatre contrôles. Ils tirent la vérité du dépôt de départ, qu'ils
reconstruisent à partir des fixtures du lab, jamais de vos fichiers. Ils
jouent vos tests et des tests de référence sur une copie de votre dernier
commit, puis sur des versions d'`orders.py` qui cassent chacune un critère :
le test que `SPEC.md` cite pour ce critère doit échouer. Ils lisent
l'historique et `git status`, comparent les empreintes SHA-256 de `SPEC.md`
et des tests faits avec celles du départ, et confrontent chaque ligne de
`PROGRESS.md` aux commits.
