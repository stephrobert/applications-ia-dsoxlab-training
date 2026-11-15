# Une fiche est une demande

## Situation

Julie Petit, acheteuse, a construit le portail-achats avec un assistant
d'IA. Elle a demandé à l'agent de code de « remplir la fiche pour que le
portail puisse être déployé ». L'agent a écrit `application.yaml`, donné au
portail la classe que voulait l'acheteuse, ajouté un champ qui le dit
autorisé, et s'est écrit un schéma que sa fiche passe.

La plateforme travaille avec deux dépôts. Le **dépôt candidat** est celui de
la demandeuse : elle y écrit librement. Le **dépôt de politique** appartient
à la plateforme : il porte le schéma, la grille, la liste de qui peut signer,
et les décisions. Le candidat ne peut pas le modifier. Dans ce lab, vous
jouez les deux côtés : la fiche de la demandeuse, puis la décision de
l'approbatrice, avec une clé à elle.

Tout est dans `challenge/work` :

| Chemin | Contenu |
|---|---|
| `candidat/application.yaml` | la fiche rédigée par l'agent, à reprendre |
| `candidat/schema/` | le schéma que l'agent s'est écrit |
| `politique/schemas/application.schema.json` | le schéma qui fait foi (JSON Schema, draft 2020-12) |
| `politique/classification.json` | la grille de la formation : le critère le plus élevé l'emporte |
| `politique/demandes.toml` | qui a fait chaque demande |
| `politique/allowed_signers` | qui peut signer une décision |
| `politique/decisions/` | les décisions, et leur format dans `README.md` |
| `demande/` | la demande, et ce que l'équipe plateforme a appris |
| `cles/` | deux clés de lab : `demandeur` (Julie Petit) et `approbateur` (Martine Leroy) |
| `plateforme/valider_fiche.py` | valide une fiche avec le dépôt de politique |
| `plateforme/barriere.py` | dit si une application est autorisée, en ne lisant que le dépôt de politique |

Les outils demandent Python 3.11 ou plus et `ssh-keygen`, rien d'autre. Ils
lisent un sous-ensemble de YAML : une valeur par ligne, sans bloc `|` ni `>`.

## Mission

1. **Reprenez la fiche.** Lancez `python3 plateforme/valider_fiche.py` et
   corrigez `candidat/application.yaml` jusqu'à ce qu'elle soit valide.
   Lisez `demande/` pour les faits : ce que fait le portail, ses deux
   propriétaires, la conservation et la finalité de chaque donnée
   (`finalite`, 10 caractères au moins), ses dépendances critiques.
   Déclarez la classe que donne la grille ; `expire_le` reste dans la durée
   d'autorisation maximale de cette classe.
2. **Tentez d'autoriser le portail depuis le dépôt candidat.** Écrivez une
   décision dans `candidat/decisions/`, signez-la avec `cles/demandeur`,
   lancez `python3 plateforme/barriere.py portail-achats` et lisez sa
   réponse. Abaissez `classe_declaree` et relancez.
3. **Décidez en approbatrice.** Remettez la fiche dans son état définitif.
   Écrivez la décision dans `politique/decisions/portail-achats-<date>.yaml`
   (format dans `politique/decisions/README.md`), avec l'empreinte sha256 de
   la fiche, la classe que donne la grille, Martine Leroy comme décideuse.
   Signez-la avec sa clé :

   ```bash
   chmod 600 cles/approbateur cles/demandeur
   sha256sum candidat/application.yaml
   ssh-keygen -Y sign -f cles/approbateur -n decision-applicative politique/decisions/<fichier>.yaml
   ```

   `python3 plateforme/barriere.py portail-achats` doit alors répondre
   AUTHORISED.

## Pistes

- Toute modification de `application.yaml` après la signature casse la
  décision : son empreinte ne correspond plus.
- Le RGPD lie une durée de conservation à une finalité : une durée sans
  finalité ne dit pas pourquoi la donnée est gardée.
- `DATE_SIMULEE=AAAA-MM-JJ` remplace la date du jour pour la barrière.
- Les clés de `cles/` sont des clés de lab : elles ne protègent rien.

## Vérification

```bash
dsoxlab check vc-contrat-applicatif
```

Quatre contrôles. Ils relancent les outils d'origine de la plateforme avec
le dépôt de politique d'origine, jamais les copies de `challenge/work`, et
rejouent ce qui doit être refusé : une fiche sans propriétaire, une donnée
sans durée de conservation ou sans finalité, et votre propre décision signée
déplacée dans le dépôt candidat.
