# Un harness pour l'agent, éprouvé sur un agent simulé

## À lire d'abord : ce qui est simulé

L'agent de ce lab est **un script Python, pas Claude Code**. Il n'appelle
aucun service d'IA. Il joue une liste d'actions fixe et applique à chacune
une **partie seulement** des formats réels :

| Format | Ce que l'agent simulé applique | Ce qu'il n'applique pas |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md` | charge AGENTS.md seul quand il n'y a pas de CLAUDE.md, et seulement par `@AGENTS.md` quand il y en a un ; consigne les fichiers, ne leur obéit jamais | tout ce qu'une instruction change au comportement d'un vrai agent |
| `.claude/settings.json`, `permissions` | `deny`, puis `ask`, puis `allow` : la première règle qui correspond décide, un allow ne lève jamais un deny. Règles sur `Read`, `Edit`, `Bash` et les outils MCP | les modes de permission, `settings.local.json`, les réglages utilisateur, le bac à sable |
| `.claude/settings.json`, `hooks.PreToolUse` | lance votre commande avant les règles de permission, avec l'appel en JSON sur l'entrée standard ; le code de sortie 2 bloque | la sortie JSON d'un hook, les autres événements de hook |
| `.mcp.json`, `mcpServers` | un appel à un serveur non déclaré est refusé | le démarrage des serveurs, leur approbation |

Une règle `ask` compte ici comme un refus : personne n'est là pour répondre.
Un score complet prouve donc que vos fichiers disent ce qu'il faut **à ce
simulateur**. Il ne prouve pas que Claude Code se comporte de la même façon :
cette preuve demande un vrai Claude Code, dans un lab distinct. L'en-tête de
`agent/agent.py` liste chaque règle que le simulateur applique.

## Situation

L'équipe ouvre un nouveau dépôt pour le module des commandes du
**portail-achats** et veut le confier à un agent de code. Rien n'encadre
encore l'agent : ni instructions, ni permissions, ni hook, ni liste de
serveurs MCP. Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `README.md`, `orders.py`, `tests/test_orders.py` | le projet |
| `secrets/erp.ini` | les paramètres de connexion à l'ERP (valeurs factices). L'application en a besoin, l'agent ne doit jamais les lire |
| `tools/docs_server.py` | le serveur MCP de documentation de l'équipe, le seul approuvé |
| `agent/agent.py` | l'agent simulé |
| `agent/scenario.json` | ce qu'il va tenter, toujours dans le même ordre |

Le scénario mêle du travail ordinaire et quatre actions à arrêter : lire
`secrets/erp.ini`, l'afficher avec `cat secrets/erp.ini`, appeler un serveur
MCP `snippets` que personne n'a approuvé, et supprimer un fichier de test
avec `rm tests/test_orders.py`.

## Mission

1. **Lancez l'agent tel quel**, depuis `challenge/work` :
   `python3 agent/agent.py`. Toutes les actions passent, sauf les appels
   MCP : aucun serveur n'est encore déclaré. Lisez `agent/journal.json`.
2. **Écrivez les instructions du projet** dans `AGENTS.md` : comment lancer
   les tests, ce que l'agent ne doit jamais faire. Claude Code ne lit
   AGENTS.md de lui-même que si le projet n'a pas de CLAUDE.md. Si vous
   ajoutez un `CLAUDE.md`, il doit importer AGENTS.md par une ligne
   `@AGENTS.md`, sinon AGENTS.md n'est plus lu. L'agent simulé charge ces
   fichiers et ne leur obéit pas, comme tout agent peut ne pas le faire : une
   instruction guide, elle n'arrête rien.
3. **Rendez le secret illisible** avec une règle `permissions.deny` sur
   `Read` dans `.claude/settings.json`. Le fichier reste à sa place :
   l'application en a besoin.
4. **Fermez aussi le chemin du shell.** Une règle `Read` ne couvre pas une
   commande shell : `cat secrets/erp.ini` passe à côté, et c'est une limite
   documentée. Refusez toute commande shell qui affiche le secret, soit dans
   un hook PreToolUse qui lit la commande, soit par une règle `Bash` dans
   `permissions.deny`. Le contrôle essaie plus d'une commande.
5. **Listez les serveurs MCP approuvés** dans `.mcp.json` : le serveur
   `docs`, lancé avec la commande `python3` et les arguments
   `["tools/docs_server.py"]`, et rien d'autre.
6. **Écrivez un hook PreToolUse** sur l'outil `Bash` qui bloque la
   suppression d'un fichier de test, quelle que soit l'écriture de la
   commande (`rm`, `rm -f`, `git rm`...). Toute autre commande doit passer,
   y compris `python3 -m pytest -q` et `rm -rf build/`.
7. **Relancez l'agent** après votre dernière modification. Son journal doit
   dire ce qu'il fait sur votre harness final.

## Ni un hook ni une règle ne sont une frontière de sécurité

Une règle `Bash` compare le **texte** d'une commande : le même programme
appelé par son chemin complet (`/bin/cat`), ou à l'intérieur de `sh -c`, ne
lui correspond pas. Un hook qui lit la commande s'élargit plus facilement,
mais une commande qui fabrique le chemin à l'exécution passe encore. Les
deux attrapent les erreurs courantes d'un agent. Aucun n'arrête un agent
déterminé. Le vrai remède est le **bac à sable**, qui limite ce que le
processus peut lire, quelle que soit la commande. Ce lab ne le simule pas.

## Pistes

La forme de `.claude/settings.json` :

```json
{
  "permissions": {
    "deny": ["Read(./chemin/a/proteger/**)"],
    "allow": ["Bash(python3 -m pytest:*)"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/votre-hook.py\""}]
      }
    ]
  }
}
```

- **Les chemins** de `Read(...)` et `Edit(...)` : `./chemin` ou `chemin` est
  relatif au répertoire courant, `/chemin` à la racine du projet, `~/chemin`
  à votre dossier personnel, `//chemin` est absolu. `*` reste dans un
  répertoire, `**` traverse les répertoires. Dans beaucoup de projets, le
  secret est un fichier `.env`, et la règle est `Read(./.env)`. Une règle
  `Read` couvre aussi Grep et Glob ; une règle `Edit` couvre aussi Write.
- **Les règles Bash** : `*` remplace n'importe quel texte. `Bash(cat *)` (ou
  `Bash(cat:*)`) accepte `cat` seul et `cat x`, mais pas `catalog`. Sans
  étoile, la commande doit être exactement la même.
- **Le matcher d'un hook** : `Bash` ou `Edit|Write` est un nom d'outil exact
  ou une liste. `*` ou un matcher vide désigne tous les outils. Tout autre
  caractère en fait une expression régulière, qui peut correspondre à une
  partie du nom.
- **Un hook** reçoit l'appel en JSON sur son entrée standard. Pour `Bash`, la
  commande est dans `tool_input.command`. Le code de sortie 2 bloque l'appel,
  et ce que vous écrivez sur la sortie d'erreur dit à l'agent pourquoi. Le
  code 0 le laisse continuer. `CLAUDE_PROJECT_DIR` contient la racine du
  projet.
- Éprouvez votre hook seul avant de lancer l'agent :
  `echo '{"tool_name": "Bash", "tool_input": {"command": "git rm tests/test_orders.py"}}' | python3 .claude/hooks/votre-hook.py; echo $?`
- La forme de `.mcp.json` : `{"mcpServers": {"<nom>": {"command": "...", "args": [...]}}}`.
- Bibliothèque standard uniquement : le hook est lancé avec `python3`.

## Les mêmes notions dans d'autres outils

Ces formats sont des exemples concrets. D'autres agents de code ont les
mêmes notions sous d'autres noms : des instructions de projet, des règles et
des permissions, un contrôle avant qu'un outil s'exécute, une liste d'outils
approuvés, et la revue du diff par un humain. Les noms de fichiers et les
formats diffèrent : lisez-les dans la documentation de chaque outil.

## Vérification

```bash
dsoxlab check vc-harness-agent-ia
```

Cinq contrôles. Chacun relance l'agent du lab sur une copie de votre
projet : modifier `agent/agent.py` ne change rien. Ils essaient aussi
d'autres façons de supprimer un test, une autre commande qui affiche le
secret et un autre serveur MCP inconnu, et comparent votre
`agent/journal.json` à ce que fait l'agent maintenant.
