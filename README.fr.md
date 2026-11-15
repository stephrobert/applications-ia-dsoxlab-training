# Sécuriser et gouverner les applications générées par IA : les labs vérifiables

**Langue :** [English](./README.md) · [Français](./README.fr.md)

[![CI](https://github.com/stephrobert/applications-ia-dsoxlab-training/actions/workflows/ci.yml/badge.svg)](https://github.com/stephrobert/applications-ia-dsoxlab-training/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/stephrobert/applications-ia-dsoxlab-training?label=OpenSSF%20Scorecard)](https://securityscorecards.dev/viewer/?uri=github.com/stephrobert/applications-ia-dsoxlab-training)
[![Conformité Plumber](https://score.getplumber.io/github.com/stephrobert/applications-ia-dsoxlab-training.svg)](https://score.getplumber.io/github.com/stephrobert/applications-ia-dsoxlab-training)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)
[![Licence : CC BY 4.0](https://img.shields.io/badge/Licence-CC%20BY%204.0-lightgrey.svg)](./LICENSE)

Catalogue de **labs vérifiables** de la formation « Sécuriser et gouverner les
applications générées par IA » du blog de Stéphane Robert, joué par la CLI
[dsoxlab](https://github.com/stephrobert/dsoxlab). Il s'adresse aux RSSI, DSI et
responsables qui décident d'accueillir une application créée avec l'IA, aux
ingénieurs qui la font tourner, et aux développeurs qui vibe codent et veulent
le faire avec méthode. Page de départ, en attendant les leçons :
[vibe coding](https://www.stephane-robert.info/docs/developper/vibe-coding/).

## Ce que c'est

À la fin du niveau 1, l'apprenant sait classer une application selon ses
données, ses flux, ses utilisateurs et sa criticité, et lui appliquer la
politique de sa classe. Il sait aussi relire les changements d'un agent face à
une spécification et refuser celui qui neutralise un test, et vérifier les
dépendances qu'un agent propose avant de les installer.

**Aucun lab n'appelle un vrai service d'IA ni n'exige de clé d'API.** L'agent et
ses propositions sont des fichiers fournis, déterministes : le même lab rend le
même résultat sur tous les postes, sans compte ni réseau.

## Prérequis

Les versions mesurées sont épinglées dans [`mise.toml`](./mise.toml).

- **Python 3.11+ et [`uv`](https://docs.astral.sh/uv/)**
- **`git`**
- **`dsoxlab`**, le moteur, installé en outil autonome (voir plus bas).

Le niveau 1 n'a **aucun lab `vm`** : `dsoxlab provision` n'y est jamais appelé,
et aucun accès réseau n'est demandé (le registre de paquets de
`vc-paquet-inexistant` est un répertoire local).

`dsoxlab doctor` dit ce dont ce dépôt a besoin et ce dont il n'a pas besoin, et
distingue un contrôle qui a échoué d'un contrôle qu'il n'a pas pu mesurer.

## Installation

`dsoxlab` est publié sur [PyPI](https://pypi.org/project/dsoxlab/).
Installe-le en outil autonome, pour qu'il reste hors de ce dépôt :

```bash
# 1. La CLI dsoxlab (outil externe, hors de ce dépôt)
uv tool install dsoxlab

# 2. Ce catalogue de labs
git clone <ce dépôt>
cd applications-ia-dsoxlab-training

# 3. Vérifier que le contrat est valide
dsoxlab validate-structure
```

### Votre premier lab, en cinq minutes

```bash
export LAB_HOME=$PWD
dsoxlab list-labs                # le catalogue, dans l'ordre pédagogique
dsoxlab run       <id>           # poser l'état de départ
dsoxlab challenge <id>           # lire la mission
dsoxlab check     <id>           # lancer les tests, enregistrer le score
```

C'est `run` qui prépare le lab. Un `check` joué sur un lab jamais démarré ne
mesure rien, et le dit au lieu d'enregistrer un 0.

### Garder à jour

```bash
uv tool upgrade dsoxlab        # le moteur, publié sur PyPI
git -C <ce dépôt> pull         # le catalogue
```

Le moteur et le catalogue avancent indépendamment : un nouveau `dsoxlab` ne
demande jamais de recloner les labs, et de nouveaux labs ne demandent jamais de
mettre l'outil à jour, tant que la version du contrat correspond.

## Comment ça marche

### Le moteur, documenté là où il vit

Ce catalogue se joue avec `dsoxlab`, qui documente lui-même son contrat et ses
commandes. Ce README ne les répète pas, pour ne pas dériver quand le moteur
change (issue dsoxlab #201) :

- le contrat : `meta.yml`, `lab.yaml`, `lab.<langue>.yaml`, les runtimes et
  leurs champs : [contrat](https://github.com/stephrobert/dsoxlab/blob/main/docs/contract-v1.fr.md) ;
- les commandes et la vie d'un lab, de `run` à `check` :
  [commandes](https://github.com/stephrobert/dsoxlab/blob/main/docs/commands.fr.md) et [jouer un lab](https://github.com/stephrobert/dsoxlab/blob/main/docs/learner.fr.md) ;
- écrire un lab, et ce que contrôle `validate-structure` :
  [guide de l'auteur](https://github.com/stephrobert/dsoxlab/blob/main/docs/catalog-author.fr.md).

### Les runtimes

Le niveau 1 n'emploie que le runtime `shell`.

| Runtime | Ce que le lab demande |
|---|---|
| `shell` | un terminal, Python 3.11 ou plus récent et `git` ; rien d'autre |

### Le modèle de validation

La validation **prouve l'état, elle ne fait pas confiance à l'apprenant**.
Chaque lab porte des tests `pytest` sous `challenge/tests/` qui lisent ce que
le système contient, jamais ce qu'un fichier contient ni quelles commandes ont
été tapées.

Et un lab est prouvé **dans les deux sens** : les tests doivent échouer avant
le travail et passer après. Un test vert avant le travail n'est pas un test,
c'est une hypothèse sur le setup.

Les solutions de référence vivent dans `labs/<id>/solution/` et sont
**chiffrées** (ansible-vault). `scripts/valider-labs.py` les déchiffre au moment
de les poser dans le répertoire de travail, et inscrit le verdict de chaque lab
dans `validation-labs.json`.

### Score, indices, avancement

`check` enregistre un score (tests réussis sur total, moins le coût des indices
révélés). Les indices sont **en base64** dans `challenge/hints.yaml`, pour qu'on
n'y accède pas en ouvrant le fichier, et leur coût croît avec leur précision.
L'historique vit dans une base SQLite **locale à ce dépôt**.

Une exécution qui n'a rien mesuré n'est ni une réussite ni un échec : si tous
les tests collectés skippent, `check` n'enregistre aucune note et dit pourquoi.
Un 0 accuserait le lab de ce qui manque au poste.

## Catalogue

### Niveau 1 : classer, cadrer et vibe coder avec méthode

| Lab | Ce qu'il fait faire | Durée |
|---|---|---|
| [`vc-classifier-applications`](labs/vc-classifier-applications/) | Classer quatre applications créées avec l'IA et appliquer la politique de leur classe | 45 min |
| [`vc-contrat-applicatif`](labs/vc-contrat-applicatif/) | Rédiger la fiche applicative d'une application créée avec l'IA sans laisser le dépôt candidat s'autoriser | 45 min |
| [`vc-boucle-methode`](labs/vc-boucle-methode/) | Relire les changements d'un agent face à une spécification et à ses tests | 40 min |
| [`vc-specification-agent`](labs/vc-specification-agent/) | Transformer une demande métier en critères vérifiables et la faire implémenter par un agent | 50 min |
| [`vc-reprise-session`](labs/vc-reprise-session/) | Reprendre une session de code interrompue à partir de Git, pas de la mémoire | 40 min |
| [`vc-paquet-inexistant`](labs/vc-paquet-inexistant/) | Vérifier les dépendances qu'un agent propose avant de les installer | 30 min |
| [`vc-contexte-agent`](labs/vc-contexte-agent/) | Concevoir le contexte d'un agent de code et vérifier ce qu'il a vraiment chargé | 45 min |
| [`vc-harness-agent-ia`](labs/vc-harness-agent-ia/) | Poser un harness minimal pour un agent de code et l'éprouver sur un agent simulé | 60 min |
| [`vc-epreuve-classification`](labs/vc-epreuve-classification/) | Épreuve du niveau 1 : qualifier une application non documentée | 90 min |

### Claude Code : un mécanisme par lab

| Lab | Ce qu'il fait faire | Durée |
|---|---|---|
| [`cc-hook-qui-echoue`](labs/cc-hook-qui-echoue/) | Éprouver un hook qui réussit, bloque et plante | 45 min |
| [`cc-serveur-mcp-non-approuve`](labs/cc-serveur-mcp-non-approuve/) | Refuser un serveur MCP qu'un dépôt déclare sans approbation | 30 min |
| [`cc-regles-allow-ask-deny`](labs/cc-regles-allow-ask-deny/) | Faire appliquer des règles allow, ask et deny, au niveau projet et administré | 40 min |
| [`cc-subagent-relecteur-borne`](labs/cc-subagent-relecteur-borne/) | Limiter un subagent relecteur aux outils qui lisent | 30 min |
| [`cc-skill-de-validation`](labs/cc-skill-de-validation/) | Construire une skill de validation réutilisable qui lance ses propres scripts | 40 min |

## Contribuer

Lis [`CONTRIBUTING.fr.md`](./CONTRIBUTING.fr.md). En bref : un lab est prouvé
**dans les deux sens** avant d'être fusionné, `dsoxlab validate-structure` est
vert, et l'énoncé existe en anglais et en français.

Tout ce qui s'affiche est bilingue. Un document traduit d'un seul côté est
signalé par le validateur, et non laissé à la bonne volonté.

## Licence

Voir [`LICENSE`](./LICENSE).
