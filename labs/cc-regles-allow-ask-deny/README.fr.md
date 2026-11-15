# Faire appliquer des règles allow, ask et deny, au niveau projet et administré

Lab de la formation **Claude Code**, leçon « settings.json avancé et
permissions ». L'agent de code d'un dépôt a fait un push forcé sur `main`,
parce que le projet autorise `Bash(git *)` et que sa règle deny ne
correspond qu'à un texte exact. Vous écrivez la politique à deux niveaux :
des règles deny et ask dans le projet, sans retirer les règles allow de
l'équipe, et des règles deny au niveau administré, qu'aucun projet ne peut
contourner.

L'agent est un script Python déterministe, pas Claude Code : il dit ce que
décident vos règles fusionnées, il n'exécute rien. Cette partie hors ligne
prouve la lecture des règles. Leur effet dans une vraie session est l'autre
partie du lab, publiée à part.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 40 minutes |
| Leçon associée | [Claude Code : settings.json avancé et permissions](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/settings-json-avance/) |

```bash
dsoxlab run cc-regles-allow-ask-deny
cd labs/cc-regles-allow-ask-deny/challenge/work
python3 agent/agent.py
dsoxlab check cc-regles-allow-ask-deny
```

## Ce que vous saurez faire

- Connaître l'ordre dans lequel Claude Code lit les règles : deny, puis ask,
  puis allow, quelle que soit leur précision.
- Écrire des règles deny qui couvrent toutes les formes d'une commande, en
  sachant qu'une règle lit le texte de la commande.
- Faire demander une action même là où une règle allow plus précise
  correspond.
- Placer un refus au niveau administré pour qu'aucun projet ne le
  contourne, et savoir que les règles des niveaux fusionnent.
