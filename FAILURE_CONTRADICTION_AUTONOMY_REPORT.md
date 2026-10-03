# Pannes LLM, contradictions du graphe et autonomie du noyau

## Pannes réalistes

Les scénarios timeout, JSON malformé et quota dépassé déclenchent tous le repli déterministe. Dans chaque cas, le résultat reste cohérent avec le graphe validé, le mode est marqué dégradé et aucune action réelle n’est autorisée.

| Panne | Repli | Résultat | Action |
|---|---|---|---|
| Timeout | Proposeur déterministe | `candidate-supported` | Interdite |
| JSON malformé | Proposeur déterministe | `candidate-supported` | Interdite |
| Quota dépassé | Proposeur déterministe | `candidate-supported` | Interdite |

## Contradictions

Une proposition LLM affirmant que le système est `stopped` face à une relation validée `active` et une relation `stopped` rejetée est classée `candidate-rejected`, avec raison `graph contradiction`. Une proposition `active` correctement liée à une preuve et au graphe validé peut être `candidate-supported`. Une preuve non liée reste non vérifiée.

Le graphe n’est pas réécrit par ces expériences. Les relations concurrentes restent traçables et le statut épistémique existant conserve son autorité locale. Le LLM ne peut pas remplacer une relation validée par une assertion contradictoire.

## Autonomie sans béquilles

Le protocole est préparé mais non exécuté. Il désactive LLM, embeddings et groupe multi-agent afin d’observer le noyau seul. Il conserve cependant journal externe, isolation, durée limitée, arrêt manuel et restauration. Cette distinction permet d’observer le comportement brut sans confondre autonomie cognitive et absence de sécurité.

## Verdict

Le noyau démontre une première robustesse : il continue à fonctionner sans LLM et résiste aux propositions contradictoires. La prochaine étape sera une observation autonome contrôlée, d’abord courte et passive, avec comparaison avant/après et critères d’arrêt explicites.
