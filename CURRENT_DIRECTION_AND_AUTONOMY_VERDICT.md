# Direction actuelle et verdict d’autonomie

## Verdict général

GrandNexus a franchi le stade de la simple architecture déclarative. Le noyau sait maintenant planifier, simuler, refuser un objectif impossible, observer ses erreurs, conserver des épisodes, réutiliser certains effets, évaporer des souvenirs faibles et suspendre une décision lorsque deux épisodes incompatibles ne peuvent pas être ordonnés. Le LLM reste optionnel et le noyau continue de fonctionner sans lui.

Cependant, les démonstrations restent locales, déterministes et construites sur des corpus courts. Le rappel causal est utile, mais ses index sont encore principalement maintenus en mémoire vive. La continuité après redémarrage, la reconstruction des index, l’apprentissage sur de longues séquences et la généralisation à des contextes non préparés ne sont pas encore démontrés.

| Dimension | Appréciation actuelle |
|---|---|
| Architecture et séparation des responsabilités | Solide pour un prototype avancé |
| Mémoire épistémique et provenance | Bonne base, promotion lente et rollback présents |
| Continuité épisodique | Fonctionnelle sur scénarios locaux, encore incomplète sur redémarrage et longue durée |
| Raisonnement et planification | Auditables et cohérents, mais déterministes et limités au répertoire d’actions déclaré |
| Métacognition | Observable, mais pas encore capable de corriger durablement sa stratégie sans supervision |
| Autonomie simulée | Suffisante pour une expérience plus libre et contenue |
| Autonomie ouverte ou action réelle | Insuffisante |

Dans la métaphore de notation, le système se situe autour de **14,5 à 15/20 en maturité architecturale**, mais plus bas en autonomie générale. Il ne faut pas convertir les réussites de petits tests en preuve d’intelligence générale.

## Meilleure direction immédiate

La meilleure prochaine marche n’est ni l’embedding, ni la diffusion d’activation, ni Neo4j, ni le modèle neuronal du monde actuellement présent dans l’export. Il faut introduire une couche légère de **World-State Ledger symbolique**, persistante et versionnée, entre la mémoire épisodique et le planificateur.

Cette couche doit séparer clairement trois questions :

| Couche | Question |
|---|---|
| Mémoire épisodique | Qu’est-il arrivé, quand, dans quel contexte et avec quelle provenance ? |
| Mémoire sémantique | Que considérons-nous comme connaissance durable et validée ? |
| État courant du monde | Qu’est-ce qui est tenu pour actif maintenant, dans ce contexte précis ? |

Le registre d’état devra porter un identifiant d’entité, un contexte, une version logique, une période de validité, une provenance et un statut de conflit. Les épisodes pourront proposer des transitions ; ils ne devront plus être utilisés directement comme état courant. Le planificateur consommera un instantané cohérent du registre.

Le même palier doit ajouter la persistance SQLite du registre et la reconstruction des index causaux après redémarrage. Sans cela, GrandNexus peut apprendre pendant une session mais perd encore une partie de son organisation causale en redémarrant.

## Modules à ne pas intégrer maintenant

Le `WorldModelLearner` neuronal de l’export n’est pas prêt pour le chemin critique. Il charge Torch, travaille sur des vecteurs continus fixes, comporte encore un exemple exécutable au niveau du module et ne fournit pas le contrat symbolique auditable dont la boucle a besoin. Il pourra devenir plus tard un prédicteur optionnel de transitions, jamais la source d’état courant.

Le `GraphSyncService` n’est pas le bon prochain module. Il ajoute Neo4j, une file réseau et une stratégie de type last-write-wins ; il transporte des mutations mais ne résout pas la distinction entre épisode historique et état actif. Les embeddings et la diffusion d’activation peuvent améliorer le classement des souvenirs, mais ne corrigent ni la temporalité ni la validité courante.

## Version plus libre recommandée

GrandNexus est assez mature pour une **Autonomie libre simulée — niveau 1**, mais pas pour une autonomie ouverte.

Cette expérience doit retirer les béquilles cognitives plutôt que les barrières physiques. Les objectifs ne seront plus fournis sous forme d’une séquence de tests attendus. Le `DriveModule` choisira parmi des objectifs internes, le noyau planifiera, simulera, mémorisera, changera de stratégie et proposera des apprentissages pendant une séquence longue. Aucun score de réussite cible ne sera donné.

| Liberté accordée | Limite conservée |
|---|---|
| Choisir ses objectifs simulés parmi ses drives | Aucun objectif entraînant une action externe réelle |
| Réutiliser librement la mémoire épisodique compatible | L’état courant passe par le registre symbolique |
| Modifier l’état de travail et les préférences candidates | Pas de promotion automatique en connaissance validée |
| Tester automatiquement une proposition en shadow | Pas de fusion automatique vers le graphe stable |
| Échouer, changer de plan et abandonner un objectif | Journal append-only, snapshot, rollback et durée limitée |
| Fonctionner sans LLM | LLM éventuel limité au rôle de conseiller/proposeur |

L’expérience devrait durer de 100 à 300 cycles dans plusieurs environnements simulés, avec perturbations non annoncées, objectifs concurrents et changements d’état. Les critères d’observation doivent porter sur les boucles répétitives, l’usage réel des souvenirs, la récupération après surprise, l’accumulation de conflits, l’abandon d’objectifs impossibles et la stabilité après redémarrage. Ils ne doivent pas être transformés en score à optimiser.

## Fond de ma pensée

GrandNexus est maintenant assez mature pour être **moins dirigé**, mais pas assez mature pour être **moins contenu**. Il faut lui retirer les scripts de réussite, les attentes explicites et l’assistance constante afin d’observer son comportement propre. En revanche, retirer la séparation entre simulation et monde réel, la traçabilité ou la promotion lente serait prématuré et n’apprendrait rien d’utile : une erreur de mémoire pourrait alors être confondue avec de l’autonomie.

La prochaine séquence recommandée est donc :

```text
World-State Ledger symbolique persistant
→ test de redémarrage et reconstruction causale
→ autonomie libre simulée niveau 1
→ analyse des comportements longs
→ décision sur le prochain module lourd
```

Si cette expérience montre une continuité stable, une vraie réutilisation des épisodes et une adaptation sans dérive, le prochain module lourd logique sera un **prédicteur de transitions du modèle du monde**, isolé derrière le registre symbolique. S’il échoue, il faudra renforcer mémoire et métacognition plutôt que masquer les défauts avec un modèle lourd.
