# Éprouver un hook qui réussit, bloque et plante

Premier lab de la section **Claude Code** : un mécanisme par lab. Les hooks
du portail-achats ont l'air en place et ne protègent rien : la garde plante,
le vérificateur de style ne rapporte à personne, les tests n'arrêtent jamais
le tour. Vous les rejouez sur un banc de hooks avec des événements
PreToolUse, PostToolUse et Stop fixés, vous lisez leurs codes de sortie et ce
que Claude recevrait, puis vous les réparez.

Le banc est un script Python, pas Claude Code. Il exécute vraiment vos hooks,
et simule les événements et ce que Claude Code fait d'un code de sortie et
d'une sortie. Le scénario dit exactement ce qui est simulé.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus. Ni réseau, ni Claude Code, ni service d'IA, ni clé d'API |
| Durée | environ 45 minutes |
| Leçon associée | [Les hooks de Claude Code](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/hooks-claude-code/) |

```bash
dsoxlab run cc-hook-qui-echoue
cd labs/cc-hook-qui-echoue/challenge/work
python3 banc/banc_hooks.py
dsoxlab check cc-hook-qui-echoue
```

## Ce que vous saurez faire

- Lire ce que font les codes de sortie 0, 1 et 2 d'un hook sur PreToolUse,
  PostToolUse et Stop, et savoir qu'un hook qui plante (code 1) laisse
  l'action se faire.
- Bloquer un appel par le code 2 avec une raison sur stderr, sans bloquer le
  travail ordinaire.
- Transmettre à Claude le rapport d'un outil qui écrit sur stdout, après une
  modification ou à la fin d'un tour.
- Refuser un appel par une `permissionDecision` JSON en code 0, au bon niveau
  du JSON.
- Éprouver un hook seul, sur le JSON exact qu'il reçoit.
