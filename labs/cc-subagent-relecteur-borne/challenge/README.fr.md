# Challenge : Un subagent relecteur qui a corrigé le code lui-même

## À lire d'abord : ce qui est simulé

Le banc de ce lab est **un script Python, pas Claude Code**. Il ne lance
aucun agent, n'appelle aucun service d'IA et n'a pas besoin du réseau. Il lit
les fichiers de subagent du projet, rejoue une liste fixe d'appels d'outils,
et applique une **partie** du format réel :

| Quoi | Ce que le banc applique | Ce qu'il n'applique pas |
|---|---|---|
| `.claude/agents/*.md` | le frontmatter entre deux lignes `---` : `name`, `description`, `model`, `tools`, `disallowedTools`, en `clé: valeur` ou en liste de lignes `- élément` | les autres champs du frontmatter, les niveaux utilisateur et plugin, le choix du subagent que fait Claude Code |
| `tools` | absent : le subagent hérite de tous les outils de la session (`bench/session.json`). Présent : ces outils et rien d'autre. `Bash` seul autorise toute commande, `Bash(motif)` les commandes qui correspondent, une étoile valant n'importe quel texte | les règles du type `Read(chemin)` : le banc les liste comme inconnues, et elles n'accordent rien |
| une commande | en plusieurs morceaux (`&&`, `\|\|`, `;`, `\|`) : autorisée seulement si chaque morceau l'est. Avec une redirection ou une substitution : refusée | les règles de permission des fichiers de réglages, le mode de permission, les hooks |

Un score complet prouve donc que votre fichier de subagent dit la bonne chose
**à ce banc**, pas comment se comporte une version donnée de Claude Code.
L'en-tête de `bench/agent_bench.py` liste toutes les règles qu'il applique.

## Situation

Le dépôt **portail-achats** a deux subagents dans `.claude/agents/` :

- `relecteur` relit une branche avant une fusion et rend un rapport ;
- `correcteur` applique, sur demande, les corrections qu'un humain a listées.

Lors de la dernière revue, le relecteur est allé bien au-delà d'un rapport :
il a lancé le linter avec `--fix`, modifié le code, commité, poussé et fermé
le ticket du tracker. Ses instructions disent « You never modify a file ». Il
l'a fait quand même, parce que son fichier n'a **pas de champ `tools`** : il
hérite de tous les outils de la session. Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `.claude/agents/relecteur.md` | le relecteur, tel qu'il est aujourd'hui |
| `.claude/agents/correcteur.md` | le correcteur, qui garde ses outils |
| `docs/review-incident.md` | ce qu'a fait le relecteur, et ce que l'équipe a décidé |
| `src/orders.py` | le code relu |
| `bench/agent_bench.py` | le banc |
| `bench/session.json` | les outils de la session principale |
| `bench/review.json` | les appels que le relecteur a tentés pendant l'incident |

## Mission

1. **Lancez le banc tel quel**, depuis `challenge/work` :
   `python3 bench/agent_bench.py`. Tous les appels de l'incident atteignent
   un outil.
2. **Lisez `docs/review-incident.md`** : il dit ce dont une revue a besoin,
   et ce que le relecteur doit perdre.
3. **Donnez au relecteur un champ `tools` explicite** dans son frontmatter :
   les outils qui lisent le code, y cherchent, lisent l'état, l'historique et
   le diff git, et lisent le ticket du tracker. Rien qui modifie un fichier,
   lance une commande qui écrit, ou change le tracker.
4. **Ne changez rien d'autre** : le nom, la description, le modèle et les
   instructions du relecteur restent tels quels, et le subagent `correcteur`
   aussi.
5. **Relancez le banc** après votre dernière modification. Son journal,
   `bench/journal.json`, doit dire ce qu'il décide sur votre fichier final.

## Repères

- `tools` est une liste séparée par des virgules dans le frontmatter :
  `tools: Read, Grep, Glob`. Sans lui, le subagent reçoit tous les outils de
  la session, outils MCP compris, et tout outil ajouté plus tard.
- Un outil MCP s'appelle `mcp__<serveur>__<outil>`. Listez celui dont le
  relecteur a besoin par son nom complet.
- `Bash(git diff *)` autorise les commandes qui commencent par `git diff `.
  `Bash(git *)` autorise aussi `git commit`, `git push` et `git checkout --`.
  `Bash` seul autorise tout.
- N'écrivez pas les commandes exactes de l'incident : une revue lit le diff
  et l'historique sous plus d'une forme (`--stat`, `-p`...).
- Une commande en plusieurs morceaux n'est autorisée que si chaque morceau
  l'est : un motif qui commence comme `git diff` ne laisse pas passer
  `git diff && git push`.
- `disallowedTools` est une liste noire : il retire ce que vous nommez, et
  laisse hérité tout le reste, y compris ce que la session gagnera plus tard.

## Vérifier

```bash
dsoxlab check cc-subagent-relecteur-borne
```

Quatre contrôles. Chacun relance le banc du lab sur une copie de votre
projet : modifier `bench/agent_bench.py`, `bench/session.json` ou
`bench/review.json` ne change rien. Les contrôles rejouent **plus d'appels
que n'en montre `bench/review.json`** : d'autres commandes qui écrivent, des
commandes en plusieurs morceaux, et d'autres formes des lectures dont une
revue a besoin. Un contrôle compare votre `bench/journal.json` à ce que le
banc décide maintenant.
