# Glossaire

Vocabulaire du domaine, utilisé tel quel dans le code (`src/superselection/`).

- **Adversaire / Joueur** (`Joueur`) : un joueur de War Selection croisé en partie, identifié
  par son nom en jeu. Deux noms identiques à la casse près désignent le même joueur
  (`pizza` = `Pizza`), mais `[IMP] Pizza` et `Pizza` sont deux joueurs différents.
- **Carnet** (`Carnet`) : l'ensemble des joueurs connus du propriétaire, enregistré dans
  `carnet.json`. Le carnet a un **auteur** : le pseudo du propriétaire.
- **Rencontre** : le fait de taper le nom d'un joueur (commande `croiser`). Ça incrémente
  son compteur et met à jour la date de la dernière rencontre. Le compteur ne compte que
  les rencontres du propriétaire du carnet, jamais celles d'un pote.
- **Style** (`Note`) : texte libre court qui décrit la façon de jouer d'un joueur (« agressif,
  rush archers »). Un joueur a au plus un style par **auteur**.
- **Classement** (`Classement`) : le top 100 officiel d'une **saison**, en 1v1 et en 2v2, lu sur
  `https://ratings.warselect.io/webapi/top100{1v1|2v2}?season=N` (source de ws-stats.pl).
  En 2v2 le rang est individuel : les deux coéquipiers ont les mêmes points.
- **Rang** (`Rang`) : la position (1 à 100) et les points d'un joueur dans un mode.
  « Hors top 100 » veut dire absent du classement, pas « inconnu ».
- **Saison** : numéro croissant (29 en novembre 2026). La saison en cours est la dernière
  qui a des joueurs classés en 1v1 ; elle est détectée automatiquement.
- **Export / Import (fusion)** : l'export écrit le carnet dans un fichier pour un pote ;
  l'import fusionne le carnet d'un pote dans le sien. La fusion ajoute les joueurs qui ont
  au moins un style d'un autre auteur, ajoute ou met à jour les styles des autres auteurs
  (seulement si leur version est plus récente) et ne touche jamais aux styles du propriétaire.
