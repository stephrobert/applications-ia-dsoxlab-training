# Politique de sécurité

**Langue :** [English](./SECURITY.md) · [Français](./SECURITY.fr.md)

## Versions supportées

`applications-ia-dsoxlab-training` est en développement actif. Les correctifs de
sécurité sont appliqués à la dernière version de la branche `main`.

| Version | Supportée |
| --- | --- |
| dernière (`main`) | oui |
| plus anciennes | non |

## Signaler une vulnérabilité

**N'ouvrez pas d'issue publique pour une vulnérabilité de sécurité.**

Si vous pensez avoir trouvé une vulnérabilité, signalez-la en privé :

- De préférence : ouvrez un
  [avis de sécurité privé](https://github.com/stephrobert/applications-ia-dsoxlab-training/security/advisories/new)
  sur GitHub.
- Sinon, utilisez les coordonnées publiées sur
  <https://www.stephane-robert.info>.

Merci d'inclure :

- une description de la vulnérabilité et de son impact,
- les étapes pour la reproduire (commande, environnement, `dsoxlab --version`),
- tout journal ou preuve de concept pertinent.

Nous vous tiendrons informé de l'avancement du correctif et vous créditerons
dans les notes de version si vous le souhaitez.

## Politique de divulgation

Nous pratiquons la divulgation coordonnée et nous engageons sur les délais
suivants, décomptés à partir de la réception de votre signalement :

| Étape | Délai visé |
| --- | --- |
| Accusé de réception de votre signalement | sous **48 heures** |
| Évaluation initiale et qualification de la sévérité | sous **5 jours** |
| Correctif publié, ou plan de remédiation écrit | sous **30 jours** |
| Divulgation publique de la vulnérabilité | sous **90 jours** |

Nous publions l'avis de sécurité dès qu'un correctif est disponible, ou au plus
tard à l'échéance des **90 jours**, selon ce qui arrive en premier. Si une
vulnérabilité est activement exploitée, nous pouvons la divulguer plus tôt pour
protéger les utilisateurs. Si un correctif complexe demande plus de temps, nous
vous prévenons avant l'échéance et convenons d'une nouvelle date avec vous,
plutôt que de la laisser expirer sans rien dire.

## Périmètre

Ce dépôt livre du **contenu de labs** : énoncés, fixtures, tests pytest et
solutions de référence chiffrées, joués par la CLI externe `dsoxlab` dans un
shell local. Les labs n'appellent **aucun service d'IA** et n'exigent **aucune clé
d'API** : l'agent et ses propositions sont des fichiers fournis. Le registre de
paquets de `vc-paquet-inexistant` est un répertoire local de roues fictives ;
aucun lab n'accède au réseau.

CodeQL n'analyse ni `labs/**/fixtures/**` ni `labs/**/solution/**` (voir
[`.github/codeql/config.yml`](.github/codeql/config.yml)). Ce que le dépôt livre
comme outillage **propre** (workflows, scripts de validation, tests pytest) reste
entièrement analysé.

Dans le périmètre :

- un matériau de lab dangereux ou malveillant, notamment un test ou une fixture
  qui accéderait au réseau, appellerait un vrai service d'IA ou exfiltrerait des
  données du poste de l'apprenant ;
- la fuite d'un vrai secret, d'une clé privée ou d'un jeton d'API commité par
  erreur ;
- une solution de référence livrée en clair, qui gâche le lab et reste dans
  l'historique ;
- une action référencée sans épinglage par SHA dans ce que le dépôt livre.

Hors périmètre :

- les vulnérabilités du moteur `dsoxlab` lui-même, qui relèvent de
  [son propre dépôt](https://github.com/stephrobert/dsoxlab) ;
- celles d'une dépendance tierce, à signaler à son projet ;
- un lab qui échoue ou note mal : c'est un défaut, ouvrez une issue publique.

## Ce que ce dépôt ne vous demandera jamais

Aucun lab n'exige de compte chez un fournisseur d'IA, de clé d'API ni de vrai
secret. Si un énoncé vous en demande un, c'est un défaut du catalogue :
signalez-le.
