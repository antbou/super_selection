# superselection

Carnet d'adversaires pour **War Selection**. Quand tu tombes sur un joueur, tu tapes
son nom et l'outil te dit :

- s'il est dans le **top 100** (1v1 et 2v2, saison en cours, d'après
  [ws-stats.pl](https://ws-stats.pl/leaderboard)) ;
- si tu l'as **déjà croisé**, combien de fois et quand ;
- le **style de jeu** que toi (et tes potes) avez noté.

Puis tu notes son style en une ligne. C'est tout.

## Installation

### Windows

Ouvre **PowerShell**, colle cette ligne, Entrée :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/antbou/super_selection/main/install.ps1 | iex"
```

Ferme la fenêtre, rouvre-la, tape `superselection`. Rien d'autre à installer (ni Python,
ni Git). Même ligne pour mettre à jour. Détails et dépannage :
[docs/installation-windows.md](docs/installation-windows.md).

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install https://github.com/antbou/super_selection/archive/refs/heads/main.zip
```

## Utilisation

```text
$ superselection
Chargement du classement top 100… saison 29 OK.
Tape un nom de joueur (Tab pour compléter), « help » pour les commandes.

adversaire > marme⇥            ← Tab complète : Marmelaaada  (1v1 #1)
Marmelaaada
  1v1 : #1 (758 pts)   ·   2v2 : hors top 100
  Première rencontre.
  Style : pas encore noté
  Son style ? (Tab = mots-clés, Entrée = passer) > aggressive, rush archers
  Style enregistré.

adversaire > Bob
Bob
  1v1 : hors top 100   ·   2v2 : hors top 100
  Croisé 3 fois — dernière fois le 12/11/2026
  Style (toi) : 🛡️ defence, 😤 tryhard
  Style (Kevin) : 🐣 noob, spam cavalerie
  Nouveau style ? (Tab = mots-clés, Entrée = garder, - = effacer) >
```

Chaque nom tapé compte comme une rencontre. Pour seulement regarder une fiche sans
compter de rencontre : `show Bob`.

### Commandes

| Commande           | Ce que ça fait                                   | Exemple              |
|--------------------|--------------------------------------------------|----------------------|
| `<nom>`            | croiser un joueur, puis noter son style          | `[IMP] Pizza`        |
| `show <nom>`       | voir sa fiche sans compter de rencontre          | `show Unloukee`      |
| `list`             | tous les joueurs déjà croisés, du plus récent    | `list`               |
| `styles`           | les mots-clés de style et leurs emojis           | `styles`             |
| `export <fichier>` | écrire ton carnet dans un fichier pour un pote   | `export antho.json`  |
| `import <fichier>` | fusionner le carnet d'un pote dans le tien       | `import kevin.json`  |
| `refresh`          | recharger le classement                          | `refresh`            |
| `help`             | afficher l'aide                                  | `help`               |
| `quit`             | sortir (ou `q`, `exit`, Ctrl+D)                  | `q`                  |

### Styles et emojis

Le style est un texte libre. Cinq mots-clés reçoivent un emoji à l'affichage, et Tab les
complète quand tu notes un style :

| Emoji | Mot-clé      | Sens                                   |
|-------|--------------|----------------------------------------|
| 🔥    | `aggressive` | attaque tout le temps                  |
| 🛡️    | `defence`    | joue défensif, tient bien ses positions |
| 🐣    | `noob`       | débutant / faible                      |
| 😤    | `tryhard`    | joue à fond, ne lâche rien             |
| 👑    | `pro`        | très fort                              |

Tu peux en mettre plusieurs et ajouter du texte : `aggressive, tryhard, rush archers`
s'affiche `🔥 aggressive, 😤 tryhard, rush archers`. Les variantes marchent aussi
(`aggresive`, `agressif`, `defense`, `défense`, `def`, `nul`…).

Un joueur s'appelle comme une commande ? Utilise `player list`.

Tu peux aussi lancer une commande directement, sans la boucle :

```bash
superselection list
superselection import kevin.json
superselection "[IMP] Pizza"
```

### Partager avec un pote

1. Toi : `export antho.json`, puis tu lui envoies le fichier (Discord, mail…).
2. Lui : `import antho.json` (astuce Windows : tape `import `, puis glisse le fichier
   dans la fenêtre pour coller son chemin).

La fusion ajoute les joueurs qu'il ne connaît pas et les styles que tu as notés,
**signés de ton pseudo**. Elle ne touche jamais à ses propres notes. Le compteur
« croisé N fois » ne compte que ses rencontres à lui. Si tu lui renvoies plus
tard une version plus récente de ton carnet, tes notes sont mises à jour chez lui.

## Où sont mes données ?

| Système | Carnet (`carnet.json`)                              |
|---------|-----------------------------------------------------|
| Windows | `%APPDATA%\superselection\`                         |
| Linux   | `~/.local/share/superselection/`                    |
| macOS   | `~/Library/Application Support/superselection/`     |

C'est un fichier JSON lisible : tu peux l'ouvrir et le modifier à la main. La
variable d'environnement `SUPERSELECTION_DIR` permet de choisir un autre dossier.

## Développement

```bash
uv sync
uv run pytest
uv run superselection
```

Vocabulaire du domaine : voir [GLOSSARY.md](GLOSSARY.md).
