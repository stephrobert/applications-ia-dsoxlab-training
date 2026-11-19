# Challenge : Un hook qui réussit, bloque et plante

## À lire d'abord : ce qui est simulé

Ce lab se joue **sans Claude Code** et n'appelle aucun service d'IA. Il
fournit un **banc de hooks**, `banc/banc_hooks.py`, un script Python qui fait
pour les hooks ce que fait Claude Code :

| | Réel ou simulé |
|---|---|
| Vos hooks (les commandes de `.claude/settings.json`) | **réels** : le banc les exécute, avec l'événement en JSON sur stdin et `CLAUDE_PROJECT_DIR` posée |
| Les événements (une commande Bash, une modification, la fin d'un tour) | **simulés** : des fichiers JSON fixés dans `banc/evenements/`. Rien n'est supprimé ni modifié |
| Ce que Claude Code fait du code de sortie et de la sortie d'un hook | **simulé**, d'après la documentation officielle : bloqué ou non, ce que Claude lit, ce que vous voyez |
| Le modèle | **absent** : aucune réponse, aucune réaction |

Chaque événement se joue dans une copie jetable du projet : un hook peut lire
et lancer ce dont il a besoin, vos fichiers ne sont jamais touchés. Le banc
écrit ce qui s'est passé dans `banc/journal.json`. Son en-tête liste chaque
règle qu'il applique, et ce qu'il ne simule pas (règles de permission,
`onFailure`, `async`...). Un score complet prouve que vos hooks rendent le bon
code de sortie et la bonne sortie. Il ne prouve pas que Claude, le modèle,
agira bien ensuite.

## Situation

L'équipe du **portail-achats** a trois hooks dans `.claude/settings.json`. Sur
le papier, ils protègent le projet. En pratique :

| Événement | Hook | Ce qu'il devrait faire |
|---|---|---|
| `PreToolUse` sur `Bash` | `.claude/hooks/garde_tests.py` | bloquer toute commande qui supprime la suite de tests |
| `PostToolUse` sur `Edit\|Write` | `python3 outils/verifier_style.py` | signaler à Claude les défauts de style qu'il vient d'écrire |
| `Stop` | `python3 -m unittest -q` | renvoyer Claude au travail quand il finit son tour avec un test en échec |

Une quatrième règle n'existe que dans le README : l'agent ne doit jamais
modifier `config/production.toml`. Aucun hook ne la fait respecter.

## Ce que veulent dire les codes de sortie

C'est tout le lab. Un hook ne parle à Claude Code que par son code de sortie
et sa sortie :

| Code de sortie | PreToolUse | PostToolUse | Stop |
|---|---|---|---|
| **0** | l'appel continue ; une décision JSON sur stdout peut encore le refuser | rien ne parvient à Claude | Claude s'arrête |
| **2** | l'appel est **bloqué** ; Claude lit **stderr** | l'outil a déjà tourné ; Claude lit **stderr** | Claude **ne s'arrête pas** ; il lit **stderr** et continue |
| **tout autre** (1 compris) | erreur non bloquante : l'appel **passe** | erreur non bloquante : Claude ne lit rien | erreur non bloquante : Claude s'arrête |

Sur une erreur non bloquante, vous voyez un avertissement dans la session.
Claude, lui, ne voit rien. Le code 1 est le code d'échec habituel sous Unix,
donc aussi celui que rend un script Python qui plante : une garde qui plante
laisse tout passer.

Sur ces trois événements, Claude ne lit jamais stdout. Seulement stderr, et
seulement en code 2.

## Mission

Travaillez dans `challenge/work`.

1. **Rejouez les hooks tels quels** : `python3 banc/banc_hooks.py`. Neuf
   événements sont joués. Lisez chaque ligne : l'issue, le code de sortie de
   chaque hook, ce que vous verriez, ce que Claude verrait. Ouvrez
   `banc/journal.json` pour le stdout et le stderr complets.
2. **Réparez la garde** `garde_tests.py`. Lancez-la d'abord seule, sur le
   JSON qu'elle reçoit :
   `python3 banc/banc_hooks.py --print-input 02 | python3 .claude/hooks/garde_tests.py; echo "exit $?"`.
   Elle doit bloquer la suppression des tests (`rm -rf tests/`, mais aussi
   `git rm -r tests` ou `rm -f ./tests/test_facture.py`) par le **code 2**
   avec une raison sur **stderr**, et laisser passer toute autre commande en
   code 0, sans planter.
3. **Faites entendre le vérificateur de style.** Il se comporte comme ruff :
   constats sur stdout, code de sortie 1. Modifiez la commande `PostToolUse`
   pour que ses constats parviennent à Claude, et pour qu'un fichier propre
   donne le code 0.
4. **Faites que le hook Stop empêche la fin du tour quand un test échoue**,
   avec le rapport des tests transmis à Claude, et qu'il laisse Claude
   s'arrêter quand les tests passent.
5. **Protégez `config/production.toml`** par un nouveau hook `PreToolUse`
   sur `Edit|Write`. Celui-ci ne doit pas utiliser le code 2 : il **sort en
   0** et écrit une décision JSON sur stdout (format ci-dessous). Tout autre
   fichier reste modifiable, `config/developpement.toml` compris.
6. **Rejouez le banc** après votre dernière modification. Son journal doit
   dire ce que font vos hooks finaux.

## La décision JSON d'un hook PreToolUse

En code 0, un hook PreToolUse peut écrire **un seul objet JSON, et rien
d'autre**, sur stdout :

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Pourquoi l'appel est refusé. Claude lit ce texte."
  }
}
```

- `permissionDecision` : `deny` refuse l'appel, `ask` vous demande, `allow`
  saute la demande de permission.
- La décision vit **dans** `hookSpecificOutput`, qui doit nommer son
  événement dans `hookEventName`. Un `permissionDecision` au premier niveau
  n'est pas lu.
- Le JSON n'est lu qu'en code 0. En code 1, il est ignoré. En code 2,
  l'appel est bloqué de toute façon.
- Pour un `Edit` ou un `Write`, le chemin est dans `tool_input.file_path`, en
  chemin **absolu**.

## Repères

- La forme d'une entrée de hook dans `.claude/settings.json` :

  ```json
  {"matcher": "Edit|Write",
   "hooks": [{"type": "command",
              "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/votre-hook.py\"",
              "timeout": 10}]}
  ```

  Plusieurs entrées peuvent se suivre sous le même événement. `Stop` ne
  prend pas de matcher.
- **Matcher** : `"*"`, `""` ou pas de matcher veut dire tous les outils. Une
  valeur faite seulement de lettres, chiffres, `_`, `-`, espaces, virgules
  et `|` est un nom exact ou une liste (`Edit|Write`). Tout autre caractère
  en fait une expression régulière qui peut reconnaître une partie d'un
  nom : `Edit.*` reconnaît aussi `NotebookEdit`.
- **Le JSON que reçoit un hook** porte toujours `session_id`, `cwd`,
  `hook_event_name` et quelques autres champs. Pour `PreToolUse`, il ajoute
  `tool_name`, `tool_input` et `tool_use_id`. Pour un appel Bash, la
  commande est dans `tool_input.command`. `--print-input` montre le JSON
  exact.
- **Une commande shell peut choisir ses flux et son code de sortie.** `1>&2`
  envoie stdout vers stderr. `cmd || exit 2` sort en 2 quand `cmd` échoue, et
  en 0 quand elle réussit.
- `python3 banc/banc_hooks.py --only 07` ne rejoue que les événements dont le
  nom commence par `07`.
- Le hook tourne avec `python3` : bibliothèque standard uniquement.

## Vérification

```bash
dsoxlab check cc-hook-qui-echoue
```

Cinq contrôles. Chacun rejoue le banc du lab sur vos hooks : modifier
`banc/banc_hooks.py` ou les événements ne change rien. Ils ajoutent aussi
leurs propres événements : d'autres façons de supprimer les tests, un autre
défaut de style, un autre test en échec, un `Write` sur les réglages de
production. Et ils comparent votre `banc/journal.json` à ce que font vos hooks
maintenant.
