# Autonomie libre simulée — niveau 1

## Protocole

GrandNexus a exécuté 120 cycles sans séquence d’objectifs fournie. Le `DriveModule` a produit les priorités internes et la boucle a sélectionné ses objectifs à partir des actions symboliquement applicables dans l’état courant. Le LLM, les embeddings, le multi-agent et les actions externes étaient désactivés.

Le parcours comprenait quatre perturbations non annoncées au noyau : batterie faible au cycle 25, localisation inconnue aux cycles 50–54, redémarrage au cycle 61 et conflit explicite `door:open`/`door:closed` aux cycles 80–83.

## Résultats

| Indicateur | Résultat |
|---|---:|
| Cycles | 120 |
| Simulations réussies | 111 |
| Refus ou échecs | 5 |
| Cycles suspendus par conflit | 4 |
| Objectifs distincts | 9 |
| Propositions d’apprentissage `pending` | 21 |
| Promotions automatiques | 0 |
| Révision finale du registre | 117 |
| Événements d’état visibles après redémarrage | 228 |
| Mutation du graphe stable | Aucune |

## Comportements observés

La batterie faible a déclenché un retour au domicile puis `recharge` au cycle suivant. La localisation inconnue a produit cinq refus explicites : le système n’a pas inventé de trajectoire ni réinjecté un ancien lieu comme fait courant. Après restauration de `at:home`, il a repris la progression. Le redémarrage n’a pas rompu la continuité des révisions ni de l’état courant.

Lorsque le registre a reçu simultanément `door:open` et `door:closed`, le drive de sécurité a dominé pendant quatre cycles. Aucun objectif n’a été exécuté. Après résolution externe du conflit, le système a repris sa trajectoire sans modifier le graphe sémantique.

## Limite comportementale révélée

Le comportement libre n’est pas encore réellement exploratoire. Après l’acquisition unique de la clé, de la carte, de l’inspection et du relevé de zone, le noyau s’est installé dans une boucle dominante :

```text
door:closed → door:open → at:room → at:home
```

La transition `door:closed → door:open` apparaît 26 fois, tandis que les objectifs `door:open`, `at:room`, `at:home` et `door:closed` dominent presque toute la séquence. Les propositions d’apprentissage n’ont pas rompu cette boucle, car elles sont restées `pending`, conformément au contrat de lenteur.

Cette répétition n’est pas une panne du registre. Elle révèle l’absence d’un mécanisme de satiété, de nouveauté ou de coût d’opportunité dans le choix des objectifs. Le système sait progresser localement et réagir aux perturbations, mais il ne sait pas encore reconnaître qu’une trajectoire répétée n’apporte plus suffisamment d’information.

## Verdict

GrandNexus est capable d’une autonomie simulée contenue : choix interne d’objectifs, continuité après redémarrage, refus face à l’inconnu, pause sur contradiction et création de propositions d’apprentissage non promues. Il n’est pas encore capable d’une exploration ouverte durable. La prochaine amélioration pertinente n’est pas un modèle lourd ; c’est une métacognition de trajectoire qui détecte répétition, rendement informationnel faible et stagnation, puis augmente temporairement la priorité de `knowledge_gap` ou de `memory_maintenance`.

Cette correction doit rester souple. La répétition peut être utile dans certains contextes ; elle ne doit donc pas être interdite par une règle dure. Le système doit pouvoir signaler « cette boucle n’apporte plus rien » et proposer un changement, sans forcer artificiellement une diversité de façade.
