# Une skill de validation que Claude Code n'a jamais chargée

## À lire d'abord : ce qui est simulé

Le banc de ce lab est **un script Python, pas Claude Code**. Il n'appelle
aucun service d'IA et n'a pas besoin du réseau. Il lit une skill du projet,
contrôle une **partie** de son format, puis **exécute** les commandes que ses
étapes désignent :

| Quoi | Ce que le banc applique | Ce qu'il n'applique pas |
|---|---|---|
| le fichier | `.claude/skills/<skill>/SKILL.md`, avec ce nom de fichier exact | les niveaux utilisateur et plugin, le menu `/nom` |
| le frontmatter | `name` (minuscules, chiffres, tirets, le nom du dossier), `description` (non vide), `disable-model-invocation`, `allowed-tools` | `paths`, `user-invocable`, `argument-hint`, `$ARGUMENTS`, le moment où Claude décide de charger une skill |
| une étape | une ligne numérotée du corps qui contient un bout de code entre accents graves : le premier est la commande | le résumé que Claude écrirait après les étapes |
| `allowed-tools` | `Bash(motif)`, une étoile valant n'importe quel texte. Une étape qu'il ne couvre pas **n'est pas exécutée** : Claude Code vous demanderait d'abord, et le banc tourne sans surveillance | les règles de permission des fichiers de réglages |
| exécuter une étape | depuis la racine du projet, sans shell. Un programme donné par un chemin doit exister et être exécutable. Toutes les étapes s'exécutent, même après un échec | |

Un score complet prouve donc que votre skill dit la bonne chose **à ce
banc**, et que ses scripts tournent vraiment. Il ne prouve pas comment une
version donnée de Claude Code la charge. L'en-tête de `bench/skill_bench.py`
liste toutes les règles qu'il applique.

## Situation

Le dépôt **portail-achats** valide son code par trois scripts avant chaque
pull request : style, tests unitaires, secrets dans le code. La CI les lance
directement, comme des programmes. `docs/validation.md` donne leur ordre et
leurs arguments.

Quelqu'un a commencé une skill `/valider` pour que Claude Code joue la même
procédure à la demande. Claude Code ne l'a jamais chargée, et personne ne
l'a jouée jusqu'au bout. Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `.claude/skills/valider/skill.md` | la première version de la skill |
| `docs/validation.md` | la procédure, et ce que l'équipe a décidé pour la skill |
| `tools/validation/` | les trois scripts que lance la CI |
| `src/`, `tests/` | le code et ses tests unitaires |
| `bench/skill_bench.py` | le banc |

## Mission

1. **Lancez le banc tel quel**, depuis `challenge/work` :
   `python3 bench/skill_bench.py`. Lisez pourquoi il ne voit pas de skill.
2. **Rendez SKILL.md valide** : le nom du fichier, le `name`, une
   `description` qui dit quand utiliser la skill, et un lancement à la
   demande seulement.
3. **Rendez la skill autonome** : copiez les trois scripts, sans les
   modifier, dans `.claude/skills/valider/scripts/`, et rendez-les
   exécutables.
4. **Appelez-les directement** dans les étapes, dans l'ordre et avec les
   arguments de `docs/validation.md`, depuis la racine du projet.
5. **Pré-approuvez exactement ces trois appels** dans `allowed-tools`, et
   rien d'autre.
6. **Relancez le banc** après votre dernière modification. Son journal,
   `bench/journal.json`, doit montrer les trois étapes réussies sur vos
   fichiers finaux.

## Repères

- Une skill est un dossier : `.claude/skills/<nom>/SKILL.md`. Le fichier
  s'appelle `SKILL.md`, en capitales. Le `name` s'écrit en minuscules et vaut
  le nom du dossier.
- `disable-model-invocation: true` réserve une skill à `/nom` : Claude ne la
  lance pas de lui-même.
- `allowed-tools` prend des entrées séparées par des espaces :
  `Bash(chemin/vers/script.py arg)`. Une étoile vaut n'importe quel texte :
  une étoile sur un dossier approuve donc tout script qu'on y ajoutera plus
  tard.
- Un script appelé directement (`chemin/vers/script.py`) a besoin de sa
  première ligne (`#!/usr/bin/env python3`, déjà présente) et du bit
  d'exécution (`chmod +x`). Appelé par `python3 chemin/vers/script.py`, il
  n'a besoin ni de l'un ni de l'autre, et la CI ne l'appelle pas ainsi.
- `cp` copie un fichier sans son bit d'exécution si la source n'en a pas.
- Le banc exécute les étapes pour de vrai : un script qui affiche « ok »
  sans rien vérifier est attrapé.

## Vérifier

```bash
dsoxlab check cc-skill-de-validation
```

Cinq contrôles. Chacun relance le banc du lab sur une copie de votre
projet : modifier `bench/skill_bench.py` ne change rien. Un contrôle joue
votre skill sur des copies du projet où un défaut a été **injecté** (un
secret dans le code, un test qui échoue, une ligne trop longue), et attend
que chaque défaut fasse échouer la bonne étape. Un autre essaie des
commandes qu'aucune étape n'utilise, et attend qu'`allowed-tools` n'en
approuve aucune.
