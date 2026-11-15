# Demande : les validations dans le portail d'achats

De : Claire, responsable des achats
À : l'équipe du portail-achats

Bonjour,

À partir du premier du mois prochain, aucune commande ne doit partir chez un
fournisseur avant que les bonnes personnes aient dit oui. Voici ce que nous
avons convenu avec la finance.

Les petites commandes, jusqu'à 1 000 euros (1 000 compris), l'acheteur les
passe seul, comme aujourd'hui. Au-dessus, le responsable de l'acheteur
valide d'abord la commande. Les grosses, au-dessus de 10 000 euros, passent
aussi par la direction financière, une fois que le responsable a validé.

Tous nos fournisseurs facturent en euros, et nos seuils sont en euros. Une
commande coûte toujours quelque chose. Quand le portail ne sait pas dire qui
doit valider une commande, il la refuse : il ne laisse jamais passer une
commande par défaut.

Ne touchez pas au module des commandes (`orders.py`) cette fois : l'équipe
qui en est propriétaire appellera votre fonction plus tard, une fois testée.

Merci,
Claire

(La version anglaise, `REQUEST.md`, dit la même chose. Les noms de rôles que
rend le code restent en anglais : `manager` et `finance`.)
