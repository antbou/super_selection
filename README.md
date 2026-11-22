# superselection

Carnet d'adversaires pour **War Selection**. Pour un nom de joueur saisi, l'outil affiche :

- son rang dans le **top 100** (1v1 et 2v2, saison en cours, d'après
  [ws-stats.pl](https://ws-stats.pl/leaderboard)) ;
- le nombre de rencontres précédentes et la date de la dernière ;
- son **trait** et sa **note**, communs à tous ceux qui s'échangent le carnet : chacun peut les
  modifier, la version la plus récente l'emporte et `show` garde l'historique.

Un trait se note ensuite en une ligne.

## Installation

### Windows

Ouvrir **PowerShell**, exécuter :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/antbou/super_selection/main/install.ps1 | iex"
```

Fermer la fenêtre, en ouvrir une nouvelle, lancer `superselection`. Ni Python ni Git ne sont
requis. Détails et dépannage : [docs/installation-windows.md](docs/installation-windows.md).

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install https://github.com/antbou/super_selection/archive/refs/heads/main.zip
```

### Mise à jour

Au démarrage, l'outil signale une nouvelle version :

```text
Nouvelle version 0.3.0 disponible (installée : 0.2.0) : « update ».
```

La commande `update` installe la dernière version. Sous Windows, la mise à jour s'exécute
dans une nouvelle fenêtre puis relance l'outil. Le carnet est conservé.

Juste après une publication, GitHub peut encore annoncer l'ancienne version pendant
quelques minutes. `update --force` réinstalle la dernière version sans vérifier.

## Utilisation

```text
$ superselection
Chargement du classement top 100… saison 29 OK.
Saisir un nom de joueur (Tab pour compléter), « help » pour les commandes.

adversaire > marme⇥            ← Tab complète : Marmelaaada  (1v1 #1)
Marmelaaada
  1v1 : #1 (758 pts)   ·   2v2 : hors top 100
  Première rencontre.
  Trait : pas encore noté
  Trait ? (Tab = mots-clés, Entrée = passer) > aggressive, tryhard
  Trait enregistré.

adversaire > Bob
Bob
  1v1 : hors top 100   ·   2v2 : hors top 100
  Croisé 3 fois — dernière fois le 12/11/2026
  Note : rush archers à 3 min  (Kevin, 11/11/2026)
  Trait : 🛡️ defence, 😤 tryhard  (Antho, 12/11/2026)
  Nouveau trait ? (Tab = mots-clés, Entrée = garder, - = effacer) >
```

Chaque nom saisi compte comme une rencontre, sauf s'il a déjà été saisi depuis moins de
30 minutes (relecture d'une note en pleine partie). `show Bob` affiche la fiche sans compter
de rencontre, avec l'historique des versions du trait et de la note (les 10 dernières).
`edit Bob` affiche le même historique, puis modifie nom, trait et note sans recompter.

Un nom absent du top 100 et du carnet est signalé « Nouveau joueur », avec les noms proches
s'il y en a. Une faute de frappe se corrige avec `delete`, puis en saisissant le bon nom.

Une commande peut aussi être passée directement, sans la boucle interactive :

```bash
superselection list
superselection import kevin.json
superselection "[IMP] Pizza"
```

### Commandes

| Commande           | Effet                                                   | Exemple             |
|--------------------|---------------------------------------------------------|---------------------|
| `<nom>`            | croiser un joueur, puis noter son trait                 | `[IMP] Pizza`       |
| `top [1v1\|2v2]`   | afficher le top 100, recherche en tapant                | `top 2v2`           |
| `show <nom>`       | fiche + saisons passées + historique, sans compter      | `show Unloukee`     |
| `edit <nom>`       | modifier nom, trait, note (« - » efface), sans compter  | `edit Pizza`        |
| `list`             | lister les joueurs, concis (A → Z, non latins à la fin) | `list`              |
| `delete <nom>`     | supprimer un joueur du carnet (confirmation)            | `delete Pizza`      |
| `reset`            | vider le carnet (confirmation)                          | `reset`             |
| `export [fichier]` | exporter le carnet (sur le Bureau par défaut)           | `export antho.json` |
| `import <fichier>` | fusionner un carnet exporté (choix en cas de conflit)   | `import kevin.json` |
| `refresh`          | recharger le classement                                 | `refresh`           |
| `update [--force]` | installer la dernière version (`--force` : sans vérifier) | `update --force`  |
| `version`          | afficher la version installée                           | `version`           |
| `help`             | afficher l'aide                                         | `help`              |
| `quit`             | quitter (aussi `q`, `exit`, Ctrl+D)                     | `q`                 |

Un joueur dont le nom est identique à une commande se saisit avec `player <nom>` :
`player list`.

### Traits et emojis

Le trait est choisi parmi cinq mots-clés, chacun associé à un emoji (Tab ou ↓ pour les
proposer lors de la saisie) :

| Emoji | Mot-clé      | Sens                                    |
|-------|--------------|-----------------------------------------|
| 🔥    | `aggressive` | attaque tout le temps                   |
| 🛡️    | `defence`    | joue défensif, tient bien ses positions |
| 🐣    | `noob`       | débutant / faible                       |
| 😤    | `tryhard`    | joue à fond, ne lâche rien              |
| 👑    | `pro`        | très fort                               |

Plusieurs mots-clés sont possibles : `aggressive, tryhard` s'affiche
`🔥 aggressive, 😤 tryhard`. Les variantes (`agressif`, `defense`, `défense`, `def`, `nul`…)
sont acceptées et enregistrées sous le mot-clé correspondant. Tout autre mot est refusé : le
détail (unités, stratégie) va dans la note. Les traits déjà enregistrés en texte libre
restent affichés tels quels.

### Noms en caractères non saisissables (chinois, russe…)

Le nom peut être copié depuis une capture d'écran, puis collé dans l'outil :

1. **Windows 11** : `Windows + Maj + S`, sélectionner le nom. Ouvrir la capture dans l'**Outil
   Capture** (clic sur la notification), puis **Actions de texte** → **Copier tout le texte**.
   Alternative plus rapide : [PowerToys](https://aka.ms/installpowertoys) → **Text Extractor**
   (`Windows + Maj + T`), le texte est copié directement.
2. Dans superselection : clic droit (ou `Ctrl + V`) pour coller, puis Entrée.

Si la reconnaissance se trompe sur un caractère, coller seulement une partie du nom puis
appuyer sur Tab : la complétion cherche dans tout le nom, dans le top 100 comme dans le carnet.

La reconnaissance du chinois ou du russe requiert la langue correspondante dans Windows :
Paramètres → Heure et langue → Langue → Ajouter une langue (le module de base suffit).

### Partage de carnet

1. Exporter : `export` (crée `<pseudo>.json` sur le Bureau) ou `export antho.json`, puis
   transmettre le fichier (Discord, mail…). Un chemin complet est utilisé tel quel.
2. Importer, chez le destinataire : `import antho.json` (Windows : saisir `import `, puis
   glisser le fichier dans la fenêtre pour coller son chemin).

Un joueur n'a qu'**un trait et une note**, communs : le destinataire peut modifier la note
écrite par l'exportateur, et inversement. Chaque modification est une **version** signée et
datée. À l'import, les versions de l'autre rejoignent l'historique et **la plus récente
l'emporte**. Rien n'est perdu : `show` et `edit` montrent les versions remplacées.

S'il y a un **conflit** (chacun a modifié la même note de son côté), l'import demande :

```text
2 conflit(s) avec Paul (1 note(s), 1 trait(s)), dont 1 suppression(s).
  Garder ? (Entrée = la plus récente gagne, s = la plus récente sans suppression, u = choisir un par un) >
```

- **Entrée** : la plus récente gagne, même si c'est une suppression.
- **s** : pareil, mais une note ou un trait supprimé par l'autre est gardé.
- **u** : pour chaque conflit, `1` = la mienne, `2` = la sienne, `f` = fusionner les deux
  (mots-clés réunis, ou les deux notes « a / b »), Entrée = la plus récente.

Un choix différent de la plus récente est enregistré comme nouvelle version : à son prochain
import, l'autre la reçoit sans nouvelle question. Ctrl+C pendant les questions annule l'import.

Attention : notes et historique sont lisibles par toute personne qui reçoit le fichier.
« Croisé N fois » ne compte que mes rencontres ; `show` affiche aussi celles des autres
(« Rencontres des autres : Paul 1 fois »). `list` reste concise : version actuelle, sans
auteurs. Un carnet exporté par une ancienne version (avant 0.15.0) s'importe toujours ; à
l'inverse, une ancienne version ne lit pas le nouveau format : chacun doit faire `update`.

## Données

| Système | Carnet (`notebook.json`)                        |
|---------|-------------------------------------------------|
| Windows | `%APPDATA%\superselection\`                     |
| Linux   | `~/.local/share/superselection/`                |
| macOS   | `~/Library/Application Support/superselection/` |

Fichier JSON lisible et modifiable à la main (champs en anglais : `players`, `trait_history`,
`note_history`…). La variable d'environnement `SUPERSELECTION_DIR` change le dossier. Un
ancien `carnet.json` est converti au premier lancement, et gardé sous `carnet.v1.bak.json`.

## Développement

```bash
uv sync
uv run pytest
uv run superselection
```

Publication : augmenter `version` dans `pyproject.toml` (puis `uv lock`) et pousser sur
`main`. Les utilisateurs sont prévenus au lancement suivant.

Vocabulaire du domaine : [GLOSSARY.md](GLOSSARY.md).
Décisions et justifications : [docs/adr/](docs/adr/).
