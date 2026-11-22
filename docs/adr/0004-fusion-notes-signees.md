# Fusion : notes signées par auteur, celles du propriétaire jamais écrasées

> Remplacé par l'ADR 0022 : un seul trait commun par joueur, avec historique.

Un joueur a au plus une note de style par **auteur** (le pseudo choisi au premier lancement). À l'import, les notes des autres auteurs sont ajoutées, ou remplacées seulement si leur date `maj` est plus récente. Les notes du propriétaire ne sont jamais touchées. Le compteur de rencontres n'est pas fusionné : il ne compte que les parties du propriétaire. Les joueurs du pote sans aucune note d'un autre auteur ne sont pas importés, pour ne pas remplir le carnet de joueurs vides.

## Conséquences

On peut réimporter le même fichier sans risque, ou une version plus récente : la fusion est idempotente. En contrepartie, si deux personnes choisissent le même pseudo, leurs notes se confondent.
