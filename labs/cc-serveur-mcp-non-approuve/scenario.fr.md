# Un serveur MCP que personne n'a approuvé, déclaré par le dépôt

## À lire d'abord : ce qui est simulé

Le banc de ce lab est **un script Python, pas Claude Code**. Il ne lance
aucun serveur MCP, n'appelle aucun service d'IA et n'a pas besoin du réseau.
Il lit deux fichiers du projet et applique une **partie seulement** de leur
format réel :

| Fichier | Ce que le banc applique | Ce qu'il n'applique pas |
|---|---|---|
| `.mcp.json`, `mcpServers` | tout serveur déclaré avec une `command` ou une `url` est candidat | le démarrage des serveurs : les outils que chacun exposerait viennent de `bench/tools.json`, une liste fixe |
| `.claude/settings.json`, `permissions` | les règles `mcp__` de `deny`, `ask` et `allow` : `mcp__serveur` (le serveur entier), `mcp__serveur__outil` (un outil), une étoile après un préfixe littéral, `mcp__*`. Une règle `mcp__` avec des parenthèses est ignorée. Un allow ne lève jamais un deny | les autres règles (`Read`, `Bash`...), les autres clés de réglages, les réglages utilisateur et administrés, `settings.local.json` |

Un serveur est **refusé** quand une règle deny couvre chacun de ses outils, y
compris un outil qu'il pourrait ajouter plus tard. Sinon, il est **chargé**.
Le banc ne simule pas l'invite d'approbation que Claude Code peut afficher
pour les serveurs d'un projet, ni aucun réglage lié à cette approbation. Ce
lab n'établit pas non plus si Claude Code lance encore le processus d'un
serveur dont tous les outils sont refusés. Un score complet prouve donc que
vos fichiers disent ce qu'il faut **à ce banc**, pas comment se comporte une
version donnée de Claude Code. L'en-tête de `bench/mcp_bench.py` liste chaque
règle qu'il applique.

## Situation

Le dépôt **portail-achats** est partagé par une équipe qui travaille avec
Claude Code. Son `.mcp.json` est commité : chaque clone charge les mêmes
serveurs. La revue de sécurité en a approuvé deux, listés dans
`docs/mcp-servers.md`.

Une contribution a été fusionnée hier : « Share snippets faster with the
agent ». Elle a modifié `.mcp.json`. Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `.mcp.json` | les serveurs MCP du projet, tels qu'ils sont après la fusion |
| `.claude/settings.json` | les permissions du projet : ce que l'équipe autorise, soumet à confirmation et refuse |
| `docs/mcp-servers.md` | les serveurs que la revue de sécurité a approuvés |
| `tools/` | des remplaçants des serveurs, jamais lancés |
| `bench/mcp_bench.py`, `bench/tools.json` | le banc et les outils que chaque serveur exposerait |

## Mission

1. **Lancez le banc tel quel**, depuis `challenge/work` :
   `python3 bench/mcp_bench.py`. Lisez quels serveurs sont chargés.
2. **Repérez le serveur que personne n'a approuvé** : comparez `.mcp.json`
   à `docs/mcp-servers.md`.
3. **Refusez-le** par une règle dans `permissions.deny` de
   `.claude/settings.json`. Ce fichier est partagé avec l'équipe, comme
   `.mcp.json`. La règle doit couvrir le serveur entier, pas un de ses
   outils : un outil que le serveur ajoute plus tard doit être refusé lui
   aussi.
4. **Assurez-vous qu'il reste refusé.** Retirer le serveur de `.mcp.json`
   est bien, mais ne suffit pas seul : la prochaine contribution peut le
   redéclarer. Le contrôle le redéclare et attend un refus.
5. **Gardez ce qui a été approuvé** : les serveurs `docs` et `tracker`, leur
   déclaration inchangée dans `.mcp.json`, et les permissions de leurs
   outils.
6. **Relancez le banc** après votre dernière modification. Son journal,
   `bench/journal.json`, doit dire ce qu'il décide sur vos fichiers finaux,
   et montrer le serveur non approuvé refusé par votre règle deny.

## Pistes

- Les outils MCP s'appellent `mcp__<serveur>__<outil>`. Une règle
  `mcp__<serveur>` couvre tous les outils de ce serveur ;
  `mcp__<serveur>__<outil>` en couvre un.
- Une étoile n'est acceptée qu'après un préfixe littéral :
  `mcp__github__get_*`. En `deny`, `mcp__*` couvre tous les outils MCP, ceux
  des serveurs approuvés compris.
- Une règle `mcp__` écrite avec des parenthèses, comme `mcp__serveur(*)`, est
  ignorée dans un fichier de réglages : elle ne refuse rien.
- Jamais de `mcp__*` dans `allow` : autorisez les outils un par un, par leur
  nom.
- Un deny l'emporte sur un allow, et il l'emporte aussi d'un niveau de
  réglages à l'autre (utilisateur, projet, administré). Ce banc ne lit que
  le niveau projet.
- La forme de `.mcp.json` :
  `{"mcpServers": {"<nom>": {"command": "...", "args": [...]}}}`.

## Vérification

```bash
dsoxlab check cc-serveur-mcp-non-approuve
```

Trois contrôles. Chacun relance le banc du lab sur une copie de votre
projet : modifier `bench/mcp_bench.py` ou `bench/tools.json` ne change rien.
L'un d'eux redéclare le serveur non approuvé dans `.mcp.json` avant de lancer
le banc, et un autre compare votre `bench/journal.json` à ce que décide le
banc maintenant.
