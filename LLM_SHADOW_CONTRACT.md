# Contrat LLMBridge–ShadowCycle

Le `LLMBridge` est un proposeur. Il peut produire une hypothèse structurée, une relation candidate ou une suggestion de plan. Il ne peut pas écrire dans le graphe stable, changer un statut `validated`, supprimer une contradiction ou déclencher une action.

| Étape | Branche stable | Branche shadow |
|---|---|---|
| Proposition LLM | Référence inchangée | Reçue comme `hypothesis` |
| Vérification | Lecture seule | Comparaison au graphe copié |
| Raisonnement | Faits validés seulement | Hypothèses explicitement marquées |
| Simulation | Référence | Autorisée dans le sandbox |
| Apprentissage | Aucun effet immédiat | Proposition versionnée possible |
| Fusion | Jamais implicite | Décision explicite après comparaison |

Une proposition est évaluée selon sa conformité structurée, sa provenance, son support dans le graphe, ses contradictions, son utilité dans la simulation et son absence de régression. Une meilleure plausibilité LLM ne suffit jamais à justifier une promotion.

Le résultat doit être l’un de `candidate_only`, `supported_hypothesis`, `contradicted`, `rejected` ou `pending_review`. Les connaissances validées et les actions restent hors de portée du LLM.
