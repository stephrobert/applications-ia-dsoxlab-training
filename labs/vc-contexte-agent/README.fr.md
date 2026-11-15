# Concevoir le contexte d'un agent de code et vérifier ce qu'il a vraiment chargé

Lab de niveau 1 de la formation **Gouverner et sécuriser les applications
générées par IA**, parcours « Vibe coder avec méthode ». Le portail-achats
donne tout à son agent dans un seul `CLAUDE.md`, y compris un historique de
plus de 3 000 lignes. Vous comparez cette configuration à la vôtre sur la
même tâche, puis vérifiez dans le journal de l'agent quelle information il a
réellement chargée, et pourquoi.

L'agent est un script Python déterministe, pas Claude Code, et il ne simule
qu'une partie de la façon dont Claude Code charge son contexte : le scénario
dit laquelle. Un score complet ici ne prouve pas le comportement d'un vrai
agent.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus, avec pytest. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 45 minutes |
| Leçon associée | [Applications générées par IA](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/) (la leçon « Concevoir le contexte d'un agent » n'est pas encore publiée) |
| Précédent | `vc-paquet-inexistant` |
| Suivant | `vc-harness-agent-ia` |

```bash
dsoxlab run vc-contexte-agent
cd labs/vc-contexte-agent/challenge/work
python3 agent/agent.py
dsoxlab check vc-contexte-agent
```

## Ce que vous saurez faire

- Garder un `CLAUDE.md` court, avec des commandes que vous avez lancées et
  qui fonctionnent.
- Savoir qu'un import `@` charge le fichier entier au démarrage, et citer un
  gros document par son chemin à la place.
- Ne charger une règle que quand l'agent travaille sur les fichiers qu'elle
  concerne.
- Lire un journal de chargement pour savoir ce qu'un agent avait dans son
  contexte, et pourquoi.
