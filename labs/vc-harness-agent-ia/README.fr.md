# Poser un harness minimal pour un agent de code et l'éprouver sur un agent simulé

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**, parcours « Vibe coder avec méthode ». Un nouveau dépôt du
portail-achats n'a aucun harness. Vous écrivez ses instructions de projet,
ses permissions, un hook PreToolUse et sa liste de serveurs MCP approuvés,
puis vous lancez un agent simulé : il doit échouer à lire le secret,
directement ou par le shell, se voir
refuser un serveur MCP inconnu et être bloqué quand il supprime un test,
pendant que son travail ordinaire passe.

L'agent est un script Python déterministe, pas Claude Code, et il n'applique
qu'une partie des formats réels : le scénario dit laquelle. Un score complet
ici ne prouve pas le comportement d'un vrai agent.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 60 minutes |
| Leçon associée | [Poser un harness](https://www.stephane-robert.info/docs/ia/applications-generees-par-ia/poser-un-harness/) |
| Précédent | `vc-paquet-inexistant` |

```bash
dsoxlab run vc-harness-agent-ia
cd labs/vc-harness-agent-ia/challenge/work
python3 agent/agent.py
dsoxlab check vc-harness-agent-ia
```

## Ce que vous saurez faire

- Écrire les instructions d'un projet dans `AGENTS.md`, en sachant qu'elles
  guident un agent sans l'arrêter.
- Refuser la lecture d'un secret par une règle `permissions.deny`, sans
  supprimer le secret, et fermer le chemin du shell qu'une règle `Read`
  laisse ouvert.
- Savoir que ni un hook ni une règle `Bash` ne sont une frontière de
  sécurité, et que le bac à sable en est une.
- Écrire un hook PreToolUse qui lit l'appel sur son entrée standard et le
  bloque par le code de sortie 2, sans bloquer le travail légitime.
- Tenir les serveurs MCP d'un projet à une liste approuvée.
