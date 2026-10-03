# Roadmap de maturation GrandNexus v6.4

## Position de départ

La version initiale fournit une vision architecturale très ambitieuse : noyau d’orchestration, mémoires multiples, perception, raisonnement, apprentissage, métacognition, évolution, planification, multi-agent, sécurité, simulation, capteurs, actionneurs, graphes et services distribués. Le travail déjà réalisé démontre un profil léger cohérent, mais il ne faut pas noter la présence de classes comme si elle constituait déjà une capacité validée.

La stratégie consiste donc à conserver cette version initiale comme **architecture cible**, tout en construisant une série de paliers prouvés. Chaque palier doit augmenter la note parce qu’il apporte une capacité observable, un test reproductible et un contrat d’interface stable.

## Cible de notation

| Niveau | Note indicative | Ce qui est démontré |
|---|---:|---|
| Checkpoint actuel | 12/20 | Architecture riche, profil léger fonctionnel, pipeline déterministe, persistance et premiers profils optionnels |
| MVP cognitif solide | 14/20 | Mémoire réellement interrogeable, raisonnement symbolique utile, scénarios comportementaux et tests d’erreur |
| Prototype cognitif avancé | 16/20 | Apprentissage mesurable, métacognition, objectifs persistants et amélioration sur jeux de tâches |
| Système expérimental intégré | 17–18/20 | Multi-agent, sécurité, observabilité, simulation et déploiement distribué validés |
| 19–20/20 | Non prioritaire | Nécessiterait des résultats comparatifs externes, une robustesse élevée et une démonstration scientifique de l’émergence |

## Priorités recommandées

### 1. Transformer les mémoires en capacités observables

La prochaine amélioration à fort rendement est de donner aux mémoires des opérations réellement utiles : insertion, recherche, consolidation, oubli contrôlé, association et restauration après redémarrage. Il faut mesurer la précision du rappel, la latence et le comportement lorsque plusieurs souvenirs sont contradictoires.

**Gain attendu : +1 à +1,5 point.**

### 2. Remplacer le raisonnement de démonstration par des tâches vérifiables

Le raisonnement doit traiter un petit jeu de problèmes déterministes : déduction de règles, résolution de contraintes, planification d’étapes, détection de contradiction et justification de conclusion. Chaque réponse doit comporter les prémisses, les étapes, la confiance et les raisons d’échec.

**Gain attendu : +1,5 à +2 points.**

### 3. Ajouter une métacognition opérationnelle

Les modules de métacognition de la version initiale doivent surveiller l’incertitude, détecter les erreurs, comparer la confiance annoncée à la réussite réelle et déclencher une demande de clarification ou un second passage. Une métrique de calibration est plus importante qu’un simple nom de classe : une confiance de 0,8 doit correspondre approximativement à une réussite de 80 % sur un jeu de tests.

**Gain attendu : +1 à +1,5 point.**

### 4. Introduire l’apprentissage avec une mesure avant/après

Il faut choisir un environnement réduit et mesurer le système avant apprentissage, après apprentissage et après perturbation. Le premier objectif ne devrait pas être l’auto-amélioration générale, mais l’apprentissage d’une compétence circonscrite : classer des entrées, mémoriser des règles ou améliorer une stratégie de planification.

**Gain attendu : +1 à +2 points.**

### 5. Reconnecter les inspirations de la version 0.9 sans créer de dépendance confuse

Les concepts de `MetaCognition`, `ProblemSolver`, `CodeIntegrator`, `DriveModule` et `LLMBridge` peuvent devenir des adaptateurs autour des contrats v6.4. Ils ne doivent pas être copiés directement dans le noyau. Chaque adaptateur doit déclarer ses entrées, sorties, coûts, risques et conditions d’activation.

**Gain attendu : +0,5 à +1 point.**

### 6. Valider la coopération multi-agent

Le coordinateur multi-agent doit être testé avec plusieurs agents spécialisés : perception, planification, vérification et critique. La démonstration doit comparer un agent seul et le groupe, mesurer le gain réel, détecter les désaccords et empêcher une décision dangereuse sans validation.

**Gain attendu : +1 à +1,5 point.**

### 7. Rendre la sécurité et les limites vérifiables

Le module de sécurité doit bloquer les actions interdites, journaliser la décision, différencier une erreur de permission d’une erreur technique et fournir un mode simulation. Cette étape est indispensable avant les actionneurs, les connecteurs externes ou l’auto-modification.

**Gain attendu : +1 point en robustesse, mais surtout réduction du risque.**

### 8. Prouver le déploiement distribué au lieu de seulement le déclarer

Les services graphes, capteurs, actionneurs, simulation et fédération doivent rester optionnels jusqu’à ce qu’un scénario de bout en bout soit reproductible. Il faudra un fichier de configuration, des health checks, des timeouts, une reprise après panne et une observation centralisée.

**Gain attendu : +1 à +2 points.**

## Ordre d’exécution conseillé

| Sprint | Livrable | Critère de sortie |
|---|---|---|
| A | Mémoire interrogeable et consolidation | Rappel correct sur un jeu de souvenirs connu |
| B | Raisonnement symbolique vérifiable | Conclusions accompagnées de prémisses et étapes |
| C | Métacognition et calibration | Confiance mesurée et amélioration après erreur |
| D | Apprentissage ciblé | Score avant/après statistiquement meilleur |
| E | Adaptateurs v0.9 | Interfaces v6.4 conservées, activation optionnelle |
| F | Multi-agent et sécurité | Coopération utile, conflits tracés, actions contrôlées |
| G | Simulation et distribution | Redémarrage et panne partielle gérés |

## Ce qu’il faut éviter

Il ne faut pas augmenter la note en ajoutant encore des classes, des imports ou des services sans scénario de validation. Il faut éviter de brancher directement un LLM externe au cœur, de charger toutes les dépendances au démarrage, de confondre une sortie plausible avec une conclusion prouvée et de déclarer l’émergence avant d’avoir défini des mesures observables.

La trajectoire la plus crédible est **12 → 14 → 16 → 18**, avec des preuves à chaque palier. Le meilleur investissement immédiat est un banc d’évaluation contenant des tâches de mémoire, de raisonnement, de planification et de correction d’erreur, exécutables à chaque modification.
