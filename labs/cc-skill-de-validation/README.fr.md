# Construire une skill de validation réutilisable qui lance ses propres scripts

Lab de la formation **Claude Code**, leçon « Skills : routines
réutilisables ». Une première version d'une skill `/valider` n'a jamais été
chargée par Claude Code. Vous la rendez valide et autonome : un `SKILL.md`
correct, ses trois scripts de validation dans son propre dossier
`scripts/`, exécutables et appelés directement, et un `allowed-tools` qui
pré-approuve exactement ces appels.

Le banc est un script Python déterministe, pas Claude Code, et il n'applique
qu'une partie du format réel : le scénario dit laquelle. Il exécute pour de
vrai les étapes de votre skill, y compris sur des copies du projet où un
défaut a été injecté. Un score complet ici ne prouve pas le comportement
d'une version donnée de Claude Code.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 40 minutes |
| Leçon associée | [Claude Code : skills, routines réutilisables](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/skills-claude-code/) |

```bash
dsoxlab run cc-skill-de-validation
cd labs/cc-skill-de-validation/challenge/work
python3 bench/skill_bench.py
dsoxlab check cc-skill-de-validation
```

## Ce que vous saurez faire

- Écrire un `SKILL.md` que Claude Code sait charger : nom de fichier,
  `name` égal au dossier, `description`, lancement à la demande.
- Empaqueter une procédure en skill autonome dont les scripts vivent dans
  son propre dossier `scripts/`.
- Rendre ces scripts exécutables et les appeler directement depuis les
  étapes.
- Pré-approuver exactement les appels de la procédure dans `allowed-tools`,
  et savoir pourquoi un `Bash` nu ou une étoile sur un dossier approuve trop.
