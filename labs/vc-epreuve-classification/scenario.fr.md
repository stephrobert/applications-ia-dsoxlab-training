# Qualifier une application que personne n'a décrite

## Situation

Le portail-achats demande à être hébergé sur la plateforme de l'entreprise.
Julie Petit, acheteuse, l'a construit avec un assistant d'IA et demande C2.
Personne n'a écrit ce qu'il fait : ni demande, ni documentation. Son agent de
code a rédigé une fiche « pour que le portail puisse être déployé ». C'est
l'équipe plateforme qui classe, pas la demandeuse, et elle décide d'après ce
que fait l'application.

C'est l'épreuve du niveau 1. Vous connaissez déjà chaque outil : la grille et
`classify.py` de `vc-classifier-applications`, le dépôt de politique et la
barrière de `vc-contrat-applicatif`. Ici, vous les appliquez seul, sur une
application qu'il faut lire.

Tout est dans `challenge/work` :

| Chemin | Contenu |
|---|---|
| `candidat/src/portail/` | le code du portail, seule description de ce qu'il fait |
| `candidat/application.yaml` | la fiche rédigée par l'agent |
| `candidat/schema/` | le schéma que l'agent s'est écrit |
| `accueil/precisions.md` | ce que le code ne peut pas dire : propriétaires, arrêt, qui décide |
| `accueil/registre-conservation.md` | le registre de conservation de l'entreprise |
| `grille.toml`, `classify.py` | la grille de la formation et son calcul |
| `classification.toml` | votre classification, à remplir |
| `politique/` | le dépôt de politique : schéma, grille, demandes, qui peut signer, décisions |
| `plateforme/valider_fiche.py` | valide une fiche avec le dépôt de politique |
| `plateforme/barriere.py` | dit si une application est autorisée, en ne lisant que le dépôt de politique |
| `cles/` | deux clés de lab : `demandeur` (Julie Petit) et `approbateur` (Martine Leroy) |

Les outils demandent Python 3.11 ou plus et `ssh-keygen`, rien d'autre. Les
outils de la plateforme lisent un sous-ensemble de YAML : une valeur par
ligne, pas de blocs `|` ou `>`. Rien dans cette épreuve ne lance le portail
ni n'appelle le réseau.

## Mission

1. **Qualifiez le portail.** Lisez son code : ce qu'il conserve, quels
   systèmes de l'entreprise il appelle et comment, qui peut l'utiliser. Lisez
   `accueil/` pour le reste. Remplissez `classification.toml` comme dans
   `vc-classifier-applications` : les critères, le sort de la classe
   demandée, la classe retenue et sa politique. `python3 classify.py` vérifie
   la cohérence.
2. **Vérifiez sa fiche.** Reprenez `candidat/application.yaml` jusqu'à ce
   qu'elle déclare ce que fait le code et que
   `python3 plateforme/valider_fiche.py` réponde valide. Chaque donnée prend
   la durée et la finalité de sa ligne du registre.
3. **Préparez sa décision.** Avant de signer quoi que ce soit, lancez
   `python3 plateforme/barriere.py portail-achats` et lisez sa réponse. Puis,
   en approbatrice, écrivez la décision dans
   `politique/decisions/portail-achats-<date>.yaml` (format dans
   `politique/decisions/README.md`) et signez-la :

   ```bash
   chmod 600 cles/approbateur cles/demandeur
   sha256sum candidat/application.yaml
   ssh-keygen -Y sign -f cles/approbateur -n decision-applicative politique/decisions/<fichier>.yaml
   ```

   La barrière doit alors répondre AUTHORISED.

## Règles de l'épreuve

- La vérification rend un verdict par critère, pas sa raison. Chaque
  critère est critique : aucun total ne compense un critère manqué.
- Il n'y a aucun indice : l'épreuve se passe sans aide, comme elle se note.
- Toute modification de `application.yaml` après la signature casse la
  décision : son sha256 ne correspond plus.
- `DATE_SIMULEE=AAAA-MM-JJ` remplace la date du jour pour la barrière.
- Les clés de `cles/` sont des clés de lab : elles ne protègent rien.

## Vérification

```bash
dsoxlab check vc-epreuve-classification
```

Cinq critères. Les contrôles relancent les outils d'origine et le dépôt de
politique d'origine, jamais les copies de `challenge/work`, et rejouent ce
qui doit rester refusé : une fiche sans finalité ou dont la demandeuse est
propriétaire, votre décision sans sa signature, et votre décision signée
déplacée dans le dépôt candidat.
