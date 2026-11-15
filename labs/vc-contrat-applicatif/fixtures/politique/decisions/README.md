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

Sign with / Signer avec :

```bash
ssh-keygen -Y sign -f <private key> -n decision-applicative <file>.yaml
```
