# Glossaire

Vocabulaire du domaine, utilisé tel quel dans le code (`src/superselection/`).

- **Adversaire / Joueur** (`Joueur`) : un joueur de War Selection croisé en partie, identifié
  par son nom en jeu. Deux noms identiques à la casse près désignent le même joueur
  (`pizza` = `Pizza`), mais `[IMP] Pizza` et `Pizza` sont deux joueurs différents.
- **Carnet** (`Carnet`) : l'ensemble des joueurs connus du propriétaire, enregistré dans
  `notebook.json` (format 2, champs en anglais, ADR 0023 ; l'ancien `carnet.json` est converti).
  Le carnet a un **auteur** (`owner` dans le fichier) : le pseudo du propriétaire, qui signe ses versions.
- **Rencontre** : le fait de saisir le nom d'un joueur (directement, ou avec `player <nom>`). Ça incrémente
  son compteur et met à jour la date et l'heure de la dernière rencontre, sauf si la précédente date de moins de 30 minutes (ADR 0010). Le compteur
  (`Joueur.rencontres`) ne compte que les rencontres du propriétaire. Celles des autres (`Joueur.autres_rencontres`,
  `encountered_by` dans le fichier) sont importées à leur nom et affichées seulement dans `show`.
- **Edit** (`edit`) : changer le nom, le trait et la note perso d'un joueur déjà croisé sans compter de rencontre (ADR 0016), typiquement en fin de partie.
- **Trait** (`Joueur.trait`, ancien « style ») : façon de jouer d'un joueur, choisie parmi les cinq **mots-clés de trait** (« aggressive, tryhard », ADR 0017). Un seul trait par joueur, **commun** à tous ceux qui s'échangent le carnet (ADR 0022).
- **Note** (`Joueur.note`, ancienne « note perso », proposée après le trait à chaque rencontre) : texte libre sur un joueur. Une seule par joueur, commune comme le trait : chacun peut modifier celle d'un autre.
- **Version** (`Revision`) : une valeur du trait ou de la note, avec son auteur (`by`) et sa date (`at`). Effacer ajoute une version vide. La **version actuelle** est la plus récente.
- **Historique** (`Joueur.historique_trait`, `Joueur.historique_note`) : toutes les versions d'un champ, de la plus ancienne à la plus récente. `show` et `edit` affichent les versions remplacées. Rien n'en est jamais retiré, sauf en supprimant le joueur.
- **Différence** (`Difference`) : à l'import, la version actuelle de l'autre est nouvelle pour moi et sa valeur diffère de la mienne. C'est un **conflit** (`Difference.conflit`) quand chacun a modifié de son côté. Sinon, c'est une avance rapide : il a remplacé ma version.
- **Stratégie d'import** (`STRATEGIES`, options `--latest`, `--keep-deleted`, `--mine`, `--theirs`, `--merge`, `--ask`) : comment chaque différence est tranchée. Elle est affichée entre parenthèses à la confirmation et modifiable avec `c`. Par défaut, la plus récente gagne. Un choix différent de la plus récente devient une nouvelle version.
- **Mot-clé de trait** (`Tag`, `traits.py`) : l'un des cinq mots permis (`aggressive`, `defence`,
  `noob`, `tryhard`, `pro`), affiché avec son emoji. Le texte est stocké sans emoji ; l'emoji est ajouté à l'affichage.
- **Classement** (`Classement`) : le top 100 officiel d'une **saison**, en 1v1 et en 2v2, lu sur
  `https://ratings.warselect.io/webapi/top100{1v1|2v2}?season=N` (source de ws-stats.pl).
  En 2v2 le rang est individuel : les deux coéquipiers ont les mêmes points.
- **Rang** (`Rang`) : la position (1 à 100) et les points d'un joueur dans un mode.
  « Hors top 100 » veut dire absent du classement, pas « inconnu ».
- **Top** (`top`) : vue du classement d’un mode, filtrable en tapant (ADR 0015). Ne compte aucune rencontre.
- **Saison** : numéro croissant (29 en novembre 2026). La saison en cours est la dernière
  qui a des joueurs classés en 1v1 ; elle est détectée automatiquement. `show` affiche aussi chaque saison passée où le joueur était dans le top 100, de la plus récente à la plus ancienne (ADR 0019).
- **Export / Import (fusion)** : l'export écrit le carnet dans un fichier pour le transmettre à un autre joueur ;
  l'import fusionne le carnet d'un autre joueur dans le sien. La fusion ajoute les joueurs qui ont
  un trait ou une note, ajoute leurs versions inconnues à l'historique (la plus récente devient la
  version actuelle) et les rencontres des autres. Elle ne touche jamais aux rencontres du
  propriétaire et ne perd aucune version. L'export va sur le Bureau par défaut (`<pseudo>.json`).
