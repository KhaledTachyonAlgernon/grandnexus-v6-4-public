# Métacognition de trajectoire — palier consultatif

## Objectif

Cette étape répond au comportement observé dans l’autonomie libre initiale : après avoir produit les effets nouveaux disponibles, GrandNexus répétait une boucle `door:closed → door:open → at:room → at:home` sans reconnaître explicitement que son rendement informationnel devenait faible.

Le correctif introduit `TrajectoryMetacognition`, un observateur local et déterministe. Il ne modifie aucun fait, ne décide aucune vérité, ne promulgue aucune interdiction et n’active aucun module lourd. Il observe seulement les objectifs effectivement exécutés, les faits déjà vus et les effets actuellement candidats.

## Signaux employés

| Signal | Rôle |
|---|---|
| Motif récent répété | Détecte la répétition contiguë d’une séquence de deux à trois objectifs |
| Nombre de répétitions | Exige au moins trois occurrences avant de signaler une stagnation |
| Nouveauté disponible | Mesure la proportion d’effets atteignables mais encore non observés |
| Pause réflexive | Produit un cycle `trajectory_review`, une proposition `pending` et un cooldown temporaire |

La condition de stagnation est volontairement restrictive : une répétition ne suffit pas. Il faut une répétition stable et l’absence d’effet atteignable encore inédit. Une boucle peut donc rester exécutée lorsqu’elle demeure utile, nécessaire ou lorsqu’une occasion nouvelle apparaît.

## Intégration

La métacognition émet le drive `trajectory_review`. Ce drive est consultatif et temporaire. Lorsque ce drive domine, GrandNexus ne planifie pas une action de monde ; il journalise la trajectoire répétée, crée éventuellement une proposition d’apprentissage `pending`, puis rend la main à la sélection normale des drives après un cooldown de quatre cycles.

> **La pause réflexive ne constitue pas un bannissement de la répétition. Elle rend la répétition visible et laisse au noyau la possibilité de reprendre si aucune alternative réelle n’est disponible.**

## Résultats de la campagne multi-environnements

| Environnement simulé | Cycles acceptés | Revues de trajectoire | Fait nouveau acquis | Pauses de sécurité | Graphe stable |
|---|---:|---:|---|---:|---|
| Répétition seule | 41/48 | 7 | Aucun attendu | 0 | Inchangé |
| Nouvelle occasion au cycle 25 | 43/48 | 5 | `beacon:surveyed` | 0 | Inchangé |
| Conflit d’état temporaire | 39/48 | 5 | Aucun attendu | 4 | Inchangé |

Dans l’environnement de répétition seule, la première revue est apparue au cycle 15. Le système a ensuite repris des actions, ce qui confirme que le mécanisme ne bloque pas définitivement le comportement. Dans l’environnement où `beacon:visible` est ajouté au cycle 25, le système atteint `beacon:surveyed` malgré les pauses réflexives : la nouveauté réelle suspend donc naturellement le diagnostic de stagnation. Dans l’environnement de conflit, le `WorldStateLedger` conserve sa priorité : quatre cycles sont mis en pause avec `verification_first`, puis l’autonomie reprend après résolution externe.

Toutes les propositions d’apprentissage issues des revues sont restées `pending`. Aucune connaissance n’a été promue automatiquement, aucun graphe stable n’a été modifié et aucune action externe n’a été autorisée.

## Limite révélée

Ce palier améliore l’auto-observation, pas encore l’auto-réorientation. GrandNexus peut désormais dire implicitement : « je répète une trajectoire sans effet nouveau ». Il ne sait pas encore sélectionner une stratégie de recherche ou générer une hypothèse de cause de cette stagnation. Les cycles de revue repartent donc parfois vers la même boucle lorsque l’environnement ne contient aucune autre affordance symbolique.

La prochaine direction ne doit pas être un LLM ni un mécanisme d’exploration aléatoire. La suite cohérente est un **ProblemSolver orienté lacunes** : à partir d’une revue de trajectoire, identifier les préconditions non satisfaites ou les états non observés, puis proposer en shadow un objectif de vérification ou une expérience symbolique. Ce module devra rester séparé de la décision : il proposera des pistes, que le planificateur et le registre d’état devront juger faisables et sûres.
