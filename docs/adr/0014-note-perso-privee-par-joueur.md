# Note perso : un texte perso par joueur, jamais exporté ni fusionné

Quand tu tapes un nom, après la question du style, le CLI propose « Une note ? » (Entrée = passer, `-` = effacer). Le texte (`Joueur.memo`) s'affiche dans `show` et à la rencontre (`Note : …`). Pas de commande `note` dédiée : la question à chaque rencontre suffit.

Différence avec le **style** : le style est court, décoré par mots-clés et partagé entre potes (ADR 0004). La note est privée (« m'a insulté », « joue le soir ») : `export` ne l'écrit pas dans le fichier du pote et l'import ne la lit ni ne la remplace. Compromis : une seule note par joueur, pas d'historique, et pas de partage possible ; voulu pour que personne ne lise le carnet privé d'un autre par accident.
