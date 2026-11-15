# Un push forcé que les règles ont laissé passer

## À lire d'abord : ce qui est simulé

L'agent de ce lab est **un script Python, pas Claude Code**. Il n'appelle
aucun service d'IA, n'a pas besoin du réseau, et n'exécute jamais les
actions de son scénario. Il lit les règles de permission de deux niveaux de
réglages et dit ce qu'elles décident pour chaque action :

| Niveau | Fichier dans ce lab | Fichier réel |
|---|---|---|
| administré | `managed/managed-settings.json` | `/etc/claude-code/managed-settings.json` sous Linux et WSL, déployé par l'organisation |
| projet | `.claude/settings.json` | le même, partagé par l'équipe via git |

Ce qu'il applique : les règles des deux niveaux **fusionnent**, elles ne se
remplacent pas. Tous les `deny` sont lus d'abord, puis tous les `ask`, puis
tous les `allow`, et la première règle qui correspond décide. Une règle plus
précise ne change pas cet ordre. `allowManagedPermissionRulesOnly: true` dans
le fichier administré retire les règles du projet. La syntaxe des règles
(`Bash(...)`, `Read(...)`) est listée dans l'en-tête de `agent/agent.py`.

Ce qu'il n'applique pas : les réglages utilisateur, `settings.local.json`,
les modes de permission, les hooks, le bac à sable, et le découpage d'une
commande en morceaux que fait un vrai agent. Un score complet prouve donc
que vos règles **disent** la bonne chose à cet agent. Il ne prouve pas ce
que fait une version donnée de Claude Code en session : c'est la partie de
ce lab qui se joue dans une vraie session, publiée à part.

## Situation

La semaine dernière, l'agent de code de **portail-achats** a fait un push
forcé sur `main` et effacé deux commits d'une autre personne de l'équipe. Le projet autorise
`Bash(git *)`, et sa seule règle deny ne correspond qu'à un texte exact.

L'équipe et l'équipe sécurité ont écrit une politique dans
`docs/policy.md`. Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `.claude/settings.json` | les règles de l'équipe, telles qu'elles sont aujourd'hui |
| `managed/` | tient lieu des réglages administrés de la machine (vide pour l'instant) |
| `docs/policy.md` | la politique, niveau projet et niveau administré |
| `agent/agent.py`, `agent/scenario.json` | l'agent simulé et les actions de l'incident |
| `src/`, `secrets/` | le code, et des identifiants que l'agent ne doit jamais lire |

## Mission

1. **Lancez l'agent tel quel**, depuis `challenge/work` :
   `python3 agent/agent.py`. Toutes les actions de l'incident sont
   autorisées.
2. **Niveau projet** : dans `.claude/settings.json`, refusez toute forme de
   push forcé par des règles deny, et faites demander tout autre push par
   une règle ask. **Gardez toutes les règles allow de l'équipe**,
   `Bash(git *)` et `Bash(git push origin feature/*)` comprises.
3. **Niveau administré** : créez `managed/managed-settings.json` et refusez
   `curl`, `wget` et la lecture de `secrets/`, à toute profondeur. Rien
   d'autre : l'équipe doit encore lire le code, utiliser git et lancer les
   tests.
4. **Relancez l'agent** après votre dernière modification. Son journal,
   `agent/journal.json`, doit dire ce qu'il décide sur vos fichiers finaux.

## Repères

- Une règle lit le **texte** de la commande. `Bash(git push --force *)`
  accepte `git push --force` et `git push --force origin main`, mais pas
  `git push origin main --force`. Comptez les places où un drapeau peut se
  trouver.
- Un motif qui finit par ` *` accepte aussi la commande nue :
  `Bash(git push *)` couvre `git push` seul.
- `*` vaut n'importe quel texte, lettres comprises : un motif qui cherche
  `-f` n'importe où dans la commande attrape aussi une branche nommée
  `price-format`.
- Un allow ne fait jamais exception à un deny, et un ask demande encore
  quand un allow plus précis correspond. C'est pour cela que l'équipe peut
  garder ses règles allow.
- `Read(./secrets/*)` reste dans un seul répertoire ; `**` traverse les
  répertoires.
- Un deny dans le projet ne protège que ce projet, et un contributeur peut
  le modifier. Un deny dans le fichier administré s'applique à tous les
  projets de la machine, et aucun projet ne peut le contourner.

## Vérifier

```bash
dsoxlab check cc-regles-allow-ask-deny
```

Quatre contrôles. Chacun relance l'agent du lab sur une copie de votre
projet, avec **des actions que `agent/scenario.json` ne montre pas** :
d'autres formes de push forcé, d'autres push, d'autres lectures de
`secrets/`. Un contrôle **ajoute d'abord au projet** une règle allow pour
`wget` et pour `secrets/`, et attend que le niveau administré les refuse
quand même. Modifier `agent/agent.py` ne change rien.
