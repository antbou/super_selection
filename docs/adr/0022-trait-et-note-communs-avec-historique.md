# Trait et note communs, avec historique : la version la plus récente l'emporte

Remplace les ADR 0004 et 0021. Un joueur n'a plus un trait et une note **par auteur** : il a **un** trait et **une** note, communs à tous ceux qui s'échangent le carnet. Paul peut modifier la note que j'ai écrite, et inversement. Chaque modification ajoute une **version** (texte, auteur, date) à l'**historique** du champ. Effacer (« - ») ajoute une version vide. La version actuelle est la plus récente. Une modification locale passe toujours devant la dernière version connue, même si une version importée est datée du futur (horloge décalée).

À l'import, les versions inconnues rejoignent l'historique, sans doublon, et la plus récente devient la version actuelle. Un effacement plus récent se propage. Il y a **conflit** quand chacun a modifié de son côté : sa version actuelle n'est pas dans mon historique, la mienne n'est pas dans le sien, et elles diffèrent. Si l'un a déjà vu la version de l'autre, c'est une avance rapide, comme dans Git, et il n'y a pas de question. S'il y a des conflits, l'import pose une seule question :

- Entrée : la plus récente gagne (par défaut, et sans terminal) ;
- `s` : la plus récente, mais une suppression venue de l'autre ne fait rien disparaître ;
- `u` : un par un, avec `1` = la mienne, `2` = la sienne, `f` = fusionner (mots-clés réunis, ou notes « a / b »), et Entrée = la plus récente.

Un choix différent de la plus récente est enregistré comme une nouvelle version, signée par moi et datée de maintenant. L'autre la reçoit à son prochain import sans conflit : le modèle reste « la plus récente l'emporte ». `show` et `edit` affichent les 10 dernières versions remplacées. La rencontre et `list` n'affichent que la version actuelle.

Les rencontres restent séparées par personne (`encountered_by`). Les miennes ne sont jamais modifiées par un import. Pour celles des autres, on garde la plus récente. Elles s'affichent seulement dans `show`. Un joueur sans trait ni note n'est toujours pas importé.

## Options écartées

- **Un trait et une note par auteur** (ADR 0004 et 0021) : on ne pouvait pas corriger la note d'un pote. Un même joueur affichait aussi plusieurs traits contradictoires.
- **Écraser sans historique** : une note supprimée ou remplacée par erreur était perdue.
- **Toujours demander en cas de conflit**, ou proposer des stratégies globales (« toutes les miennes », « toutes les siennes ») : trop de questions pour un cas rare. Le choix un par un couvre ces cas.

## Conséquences

La règle « les notes du propriétaire ne sont jamais écrasées par un import » devient « un import ne perd jamais rien : toute version reste dans l'historique ». L'historique grandit sans limite dans le fichier, ce qui reste négligeable pour quelques centaines de joueurs. Deux personnes avec le même pseudo se confondent toujours.
