# `show` affiche le rang des trois dernières saisons

`show <nom>` donne une ligne par saison (en cours + 2 précédentes) avec le rang 1v1 et 2v2. La saison en cours vient du classement déjà chargé ; les saisons passées sont téléchargées à la demande, au premier `show`, puis gardées dans `saison-N.json` du dossier de cache. Une saison finie ne change plus, ce cache ne s'invalide jamais. Taper un nom (rencontre) garde la fiche courte.

Compromis : le premier `show` d'un joueur peut prendre quelques secondes (4 appels réseau) ; hors ligne sans cache, la ligne dit « indisponible » au lieu de bloquer. Choisi plutôt que de tout précharger au démarrage, qui ralentirait chaque lancement.
