# superselection

Carnet d'adversaires pour **War Selection**. Quand tu tombes sur un joueur, tu tapes
son nom et l'outil te dit :

- s'il est dans le **top 100** (1v1 et 2v2, saison en cours, d'après
  [ws-stats.pl](https://ws-stats.pl/leaderboard)) ;
- si tu l'as **déjà croisé**, combien de fois et quand ;
- le **style de jeu** que toi (et tes potes) avez noté.

Puis tu notes son style en une ligne. C'est tout.

## Installation

**Sur Windows, en partant de zéro** : suis le guide pas à pas
[docs/installation-windows.md](docs/installation-windows.md).

En bref : il faut [uv](https://docs.astral.sh/uv/) (Windows, Linux ou macOS).

Windows (PowerShell) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Linux / macOS :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Puis, dans le dossier du projet :

```bash
uv tool install .
```

La commande `superselection` est alors disponible partout. Pour mettre à jour après
une modification du code : `uv tool install . --reinstall`.

Sous Windows, utilise **Windows Terminal** pour que les noms chinois ou cyrilliques
s'affichent correctement.

## Utilisation

```text
$ superselection
Chargement du classement top 100… saison 29 OK.
Tape un nom de joueur (Tab pour compléter), « aide » pour les commandes.

adversaire > marme⇥            ← Tab complète : Marmelaaada  (1v1 #1)
Marmelaaada
  1v1 : #1 (758 pts)   ·   2v2 : hors top 100
  Première rencontre.
  Style : pas encore noté
  Son style ? (Entrée = passer) > très agressif, rush dès le début
  Style enregistré.

adversaire > Bob
Bob
  1v1 : hors top 100   ·   2v2 : hors top 100
  Croisé 3 fois — dernière fois le 12/11/2026
  Style (toi) : passif, se défend bien
  Style (Kevin) : spam cavalerie
  Nouveau style ? (Entrée = garder, - = effacer) >
```

Chaque nom tapé compte comme une rencontre. Pour seulement regarder une fiche sans
compter de rencontre : `voir Bob`.

### Commandes

| Commande           | Ce que ça fait                                   | Exemple              |
|--------------------|--------------------------------------------------|----------------------|
| `<nom>`            | croiser un joueur, puis noter son style          | `[IMP] Pizza`        |
| `voir <nom>`       | voir sa fiche sans compter de rencontre          | `voir Unloukee`      |
| `liste`            | tous les joueurs déjà croisés, du plus récent    | `liste`              |
| `export <fichier>` | écrire ton carnet dans un fichier pour un pote   | `export antho.json`  |
| `import <fichier>` | fusionner le carnet d'un pote dans le tien       | `import kevin.json`  |
| `maj`              | recharger le classement                          | `maj`                |
| `aide`             | afficher l'aide                                  | `aide`               |
| `quitter`          | sortir (ou Ctrl+D)                               | `q`                  |

Un joueur s'appelle comme une commande ? Utilise `joueur liste`.

Tu peux aussi lancer une commande directement, sans la boucle :

```bash
superselection liste
superselection import kevin.json
superselection "[IMP] Pizza"
```

### Partager avec un pote

1. Toi : `export antho.json`, puis tu lui envoies le fichier (Discord, mail…).
2. Lui : `import antho.json`.

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
