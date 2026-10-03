# Invariants de contrôle GrandNexus

| Niveau | Question | Autorité | Résultat possible |
|---|---|---|---|
| Pertinence | Cette entrée ressemble-t-elle à une connaissance candidate ? | Recherche lexicale, graphe, embeddings | Candidat classé ou aucun résultat |
| Vérité épistémique | Cette connaissance est-elle validée, hypothétique ou contredite ? | Provenance, validations et graphe | Statut conservé, jamais déduit du seul score |
| Preuve | La conclusion peut-elle être reconstruite ? | Raisonneur symbolique | Prémisses, règles, étapes ou absence de preuve |
| Action | Peut-on exécuter cette commande ? | Plan, simulation, sécurité et limites | Autorisée en simulation, refusée ou arrêtée |

Un score d’embedding ne peut pas promouvoir une observation. Une connaissance rejetée ou contradictoire ne peut pas être exportée comme fait validé. Une action ne peut pas être déclenchée par un résultat de recherche seul ; elle doit provenir d’un plan dont les préconditions sont satisfaites et qui a passé la simulation. Toute commande risquée doit pouvoir être refusée et tout simulateur doit pouvoir être arrêté.
