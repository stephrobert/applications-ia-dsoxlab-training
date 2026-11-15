# D'une demande en prose à un changement qu'un agent ne peut pas tordre

## Situation

La responsable des achats d'une entreprise fictive veut une règle de
validation dans le **portail-achats**, le portail d'achats généré avec un
agent de code. Elle a écrit sa demande en prose, comme tout le monde. Un
agent de code va l'implémenter. Avant qu'il commence, quelqu'un doit
transformer la prose en exigences qu'on ne peut pas lire de deux façons, et
en tests qui disent si le code les respecte. Ce quelqu'un, c'est vous.

Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `REQUEST.fr.md` (`REQUEST.md` en anglais) | la demande, en prose |
| `SPEC.md` | la spécification, à écrire : ses sections et la forme attendue y sont |
| `tests/test_approvals.py` | vos tests, à écrire |
| `plan.json` | le plan du changement, à écrire : ses tranches et les fichiers que l'agent peut modifier |
| `approvals.py` | le module à implémenter : la signature de `approvers(amount, currency)`, aucune règle encore |
| `orders.py` | le module des commandes, propriété d'une autre équipe |
| `agent/agent.py`, `agent/proposal.json` | l'agent simulé et les modifications qu'il va tenter |

L'agent est **un script Python, pas un vrai agent de code**. Il n'appelle
aucun service d'IA. Il joue les mêmes modifications à chaque fois, dans le
même ordre : l'une implémente `approvals.py`, les autres font ce qu'un agent
sous pression peut faire pour obtenir une suite verte. Il n'applique une
modification que si le fichier figure dans votre plan, et il consigne les
empreintes SHA-256 de `SPEC.md` et de `tests/` avant et après son passage.
L'en-tête de `agent/agent.py` liste chaque règle qu'il suit. Son
implémentation est stockée en base64 dans `agent/proposal/`. Ce n'est pas un
secret : c'est pour qu'un coup d'œil au fichier ne réponde pas à la demande
à votre place. Écrivez votre spécification d'après la demande.

## Mission

1. **Lisez la demande** et listez ses règles. L'une d'elles n'est pas
   écrite comme une règle : la demande ne fait que la sous-entendre.
2. **Écrivez `SPEC.md`** : une exigence par règle (`- **R1**: ...`), puis
   des critères d'acceptation de la forme `- AC-n [Rn]: ...`, chacun citant
   son test par son identifiant pytest entre accents graves. Chaque
   exigence a besoin d'au moins un critère. Quand la demande donne une
   limite, dites de quel côté tombe la limite elle-même.
   **Une exigence par règle de la demande**, et les tests d'une exigence ne
   vérifient que sa règle : un cas à la frontière de deux règles appartient
   à l'une des deux. Les contrôles cassent l'implémentation de l'agent une
   règle à la fois. Chaque règle cassée doit faire échouer les tests d'une
   seule de vos exigences, et d'une exigence différente pour chaque règle.
3. **Écrivez les tests** dans `tests/test_approvals.py`. Lancez `pytest`
   avant l'agent : sur le module tel que livré, chaque test doit échouer.
   Un test qui réussit quand rien n'est implémenté ne vérifie rien.
4. **Écrivez `plan.json`** : les tranches du changement, chacune avec les
   exigences qu'elle couvre et les fichiers qu'elle peut modifier. L'agent
   implémente le module, et rien d'autre.
5. **Lancez l'agent**, d'abord avec `python3 agent/agent.py --dry-run` (il
   décide et ne modifie rien), puis sans. Lisez `agent/journal.json`, puis
   lancez `pytest` : la suite doit passer.
6. Si vous modifiez `SPEC.md` ou un test ensuite, **relancez l'agent** :
   son journal doit décrire vos fichiers définitifs.

Les noms de sections de `SPEC.md` (`## Requirements`, `## Acceptance
criteria`) restent en anglais, parce que les contrôles les cherchent. Le
texte des exigences et des critères peut être en français.

## Pistes

La forme de `plan.json` :

```json
{
  "task": "...",
  "slices": [
    {"id": "S1", "goal": "...", "requirements": ["R1"], "files": ["chemin/du/fichier.py"]}
  ]
}
```

- `pytest -v` depuis `challenge/work` nomme chaque test. Un test paramétré
  (`@pytest.mark.parametrize`) vérifie plusieurs cas sous un même
  identifiant.
- `pytest.raises(ValueError)` attend précisément cette exception.
  `pytest.raises(Exception)` attraperait aussi le `NotImplementedError` du
  module tel que livré.
- L'agent écrit dans votre projet. Si un passage a modifié un fichier qu'il
  n'aurait pas dû toucher, restaurez ce fichier avant de le relancer.

## Vérification

```bash
dsoxlab check vc-specification-agent
```

Quatre contrôles. Ils travaillent sur des copies de votre projet. Ils jouent
vos tests contre le module tel que livré, contre l'implémentation de
l'agent, et contre des versions cassées de celle-ci, une par règle de la
demande. Ils relancent l'agent avec votre plan, et comparent ses empreintes
avec votre `agent/journal.json`.
