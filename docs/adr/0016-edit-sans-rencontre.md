# `edit` : changer nom, style et note sans compter de rencontre ; `rename` absorbé

Une partie dure souvent plus de 30 minutes (ADR 0010) : taper le nom au début, puis à la fin pour noter le style, comptait deux rencontres pour un seul adversaire. `edit <nom>` affiche la fiche puis ouvre trois champs pré-remplis (nom, style, note perso) : Entrée garde la valeur, on peut la corriger sur place, la vider efface. Il ne touche ni au compteur ni à la date.

Le renommage (ancien `rename <a> > <b>`) devient la première question d'`edit` : une seule commande pour corriger un joueur, et moins de commandes à retenir. Le refus d'un nom déjà pris (ADR 0011) est inchangé.

Compromis : la fenêtre de 30 minutes reste telle quelle (l'allonger ferait compter deux vraies parties d'affilée pour une). `edit` refuse un joueur absent du carnet : pour en créer un, il faut le croiser. `rename` disparaît tel quel : un script qui l'utilisait ne marcherait plus (c'est un outil interactif).
