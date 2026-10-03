# Contrat d’identité et d’autonomie de GrandNexus

## Principe central

GrandNexus est une architecture cognitive modulaire. Il n’est pas un wrapper autour d’un LLM. Le LLM est un module optionnel de proposition, au même titre qu’un capteur, un ranker ou un moteur spécialisé.

L’identité opérationnelle de GrandNexus réside dans la continuité de son noyau : mémoire hiérarchique, graphe sémantique, statuts épistémiques, raisonnement symbolique, planification simulée, métacognition, réputation des sources, évaporation, promotion lente et sécurité.

## Autorité des composants

| Composant | Rôle | Autorité de vérité | Autorité d’action |
|---|---|---:|---:|
| Mémoire et graphe | Conserver et relier l’état | Conditionnelle et versionnée | Aucune |
| Raisonneur symbolique | Déduire et vérifier | Limitée aux règles et preuves | Aucune |
| Planificateur | Explorer des plans | Aucune | Simulation seulement |
| Métacognition | Évaluer limites et incertitude | Aucune | Aucune |
| LLM | Proposer, reformuler, explorer | Aucune | Aucune |
| Vérificateur | Contrôler cohérence et provenance | Portail de décision | Refus de sécurité possible |
| Noyau GrandNexus | Orchestrer et arbitrer les contrats | Décision épistémique finale | Action seulement via politique dédiée |

## Tests d’autonomie obligatoires

Un module LLM ne peut être considéré comme intégré que si GrandNexus produit encore un résultat cohérent lorsque le LLM est absent, indisponible, lent, malformé ou en désaccord avec le noyau. Une défaillance LLM doit dégrader la richesse de la proposition, pas détruire l’identité du système.

Le LLM ne peut ni modifier le graphe stable, ni promouvoir une hypothèse, ni choisir une action réelle. Toute proposition externe entre comme hypothèse, conserve sa provenance et peut s’évaporer.

## Critère de non-dépendance

```text
GrandNexus noyau seul → fonctionnement déterministe minimal
GrandNexus + LLM → exploration enrichie
LLM absent ou erroné → repli propre vers le noyau
LLM en désaccord → désaccord conservé et soumis au vérificateur
```

La réussite ne se mesure donc pas au nombre de décisions prises par le LLM, mais à la capacité de GrandNexus à rester lui-même avec ou sans ce module.
