# Contrat du ShadowCycle local

`ShadowCycle` exécute une proposition expérimentale sur une copie isolée de l’état stable. La branche candidate peut modifier sa propre mémoire, son graphe et ses préférences temporaires, mais ne peut pas écrire dans l’état stable.

| Élément | Branche stable | Branche shadow |
|---|---|---|
| Graphe | Lecture et référence | Copie modifiable |
| Connaissances | Version active | Version candidate |
| LLM | Peut proposer | Peut proposer et être observé |
| Simulation | Référence | Expérimentation |
| Traces | Immuables | Comparées à la référence |
| Fusion | Non automatique | Seulement après décision explicite |

Une proposition candidate doit produire une trace complète, un état final, les contradictions détectées, les erreurs, le coût, le risque et la comparaison aux cas de référence. Le shadowing ne constitue pas une validation : il mesure le comportement d’une branche.

La fusion est refusée si la branche candidate crée une contradiction validée, dégrade un cas de référence, augmente le risque sans bénéfice démontré ou modifie l’état stable sans autorisation. L’abandon de la branche doit supprimer ou isoler son état temporaire.
