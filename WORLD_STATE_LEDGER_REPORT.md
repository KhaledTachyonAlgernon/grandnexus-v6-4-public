# WorldStateLedger — registre symbolique de l’état courant

## Rôle architectural

Le `WorldStateLedger` sépare désormais l’état actif de deux autres couches : la mémoire épisodique conserve ce qui est arrivé, tandis que la mémoire sémantique conserve ce qui est durablement validé. Le registre représente uniquement ce qui est tenu pour actif dans un contexte donné au moment de la planification.

## Implémentation

Le registre repose sur SQLite et conserve un journal append-only de transitions, une vue matérialisée de l’état courant, les révisions, la provenance, l’épisode source et les conflits non résolus. Une transition contient des faits ajoutés et supprimés. Un rollback crée une transition compensatoire ; il n’efface pas l’historique.

| Capacité | État |
|---|---|
| Persistance SQLite | Validée |
| Révisions logiques | Validées |
| Provenance et épisode source | Conservés |
| Reconstruction après redémarrage | Validée |
| Rollback compensatoire | Validé |
| États incompatibles | Exclus de l’instantané actif et journalisés comme conflit |
| Mutation du graphe sémantique | Aucune |
| Promotion automatique | Aucune |

## Intégration à la boucle

Au premier cycle d’un contexte, les faits validés du graphe amorcent le registre. Le planificateur consomme ensuite l’instantané non conflictuel du registre. Une simulation réussie produit un épisode, puis une transition versionnée dans le registre. Les simulations échouées et les simples propositions n’altèrent pas l’état courant.

Le rappel épisodique reste consulté pour audit et préparation, mais il ne constitue plus directement l’état autoritaire lorsque le registre est actif. Cette séparation évite de confondre un souvenir historique avec une situation actuelle.

## Tests réalisés

Le test direct ajoute `door:open`, applique ensuite la transition `door:open → door:closed`, ferme la base, la recharge et retrouve l’état fermé ainsi que la même révision. Un rollback compensatoire restaure ensuite l’état ouvert. L’ajout ambigu de l’état fermé sans retrait explicite de l’état ouvert crée un conflit ; aucun des deux faits incompatibles n’est exposé comme état actif.

Le test de continuité exécute `find_token → has:token`, ferme le registre, reconstruit une nouvelle boucle sans l’action `find_token`, puis atteint `gate:open` grâce à l’état `has:token` restauré après redémarrage. Le plan exécute uniquement `open_gate`.

Les non-régressions de mémoire épisodique, rappel causal, conflits, boucle intégrée et autonomie du noyau passent.

## Limites

Le registre d’incompatibilités est encore explicite et limité. Les contextes sont identifiés par chaîne ; l’identité d’entité, la portée temporelle et la fusion distribuée ne sont pas encore formalisées. Le registre ne doit pas être synchronisé vers Neo4j ni contrôlé par le modèle neuronal du monde à ce stade.

## Verdict

Le registre remplit les prérequis immédiats d’une première autonomie libre simulée : état courant persistant, redémarrage, transitions auditables, conflits visibles et rollback. La prochaine expérimentation peut être moins dirigée tout en restant contenue, sans confondre mémoire historique, connaissance durable et état actif.
