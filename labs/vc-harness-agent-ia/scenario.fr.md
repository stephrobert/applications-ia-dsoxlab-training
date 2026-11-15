# Un harness pour l'agent, éprouvé sur un agent simulé

## À lire d'abord : ce qui est simulé

L'agent de ce lab est **un script Python, pas Claude Code**. Il n'appelle
aucun service d'IA. Il joue une liste d'actions fixe et applique à chacune
une **partie seulement** des formats réels :

| Format | Ce que l'agent simulé applique | Ce qu'il n'applique pas |
|---|---|---|
| `AGENTS.md` (et `CLAUDE.md` avec `@AGENTS.md`) | charge le fichier et le consigne | il ne lui obéit jamais : il fait ce que dit son scénario |
| `.claude/settings.json`, `permissions.deny` et `permissions.allow` | règles sur `Read`, `Edit`, `Bash` et les outils MCP ; deny l'emporte sur allow | les règles `ask`, les modes de permission, `settings.local.json`, les réglages utilisateur |
| `.claude/settings.json`, `hooks.PreToolUse` | lance votre commande avec l'appel en JSON sur l'entrée standard ; le code de sortie 2 bloque | la sortie JSON d'un hook, les autres événements de hook |
| `.mcp.json`, `mcpServers` | un appel à un serveur non déclaré est refusé | le démarrage des serveurs, leur approbation |

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

Le scénario mêle du travail ordinaire et trois actions à arrêter : lire
`secrets/erp.ini`, appeler un serveur MCP `snippets` que personne n'a
approuvé, et supprimer un fichier de test avec `rm tests/test_orders.py`.

## Mission

1. **Lancez l'agent tel quel**, depuis `challenge/work` :
   `python3 agent/agent.py`. Toutes les actions passent. Lisez
   `agent/journal.json`.
2. **Écrivez les instructions du projet** dans `AGENTS.md` : comment lancer
   les tests, ce que l'agent ne doit jamais faire. Si vous ajoutez aussi un
   `CLAUDE.md`, sa ligne `@AGENTS.md` les importe. L'agent simulé charge ces
   fichiers et ne leur obéit pas, comme tout agent peut ne pas le faire : une
   instruction guide, elle n'arrête rien.
3. **Rendez le secret illisible** avec une règle `permissions.deny` dans
   `.claude/settings.json`. Le fichier reste à sa place : l'application en a
   besoin.
4. **Listez les serveurs MCP approuvés** dans `.mcp.json` : le serveur
   `docs`, lancé avec la commande `python3` et les arguments
   `["tools/docs_server.py"]`, et rien d'autre.
5. **Écrivez un hook PreToolUse** sur l'outil `Bash` qui bloque la
   suppression d'un fichier de test, quelle que soit l'écriture de la
   commande (`rm`, `rm -f`, `git rm`...). Toute autre commande doit passer,
   y compris `python3 -m pytest -q` et `rm -rf build/`.
6. **Relancez l'agent** après votre dernière modification. Son journal doit
   dire ce qu'il fait sur votre harness final.

## Pistes

La forme de `.claude/settings.json` :

```json
{
  "permissions": {
    "deny": ["Read(./chemin/a/proteger)"],
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

- Dans beaucoup de projets, le secret est un fichier `.env`, et la règle est
  `Read(./.env)`. Ici c'est un répertoire : `**` traverse les répertoires.
- Un hook reçoit l'appel en JSON sur son entrée standard. Pour `Bash`, la
  commande est dans `tool_input.command`. Le code de sortie 2 bloque l'appel,
  et ce que vous écrivez sur la sortie d'erreur dit à l'agent pourquoi. Le
  code 0 le laisse continuer.
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

Quatre contrôles. Chacun relance l'agent du lab sur une copie de votre
projet : modifier `agent/agent.py` ne change rien. Ils essaient aussi
d'autres façons de supprimer un test et un autre serveur MCP inconnu, et
comparent votre `agent/journal.json` à ce que fait l'agent maintenant.
