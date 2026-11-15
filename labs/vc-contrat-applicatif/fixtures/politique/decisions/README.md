# Decisions / Décisions

One decision per file, `<application-id>-<date>.yaml`, with its signature next
to it, `<application-id>-<date>.yaml.sig`. Only the platform barrier reads this
directory. A decision anywhere else authorises nothing.

Une décision par fichier, `<id-application>-<date>.yaml`, avec sa signature à
côté, `<id-application>-<date>.yaml.sig`. Seule la barrière de la plateforme
lit ce répertoire. Une décision posée ailleurs n'autorise rien.

```yaml
id: <application-id>-<date>
application: <application-id>
fiche_sha256: <sha256 of candidat/application.yaml>
classe_retenue: C1 | C2 | C3 | C4
decision: accepte | accepte_sous_conditions | refuse
risques_acceptes: []
conditions: []
demandeur: <identifier of the requester>
decideur:
  identifiant: <signer, as in allowed_signers>
  role: responsable_service | securite
date_decision: YYYY-MM-DD
expire_le: YYYY-MM-DD
```

`classe_retenue` may be above the class the policy grid computes for
`application.yaml`, never below. / `classe_retenue` peut être au-dessus de la
classe que la grille de la politique calcule pour `application.yaml`, jamais
en dessous.

Answers of the barrier / Réponses de la barrière (`plateforme/barriere.py`) :

| Code | EN | FR |
|---|---|---|
| 0 | authorised | autorisée |
| 10 | no decision in this directory | aucune décision dans ce répertoire |
| 11 | signature missing or invalid, or signer absent from allowed_signers | signature absente ou invalide, ou signataire absent d'allowed_signers |
| 12 | the decider is the requester | le décideur est le demandeur |
| 13 | role insufficient for the retained class | rôle insuffisant pour la classe retenue |
| 14 | decision expired, or longer than its class allows | décision expirée, ou plus longue que sa classe ne le permet |
| 15 | application.yaml differs from the one the decision signed | application.yaml n'est pas celle que la décision a signée |
| 16 | classe_retenue below the class the grid computes | classe_retenue sous la classe que calcule la grille |

Sign with / Signer avec :

```bash
ssh-keygen -Y sign -f <private key> -n decision-applicative <file>.yaml
```
