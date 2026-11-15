# applications-ia-dsoxlab-training

**Langue :** [English](./README.md) · [Français](./README.fr.md)

À REMPLIR : un paragraphe. Ce que ce catalogue apprend, et à qui.

## Ce que c'est

À REMPLIR : ce qu'un apprenant saura faire à la fin et ne savait pas faire au
début. Dis-le en capacité, pas en liste de sujets couverts.

Dis ici pourquoi les labs sont dans cet ordre, si l'ordre compte.

## Prérequis

À REMPLIR, et sois exact : un prérequis absent de cette liste coûte une heure
de recherche à l'apprenant.

- **Python 3.11+ et [`uv`](https://docs.astral.sh/uv/)**
- **`git`**
- **`dsoxlab`**, le moteur, installé en outil autonome (voir plus bas).
- À REMPLIR : les outils dont les labs ont besoin sur le poste.

À REMPLIR : si ce catalogue a des labs `vm`, nomme l'hyperviseur, la RAM et le
disque que les machines demandent. S'il n'en a pas, dis-le : `dsoxlab provision`
n'est alors jamais appelé, et le dire épargne une question au lecteur.

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

À REMPLIR : une ligne par runtime réellement employé par ce catalogue, et ce
qu'il demande au poste.

| Runtime | Ce que le lab demande |
|---|---|
| `shell` | un terminal, et À REMPLIR |

### Le modèle de validation

La validation **prouve l'état, elle ne fait pas confiance à l'apprenant**.
Chaque lab porte des tests `pytest` sous `challenge/tests/` qui lisent ce que
le système contient, jamais ce qu'un fichier contient ni quelles commandes ont
été tapées.

Et un lab est prouvé **dans les deux sens** : les tests doivent échouer avant
le travail et passer après. Un test vert avant le travail n'est pas un test,
c'est une hypothèse sur le setup.

À REMPLIR : où vivent les solutions de référence, et si elles sont chiffrées.
Une solution livrée en clair gâche le lab, et git la garde pour toujours.

### Score, indices, avancement

`check` enregistre un score (tests réussis sur total, moins le coût des indices
révélés). Les indices sont **en base64** dans `challenge/hints.yaml`, pour qu'on
n'y accède pas en ouvrant le fichier, et leur coût croît avec leur précision.
L'historique vit dans une base SQLite **locale à ce dépôt**.

Une exécution qui n'a rien mesuré n'est ni une réussite ni un échec : si tous
les tests collectés skippent, `check` n'enregistre aucune note et dit pourquoi.
Un 0 accuserait le lab de ce qui manque au poste.

## Catalogue

À REMPLIR : une sous-section par section du `meta.yml`, avec ses labs.

## Contribuer

Lis [`CONTRIBUTING.fr.md`](./CONTRIBUTING.fr.md). En bref : un lab est prouvé
**dans les deux sens** avant d'être fusionné, `dsoxlab validate-structure` est
vert, et l'énoncé existe en anglais et en français.

Tout ce qui s'affiche est bilingue. Un document traduit d'un seul côté est
signalé par le validateur, et non laissé à la bonne volonté.

## Licence

Voir [`LICENSE`](./LICENSE).
