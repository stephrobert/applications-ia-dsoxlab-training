# portail-achats: what the platform team found out

## EN

- **Business owner:** Martine Leroy (`m.leroy`), head of the purchasing
  department. She accepts to own the portal.
- **Technical owner:** Samir Moreau (`s.moreau`), applications team of the IT
  department. He accepts to maintain it if the buyer leaves.
- **Retention**, set by the data protection officer:
  - supplier contacts (name, email, phone): **1095 days**;
  - the local copy of purchase orders (amounts and items, no contact):
    **30 days**.
- **Critical dependencies:** the ERP API, `erp-achats`. When it stops, the
  portal shows nothing. The portal depends on no other service.
- **Who decides:** for this request, the signed decision belongs to Martine
  Leroy, head of the requesting department (role `responsable_service`). Her
  lab key is `cles/approbateur`. Julie Petit's lab key is `cles/demandeur`.

## FR

- **Propriétaire métier :** Martine Leroy (`m.leroy`), responsable du service
  achats. Elle accepte d'être propriétaire du portail.
- **Propriétaire technique :** Samir Moreau (`s.moreau`), équipe applications
  de la DSI. Il accepte de le maintenir si l'acheteuse s'en va.
- **Conservation**, fixée par le délégué à la protection des données :
  - contacts fournisseurs (nom, courriel, téléphone) : **1095 jours** ;
  - copie locale des commandes d'achat (montants et articles, sans contact) :
    **30 jours**.
- **Dépendances critiques :** l'API de l'ERP, `erp-achats`. Quand elle
  s'arrête, le portail n'affiche plus rien. Le portail ne dépend d'aucun autre
  service.
- **Qui décide :** pour cette demande, la décision signée revient à Martine
  Leroy, responsable du service demandeur (rôle `responsable_service`). Sa clé
  de lab est `cles/approbateur`. Celle de Julie Petit est `cles/demandeur`.
