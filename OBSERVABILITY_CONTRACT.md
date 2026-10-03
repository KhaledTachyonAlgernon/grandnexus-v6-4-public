# Contrat d’observabilité GrandNexus

Chaque cycle cognitif produit une trace structurée et chronologique. La trace doit être lisible sans exposer de secrets ni permettre de déclencher une action.

| Champ | Règle |
|---|---|
| `event_id` | Identifiant unique de l’événement |
| `cycle_id` | Identifiant du cycle cognitif |
| `stage` | `perception`, `validation`, `retrieval`, `proof`, `planning`, `simulation`, `metacognition` ou `learning` |
| `event_type` | Événement précis, par exemple `knowledge_rejected` ou `plan_accepted` |
| `status` | `accepted`, `rejected`, `completed`, `failed` ou `pending` |
| `confidence` | Confiance explicitement bornée entre 0 et 1 |
| `provenance` | Sources ou identifiants de preuve |
| `payload` | Données non sensibles et sérialisables |
| `created_at` | Horodatage UTC |

Une trace doit permettre de répondre à quatre questions : ce qui a été perçu, ce qui a été considéré comme connaissance, pourquoi une conclusion ou un plan a été accepté ou refusé, et ce que la simulation a réellement produit. Les événements sont append-only dans le MVP. L’observabilité ne modifie jamais la mémoire, les règles ou les actions.
