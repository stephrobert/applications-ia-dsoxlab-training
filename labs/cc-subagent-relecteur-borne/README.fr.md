# Limiter un subagent relecteur aux outils qui lisent

Lab de la formation **Claude Code**, leçon « Subagents ». Un subagent
relecteur dont le fichier n'a pas de champ `tools` a corrigé le code lui-même
pendant une revue : il hérite de tous les outils de la session. Vous lui
donnez une liste `tools` explicite, ce qu'une revue doit lire et rien qui
écrive, sans toucher au reste de son fichier ni à l'autre subagent.

Le banc est un script Python déterministe, pas Claude Code, et il n'applique
qu'une partie du format réel : le scénario dit laquelle. Un score complet ici
ne prouve pas le comportement d'une version donnée de Claude Code.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 30 minutes |
| Leçon associée | [Claude Code : subagents pour isoler le contexte et déléguer les tâches longues](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/subagents-claude-code/) |

```bash
dsoxlab run cc-subagent-relecteur-borne
cd labs/cc-subagent-relecteur-borne/challenge/work
python3 bench/agent_bench.py
dsoxlab check cc-subagent-relecteur-borne
```

## Ce que vous saurez faire

- Savoir qu'un subagent sans champ `tools` hérite de tous les outils de la
  session, outils MCP et outils à venir compris.
- Écrire une liste `tools` qui garde les lectures dont une revue a besoin et
  retire tout outil qui écrit.
- Borner `Bash` aux commandes qui lisent, et savoir pourquoi `Bash(git *)`
  est trop large.
- Savoir qu'une consigne dans le prompt (« ne modifie jamais un fichier »)
  n'est pas une barrière, et qu'une liste noire laisse le reste hérité.
