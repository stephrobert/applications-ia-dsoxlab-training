# Reprendre une session de code interrompue à partir de Git, pas de la mémoire

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**, parcours « Vibe coder avec méthode ». Une session de code
sur le portail-achats s'est arrêtée au milieu d'une tranche. Elle a laissé
des commits, du travail non commité et un journal d'avancement qui en dit
plus que le dépôt. Vous reprenez à partir de ce que Git contient vraiment :
vous triez le travail non commité, terminez la tranche sans toucher à la
spécification ni aux tests des critères déjà faits, et laissez un journal
auquel la session suivante peut se fier.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus, pytest, Git. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 40 minutes |
| Leçon associée | [Workflow agentique](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/workflow-agentique/) |
| Suivant | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-reprise-session
cd labs/vc-reprise-session/challenge/work/portail-achats
git status
git log --oneline
pytest -v
dsoxlab check vc-reprise-session
```

## Ce que vous saurez faire

- Reconstituer l'état d'un projet à partir de `git log`, `git status`,
  `git diff` et de la suite de tests, et repérer où un journal d'avancement
  se trompe.
- Décider, fichier par fichier, du travail non commité à garder et de celui
  à écarter, et consigner cette décision.
- Terminer une tranche par-dessus l'historique existant, sans le réécrire et
  sans affaiblir un test pour obtenir une suite verte.
- Laisser un journal d'avancement qui donne à chaque critère son état et le
  commit qui l'a fait, ainsi que la prochaine action.

## Ce qui le distingue de `vc-specification-agent`

Dans `vc-specification-agent`, vous partez d'une demande en prose et écrivez
la spécification et ses critères. Ici, ils existent déjà : une session s'est
arrêtée au milieu d'une tranche, et c'est la reprise que les contrôles
notent.
