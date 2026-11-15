# Le contexte d'un agent : ce qu'il charge, et ce qu'il utilise

## À lire d'abord : ce qui est simulé

L'agent de ce lab est **un script Python, pas Claude Code**. Il n'appelle
aucun service d'IA. Il construit son contexte à partir des fichiers du
projet comme Claude Code le décrit, pour une **partie** du comportement réel,
puis fait une tâche avec ce qu'il a chargé :

| Quoi | Ce que fait l'agent simulé | Ce qu'il ne fait pas |
|---|---|---|
| `CLAUDE.md` à la racine | le charge au démarrage | fichiers utilisateur, administrés et des répertoires parents, `CLAUDE.local.md` |
| imports `@chemin` | charge le fichier importé au démarrage, jusqu'à 5 niveaux ; ses lignes comptent dans le contexte de démarrage | `@~/...`, chemins hors du projet |
| `AGENTS.md` | ne le charge que si `CLAUDE.md` l'importe, ou s'il n'existe aucun `CLAUDE.md` | |
| `.claude/rules/*.md` sans `paths` | la charge au démarrage | imports dans une règle |
| `.claude/rules/*.md` avec `paths` | la charge quand la tâche touche un fichier qui correspond | |
| `CLAUDE.md` dans un sous-répertoire | le charge quand la tâche touche un fichier en dessous | |
| un chemin écrit sans `@` | note le document comme cité, ne le lit jamais | lire un document à la demande |
| la tâche | écrit des montants en Decimal seulement si un fichier chargé mentionne `Decimal`, puis lance la commande de test trouvée | tout ce qu'un vrai agent décide seul |

Un score complet prouve donc que vos fichiers disent ce qu'il faut **à ce
simulateur**. Il ne prouve pas comment un vrai Claude Code les charge.
L'en-tête de `agent/agent.py` liste chaque règle qu'il applique. Deux points
de format viennent de la documentation de Claude Code et n'ont pas été
vérifiés sur toutes les versions : le frontmatter `paths` d'une règle, et les
5 niveaux d'imports. Vérifiez-les dans la documentation de la version que
vous utilisez.

## Situation

L'équipe du **portail-achats** a tout donné à son agent de code, dans un
seul `CLAUDE.md` : la description, toutes les conventions de tous les
modules, prévus ou non, le glossaire, les incidents, une commande de test
recopiée d'un autre projet, et, par `@docs/erp-history.md`, l'historique de
l'ancien ERP, plus de 3 000 lignes. Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `CLAUDE.md` | la configuration « tout dans CLAUDE.md » |
| `src/commandes/`, `src/rapports/`, `tests/`, `pytest.ini` | le projet |
| `docs/architecture.md` | l'architecture, en 14 lignes |
| `docs/erp-history.md` | l'historique de l'ERP, pour les audits seulement |
| `agent/agent.py` | l'agent simulé |
| `agent/task.json` | sa tâche : une remise de fidélité dans `src/commandes/discount.py` |
| `agent/budget.json` | le budget du contexte de démarrage : 200 lignes |

Les 200 lignes viennent du conseil de la documentation de Claude Code :
garder un `CLAUDE.md` sous 200 lignes. Un import ne réduit pas le contexte :
les lignes importées sont chargées au démarrage elles aussi, donc elles
comptent.

## Mission

1. **Lancez l'agent sur la configuration telle quelle**, depuis
   `challenge/work` : `python3 agent/agent.py`. Lisez ce qu'il a chargé,
   combien de lignes, et ce qu'a donné sa commande de test. Gardez ce journal
   pour comparer : `cp agent/journal.json agent/journal-avant.json`.
2. **Corrigez la commande de test.** La commande écrite dans `CLAUDE.md`
   doit lancer toute la suite de tests de ce projet et sortir en 0. Gardez la
   forme `- Tests: `la commande`` : c'est ainsi que l'agent la trouve.
3. **Tenez le gros document hors du contexte.** `docs/erp-history.md` reste
   à sa place, inchangé. Citez-le par son chemin, sans `@`, avec une phrase
   qui dit quand le lire.
4. **Ciblez la règle des montants.** La règle « tout montant est un
   Decimal » ne concerne que `src/commandes/`. Elle doit se charger quand
   l'agent travaille sur un fichier de ce dossier, et pas pour les autres
   tâches. Faites de même pour les règles des rapports si vous le souhaitez.
5. **Faites tenir le contexte de démarrage dans le budget** : `CLAUDE.md` et
   tout ce qu'il importe, 200 lignes au plus. Gardez ce qui aide l'agent sur
   ce dépôt : ce qu'est le projet, son architecture, les commandes qui
   fonctionnent, les conventions qui valent partout.
6. **Relancez l'agent** après votre dernière modification, et comparez son
   journal au premier : ce qui est chargé au démarrage, ce qui est chargé
   pour la tâche, ce qui est seulement cité.

## Repères

Le frontmatter d'une règle qui ne vaut que pour certains fichiers :

```markdown
---
paths:
  - "src/api/**"
---

# Règles de l'API
...
```

- `*` reste dans un répertoire, `**` traverse les répertoires.
- La tâche lance `python3 -m pytest`. Si votre `python3` répond
  `No module named pytest`, installez pytest pour lui ; le contrôle lance
  votre commande avec un Python qui a pytest.
- Le journal dit pourquoi chaque fichier a été chargé. Les noms des causes
  (`session_start`, `include`, `path_glob_match`, `nested_traversal`) sont
  ceux des matchers de l'événement de hook `InstructionsLoaded` de Claude
  Code.

## Avec un vrai Claude Code

Ce lab ne lance pas de vrai agent. Pour voir la même chose avec un vrai
Claude Code, deux pistes, que ce lab ne couvre pas : un hook sur l'événement
`InstructionsLoaded` se déclenche quand un `CLAUDE.md` ou un fichier
`.claude/rules/*.md` est chargé, avec les matchers ci-dessus (il ne se
déclenche pas pour un `AGENTS.md` lu nativement) ; et la commande
`/context all` liste les fichiers chargés.

## Contrôle

```bash
dsoxlab check vc-contexte-agent
```

Quatre contrôles. Chacun relance l'agent du lab sur une copie de votre
projet : modifier `agent/agent.py`, `agent/task.json` ou `agent/budget.json`
ne change rien. Ils donnent aussi à l'agent une tâche sur `src/rapports/`,
lancent eux-mêmes votre commande de test, avec un test en échec ajouté, et
comparent votre `agent/journal.json` à ce que l'agent charge maintenant.
