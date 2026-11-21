# Notes perso exportées et fusionnées, signées comme les traits

Remplace l'ADR 0014. Les notes perso servent aussi aux potes (« joue le soir », « rush à 3 min ») : `export` les écrit maintenant dans le fichier, et `import` les fusionne avec les règles des traits (ADR 0004). Chaque note est signée par son auteur et datée (`memo_maj`). Il y a au plus une note par auteur et par joueur. La note du propriétaire (`memo`) n'est jamais touchée. La note d'un autre auteur (`notes`) est ajoutée, ou remplacée seulement par une version plus récente. Une note effacée chez l'exportateur n'efface rien chez le destinataire. Les notes des autres sont réexportées, comme leurs traits. Un joueur qui n'a qu'une note d'un autre auteur, sans trait, est aussi importé.

Compromis : une note perso n'est plus privée. Elle est lisible par quiconque reçoit le fichier, puis par ceux à qui il le renvoie. Le message d'export le rappelle. Pas d'option pour exclure les notes : ce serait une commande de plus à retenir.

Avec ce changement, `export` sans fichier écrit `<pseudo>.json` sur le Bureau. Un nom seul (chemin relatif) va aussi sur le Bureau ; un chemin complet est utilisé tel quel. `import` ne cherche pas sur le Bureau : on y glisse le fichier reçu, qui donne un chemin complet.
