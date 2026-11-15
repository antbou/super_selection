# superselection

Carnet d'adversaires pour **War Selection**. Quand tu tombes sur un joueur, tu tapes
son nom et l'outil te dit :

- s'il est dans le **top 100** (1v1 et 2v2, saison en cours, d'après
  [ws-stats.pl](https://ws-stats.pl/leaderboard)) ;
- si tu l'as **déjà croisé**, combien de fois et quand ;
- le **profil de jeu** que toi (et tes potes) avez noté.

Puis tu notes son trait en une ligne. C'est tout.

## Installation

### Windows

Ouvre **PowerShell**, colle cette ligne, Entrée :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/antbou/super_selection/main/install.ps1 | iex"
```

Ferme la fenêtre, rouvre-la, tape `superselection`. Rien d'autre à installer (ni Python,
ni Git). Détails et dépannage :
[docs/installation-windows.md](docs/installation-windows.md).

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install https://github.com/antbou/super_selection/archive/refs/heads/main.zip
```

### Mettre à jour

Au démarrage, l'outil prévient quand une nouvelle version est sortie :

```text
Nouvelle version 0.3.0 disponible (tu as 0.2.0) : tape « update ».
```

Tape `update`. Sous Windows, la mise à jour s'ouvre dans une nouvelle fenêtre puis relance
l'outil. Ton carnet est conservé.

## Utilisation

```text
$ superselection
Chargement du classement top 100… saison 29 OK.
Tape un nom de joueur (Tab pour compléter), « help » pour les commandes.

adversaire > marme⇥            ← Tab complète : Marmelaaada  (1v1 #1)
Marmelaaada
  1v1 : #1 (758 pts)   ·   2v2 : hors top 100
  Première rencontre.
  Trait : pas encore noté
  Son trait ? (Tab = mots-clés, Entrée = passer) > aggressive, tryhard
  Trait enregistré.

adversaire > Bob
Bob
  1v1 : hors top 100   ·   2v2 : hors top 100
  Croisé 3 fois — dernière fois le 12/11/2026
  Trait (toi) : 🛡️ defence, 😤 tryhard
  Trait (Kevin) : 🐣 noob, spam cavalerie
  Nouveau trait ? (Tab = mots-clés, Entrée = garder, - = effacer) >
```

Chaque nom tapé compte comme une rencontre, sauf si tu l'as déjà tapé il y a moins de
30 minutes (pour relire une note en pleine partie). Pour seulement regarder une fiche
sans compter de rencontre : `show Bob`. Pour changer son trait, ta note ou son nom à la
fin d'une partie (sans recompter) : `edit Bob`.

Un nom inconnu du top 100 et du carnet est signalé « Nouveau joueur », avec les noms
proches s'il y en a : une faute de frappe se corrige avec `delete` (puis tape le bon nom).

### Commandes

| Commande           | Ce que ça fait                                   | Exemple              |
|--------------------|--------------------------------------------------|----------------------|
| `<nom>`            | croiser un joueur, puis noter son trait          | `[IMP] Pizza`        |
| `show <nom>`       | voir sa fiche sans compter de rencontre          | `show Unloukee`      |
| `list`             | tous les joueurs déjà croisés, du plus récent    | `list`               |
| `delete <nom>`     | retirer un joueur du carnet (confirmation)       | `delete Pizza`       |
| `edit <nom>`       | corriger nom, trait, note (« - » efface), sans compter | `edit Pizza` |
| `traits`           | les mots-clés de trait et leurs emojis           | `traits`             |
| `export <fichier>` | écrire ton carnet dans un fichier pour un pote   | `export antho.json`  |
| `import <fichier>` | fusionner le carnet d'un pote dans le tien       | `import kevin.json`  |
| `refresh`          | recharger le classement                          | `refresh`            |
| `update`           | installer la dernière version                    | `update`             |
| `version`          | voir la version installée                        | `version`            |
| `help`             | afficher l'aide                                  | `help`               |
| `quit`             | sortir (ou `q`, `exit`, Ctrl+D)                  | `q`                  |

### Traits et emojis

Le trait se choisit parmi cinq mots-clés, chacun avec son emoji. Ils s'affichent dès que tu
notes un trait (Tab ou ↓ pour choisir) :

| Emoji | Mot-clé      | Sens                                   |
|-------|--------------|----------------------------------------|
| 🔥    | `aggressive` | attaque tout le temps                  |
| 🛡️    | `defence`    | joue défensif, tient bien ses positions |
| 🐣    | `noob`       | débutant / faible                      |
| 😤    | `tryhard`    | joue à fond, ne lâche rien             |
| 👑    | `pro`        | très fort                              |

Tu peux en mettre plusieurs : `aggressive, tryhard` s'affiche `🔥 aggressive, 😤 tryhard`.
Les variantes marchent aussi (`agressif`, `defense`, `défense`, `def`, `nul`…) et sont
enregistrées sous le mot conseillé. Un autre mot est refusé : le détail (unités, stratégie)
va dans ta note perso. Les traits déjà notés en texte libre restent affichés tels quels.

Un joueur s'appelle comme une commande ? Utilise `player list`.

### Nom en chinois, russe… impossible à taper ?

Copie le texte depuis une capture d'écran, puis colle-le dans l'outil :

1. **Windows 11** : `Windows + Maj + S`, encadre le nom. Clique sur la notification
   pour ouvrir la capture dans l'**Outil Capture**, puis **Actions de texte** →
   **Copier tout le texte**.
   *Plus rapide* : [PowerToys](https://aka.ms/installpowertoys) → **Text Extractor**,
   `Windows + Maj + T`, encadre le nom, et le texte est copié directement.
2. Dans superselection : clic droit (ou `Ctrl + V`) pour coller, puis Entrée.

Astuce : si la reconnaissance se trompe sur un caractère, colle seulement une partie du
nom puis appuie sur Tab. La complétion cherche dans tout le nom, donc elle retrouve le
joueur dans le top 100 ou dans ton carnet.

Pour le chinois ou le russe, Windows doit avoir la langue de reconnaissance installée :
Paramètres → Heure et langue → Langue → Ajouter une langue (le module de base suffit).

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

La fusion ajoute les joueurs qu'il ne connaît pas et les traits que tu as notés,
**signés de ton pseudo**. Elle ne touche jamais à ses propres traits. Le compteur
« croisé N fois » ne compte que ses rencontres à lui. Si tu lui renvoies plus
tard une version plus récente de ton carnet, tes traits sont mis à jour chez lui.

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

Publier une version : augmenter `version` dans `pyproject.toml` (puis `uv lock`) et pousser
sur `main`. Les utilisateurs sont prévenus au lancement suivant.

Vocabulaire du domaine : voir [GLOSSARY.md](GLOSSARY.md).
Décisions et leurs raisons : [docs/adr/](docs/adr/).
