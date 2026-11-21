# superselection

Carnet d'adversaires pour **War Selection**. Pour un nom de joueur saisi, l'outil affiche :

- son rang dans le **top 100** (1v1 et 2v2, saison en cours, d'après
  [ws-stats.pl](https://ws-stats.pl/leaderboard)) ;
- le nombre de rencontres précédentes et la date de la dernière ;
- les **traits** et notes enregistrés (par le propriétaire du carnet et par les carnets importés).

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
  Trait (Antho) : 🛡️ defence, 😤 tryhard
  Trait (Kevin) : 🐣 noob, spam cavalerie
  Nouveau trait ? (Tab = mots-clés, Entrée = garder, - = effacer) >
```

Chaque nom saisi compte comme une rencontre, sauf s'il a déjà été saisi depuis moins de
30 minutes (relecture d'une note en pleine partie). `show Bob` affiche la fiche sans compter
de rencontre. `edit Bob` modifie nom, trait et note sans recompter.

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
| `show <nom>`       | fiche + saisons passées dans le top 100, sans compter   | `show Unloukee`     |
| `edit <nom>`       | modifier nom, trait, note (« - » efface), sans compter  | `edit Pizza`        |
| `list`             | lister les joueurs (A → Z, écritures non latines à la fin) | `list`           |
| `delete <nom>`     | supprimer un joueur du carnet (confirmation)            | `delete Pizza`      |
| `reset`            | vider le carnet (confirmation)                          | `reset`             |
| `export <fichier>` | exporter le carnet vers un fichier                      | `export antho.json` |
| `import <fichier>` | fusionner un carnet exporté                             | `import kevin.json` |
| `refresh`          | recharger le classement                                 | `refresh`           |
| `update`           | installer la dernière version                           | `update`            |
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
détail (unités, stratégie) va dans la note perso. Les traits déjà enregistrés en texte libre
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

1. Exporter : `export antho.json`, puis transmettre le fichier (Discord, mail…).
2. Importer, chez le destinataire : `import antho.json` (Windows : saisir `import `, puis
   glisser le fichier dans la fenêtre pour coller son chemin).

La fusion ajoute les joueurs inconnus et les traits de l'exportateur, **signés de son
pseudo**. Les traits et notes du destinataire ne sont jamais modifiés. Le compteur
« croisé N fois » ne compte que les rencontres du propriétaire du carnet. Un import ultérieur
d'une version plus récente met à jour les traits de l'exportateur. Dans `list`, la colonne
« Croisé par » indique qui connaît le joueur : le propriétaire s'il l'a croisé, puis les
auteurs des traits importés.

## Données

| Système | Carnet (`carnet.json`)                          |
|---------|-------------------------------------------------|
| Windows | `%APPDATA%\superselection\`                     |
| Linux   | `~/.local/share/superselection/`                |
| macOS   | `~/Library/Application Support/superselection/` |

Fichier JSON lisible et modifiable à la main. La variable d'environnement
`SUPERSELECTION_DIR` change le dossier.

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
