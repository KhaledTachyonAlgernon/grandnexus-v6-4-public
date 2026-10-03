# Contrat d’apprentissage lent

GrandNexus ne doit pas modifier silencieusement ses règles ou ses connaissances. Une évolution est une expérience versionnée qui possède une hypothèse, un jeu de cas de référence, un résultat observé et une décision explicite d’acceptation ou de rejet.

| Élément | Garantie |
|---|---|
| Source du changement | Retour métacognitif ou observation documentée |
| Version | Identifiant unique et parent explicite |
| Validation | Comparaison avant/après sur le même jeu de cas |
| Régression | Refus si les cas protégés se dégradent au-delà de la tolérance |
| Adoption | Explicitement acceptée, jamais implicite |
| Retour arrière | Ancienne version conservée et restaurable |
| Réutilisation | Une connaissance adoptée doit pouvoir être retrouvée avec sa provenance |

L’apprentissage initial sera symbolique et ciblé. Il ne modifiera pas encore les poids d’un modèle neuronal. Il ajoutera ou révisera des règles et connaissances auditables, avec un nombre limité de changements par expérience afin d’éviter la sur-adaptation aux métriques.
