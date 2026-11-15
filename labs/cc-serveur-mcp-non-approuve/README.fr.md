# Refuser un serveur MCP qu'un dépôt déclare sans approbation

Lab de la formation **Claude Code**, leçon « Brancher un serveur MCP ». Une
contribution a ajouté un serveur au `.mcp.json` commité d'un dépôt, et
personne ne l'a approuvé. Vous le repérez, vous le refusez par une règle
`permissions.deny` pour qu'il reste refusé s'il revient, et vous gardez les
serveurs approuvés et leurs permissions.

Le banc est un script Python déterministe, pas Claude Code, et il n'applique
qu'une partie des formats réels : le scénario dit laquelle. Un score complet
ici ne prouve pas le comportement d'une version donnée de Claude Code.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 30 minutes |
| Leçon associée | [Claude Code : brancher un serveur MCP](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/mcp-claude-code/) |

```bash
dsoxlab run cc-serveur-mcp-non-approuve
cd labs/cc-serveur-mcp-non-approuve/challenge/work
python3 bench/mcp_bench.py
dsoxlab check cc-serveur-mcp-non-approuve
```

## Ce que vous saurez faire

- Repérer, dans un `.mcp.json` commité, un serveur absent de la liste
  approuvée.
- Refuser un serveur MCP entier par une règle `mcp__<serveur>` dans
  `permissions.deny`, et savoir qu'une règle avec des parenthèses ne refuse
  rien.
- Savoir que retirer une ligne de `.mcp.json` ne tient que jusqu'à la
  prochaine fusion, alors qu'une règle deny reste.
- Refuser un serveur sans perdre les autres : pas de `mcp__*` en `deny`, et
  jamais en `allow`.
