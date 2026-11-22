# Trait et note communs, avec historique : la version la plus récente l'emporte

Remplace les ADR 0004 et 0021. Un joueur n'a plus un trait et une note **par auteur** : il a **un** trait et **une** note, communs à tous ceux qui s'échangent le carnet. Paul peut modifier la note que j'ai écrite, et inversement. Chaque modification ajoute une **version** (texte, auteur, date) à l'**historique** du champ. Effacer (« - ») ajoute une version vide. La version actuelle est la plus récente. Une modification locale passe toujours devant la dernière version connue, même si une version importée est datée du futur (horloge décalée).

À l'import, les versions inconnues rejoignent l'historique, sans doublon, et la plus récente devient la version actuelle. Un effacement plus récent se propage. Il y a une **différence** quand la version actuelle de l'autre est nouvelle pour moi et que sa valeur diffère de la mienne. C'est un **conflit** si, en plus, ma version n'est pas dans son historique : chacun a modifié de son côté. Sinon, c'est une avance rapide, comme dans Git (il a remplacé ma version).

L'import affiche toujours un aperçu, puis demande confirmation avec la **stratégie** en cours entre parenthèses : « Importer (la plus récente gagne) ? ». Entrée importe, `c` change de stratégie, `n` annule. Une option donne la stratégie de départ (`import paul.json --mine`). Sans terminal, on importe avec la stratégie de départ. Chaque stratégie s'applique à toutes les différences, pas seulement aux conflits :

- `--latest` : la plus récente gagne (par défaut) ;
- `--keep-deleted` : la plus récente, mais une suppression venue de l'autre ne fait rien disparaître ;
- `--mine`, `--theirs` : toujours la mienne, ou toujours la sienne ;
- `--merge` : fusionner (mots-clés réunis, ou notes « a / b ») ;
- `--ask` : un par un, avec `1` = la mienne, `2` = la sienne, `f` = fusionner, et Entrée = la plus récente.

Un choix différent de la plus récente est enregistré comme une nouvelle version, signée par moi et datée de maintenant. L'autre la reçoit à son prochain import sans conflit : le modèle reste « la plus récente l'emporte ». `show` et `edit` affichent les 10 dernières versions remplacées. La rencontre et `list` n'affichent que la version actuelle.

Les rencontres restent séparées par personne (`encountered_by`). Les miennes ne sont jamais modifiées par un import. Pour celles des autres, on garde la plus récente. Elles s'affichent seulement dans `show`. Un joueur sans trait ni note n'est toujours pas importé.

## Options écartées

- **Un trait et une note par auteur** (ADR 0004 et 0021) : on ne pouvait pas corriger la note d'un pote. Un même joueur affichait aussi plusieurs traits contradictoires.
- **Écraser sans historique** : une note supprimée ou remplacée par erreur était perdue.
- **Poser une question par conflit à chaque import** : trop de questions pour un cas rare. La confirmation unique, avec une stratégie par défaut, suffit, et `--ask` reste possible.
- **Appliquer `--mine` / `--theirs` aux seuls conflits** : `--mine` doit pouvoir garder ma note même quand l'autre l'a remplacée (avance rapide). Sinon l'option ne sert presque jamais.

## Conséquences

La règle « les notes du propriétaire ne sont jamais écrasées par un import » devient « un import ne perd jamais rien : toute version reste dans l'historique ». L'historique grandit sans limite dans le fichier, ce qui reste négligeable pour quelques centaines de joueurs. Deux personnes avec le même pseudo se confondent toujours.
