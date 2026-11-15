# Plan : corriger les bugs relevés par la revue du 15/11/2026

Ce plan est écrit pour un agent qui n'a pas suivi la revue. Il se suffit à lui-même, mais
le détail de chaque constat est dans [revue-2026-11-15.md](revue-2026-11-15.md) (les
identifiants B1, W3, S2… renvoient à ce document).

## Objectif

Après ce travail, l'utilisateur ne voit plus jamais de traceback Python, et l'outil
n'affiche plus de rang faux. Aucune fonctionnalité nouvelle.

## Périmètre

| Dans le plan | Hors du plan (ne pas y toucher) |
|---|---|
| B1 à B8, W2, W3, S2 | F1 à F8 (suppression, renommage, historique, mots-clés, coéquipier 2v2…) |
| | W1 (fins de ligne de `install.ps1`), W4, W5, W6, S1 |

Si une correction semble demander un changement hors périmètre, s'arrêter et le signaler
au lieu de l'étendre.

## Règles à respecter (extraites de `CLAUDE.md`)

- Lire `CLAUDE.md`, `GLOSSARY.md` et `docs/adr/` avant de commencer.
- TDD : écrire le test qui échoue, puis le code. Lancer `uv run pytest` après chaque étape.
- Le réseau n'est jamais appelé en test : il est injecté.
- Code, noms et messages en français ; commandes en anglais.
- Compatible Windows : `pathlib`, `encoding="utf-8"`, aucune commande shell.
- Couleurs uniquement par `couleurs.peindre` ; le texte doit rester identique sans couleur.
- La logique va dans `app.py` (testée) ; `cli.py` reste mince.
- Un commit par étape, message au format `fix: …`, **sans** ligne `Co-Authored-By`.
  Ne pas pousser : le propriétaire le fera.
- Pour essayer à la main sans toucher au vrai carnet :
  `SUPERSELECTION_DIR=/tmp/essai uv run superselection`.

## État de départ

Commit `57ae1eb` sur `main`, 41 tests passent, version `0.2.0`.

---

## Étape 1 — Valider et nettoyer ce qu'on lit d'un carnet (B5, S2)

**Problème.** `Carnet.depuis_dict` (`carnet.py:118`) ne vérifie aucun type. Un fichier
contenant `[]` lève `AttributeError`, que `App.importer` n'attrape pas. Des valeurs comme
`"rencontres": "a"` sont acceptées puis font planter plus tard. Les textes peuvent contenir
des séquences d'échappement qui sont envoyées au terminal.

**À faire.**

1. Créer `src/superselection/texte.py` avec `sans_controle(texte: str) -> str`, qui retire
   les caractères de catégorie Unicode `Cc` (cela couvre `\x1b`, `\x07`, les retours à la
   ligne, les tabulations et la plage `\x80`–`\x9f`). Ne pas retirer la catégorie `Cf` :
   elle sert dans certains emojis et noms.
2. Dans `carnet.py`, ajouter `class CarnetInvalide(ValueError)`.
3. `depuis_dict` lève `CarnetInvalide` avec un message en français qui situe l'erreur
   (exemple : `joueur n°3 (« Bob ») : « rencontres » doit être un nombre entier`) quand :
   - la racine n'est pas un objet, ou `joueurs` n'est pas une liste ;
   - `auteur` est présent mais n'est pas un texte (absent : garder `"?"` comme aujourd'hui) ;
   - un joueur n'est pas un objet, ou son `nom` n'est pas un texte non vide ;
   - `rencontres` n'est pas un entier positif ou nul (refuser aussi `true`/`false`) ;
   - `derniere` n'est ni `null` ni un texte qui commence par `AAAA-MM-JJ` ;
   - `styles` n'est pas un objet, ou une note n'a pas de `texte` en texte, ou `maj` n'est
     pas un texte (absent : garder `""`).
4. Passer `nom`, `auteur` (carnet et notes) et `texte` par `sans_controle`, puis `strip()`.
   Un nom vide après nettoyage est une erreur.
5. Dans `App.importer` (`app.py:193`), ajouter le détail au message :
   `Ce fichier n'est pas un carnet superselection : <chemin> (<détail>)`.
   `json.JSONDecodeError` hérite de `ValueError` : un seul `except (ValueError, OSError)`
   suffit, en gardant le cas `FileNotFoundError` séparé avant.

**Tests** (`tests/test_carnet.py`, `tests/test_app.py`, nouveau `tests/test_texte.py`).

- `sans_controle("a\x1b[2Jb\x07")` rend `"a[2Jb"` ; un nom chinois et un emoji composé
  restent intacts.
- `depuis_dict([])`, puis un cas par règle ci-dessus : `CarnetInvalide`.
- Un carnet valide en version 1 se charge comme avant (le test existant
  `test_sauver_puis_charger` doit rester vert).
- `importer` d'un fichier `[]` et d'un fichier au JSON cassé : message d'erreur, pas
  d'exception, carnet inchangé.

## Étape 2 — Carnet illisible, premier lancement, filet de sécurité (B4, B6, W2)

**Problème.** `cli.py:194` charge le carnet sans protection. `cli.py:199` appelle `input()`
même sans terminal. Toute exception ferme la fenêtre quand l'outil est lancé par un
raccourci Windows.

**À faire.**

1. Renommer le corps actuel de `main` en `_principal(argv)`. Le nouveau `main` l'appelle
   dans un `try` :
   - `CarnetInvalide` ou `OSError` au chargement du carnet : afficher
     `Ton carnet est illisible : <chemin>` suivi du détail et de
     `Corrige ce fichier ou renomme-le pour repartir d'un carnet vide.` **Ne jamais écraser
     ni supprimer le fichier.**
   - toute autre `Exception` : afficher `Erreur inattendue : <type> : <message>` et écrire
     le traceback complet dans `erreur.log` du dossier de données (UTF-8), en indiquant
     son chemin.
   - dans les deux cas, si `sys.stdin.isatty()`, attendre avec
     `Appuie sur Entrée pour fermer…`, puis sortir avec le code 1.
2. Premier lancement :
   - sans terminal (`not interactif`) : afficher
     `Premier lancement : lance « superselection » dans un terminal pour choisir ton pseudo.`
     et sortir avec le code 1, sans créer de carnet ;
   - Ctrl+C ou Ctrl+D à la question du pseudo : sortir proprement, sans créer de carnet.
3. Nettoyer le pseudo saisi avec `sans_controle`.

**Tests** (nouveau `tests/test_cli.py`). Appeler `main([...])` avec `SUPERSELECTION_DIR`
pointé sur `tmp_path` (`monkeypatch.setenv`) et **remplacer le réseau** :
`monkeypatch.setattr` sur `cli.fetch_http` et `cli.fetch_pyproject` par des fonctions
qui lèvent `OSError`. Lire la sortie avec `capsys`.

- Carnet contenant `{` : `SystemExit` de code 1, le message contient le chemin, le fichier
  est inchangé sur le disque, aucun mot `Traceback` dans la sortie.
- Premier lancement sans terminal : code 1, message attendu, `carnet.json` n'existe pas.
- Exception inattendue (faire lever `RuntimeError` par un `charger_classement` remplacé) :
  code 1, `erreur.log` existe et contient `RuntimeError`.

## Étape 3 — Ctrl+C ou Ctrl+D pendant la saisie du style (B1)

**Problème.** `executer` (`cli.py:114`) laisse remonter `KeyboardInterrupt` et `EOFError`
levés par `demander`, et l'appel `executer` de la boucle (`cli.py:251`) est hors du `try`.

**À faire.** Dans `executer`, entourer l'appel à `demander` : ces deux exceptions valent
une réponse vide (on garde le style actuel, la rencontre reste comptée). En profiter pour
remplacer l'appel à la méthode privée `app._nom_canonique` (`cli.py:107`) par une méthode
publique de `App` ; ne pas déplacer davantage de logique.

**Tests** (`tests/test_cli.py`). `executer(app, "Bob", demander)` avec un `demander` qui
lève `KeyboardInterrupt`, puis `EOFError` : renvoie `True`, `Bob` a une rencontre, aucun
style. Vérifier aussi les trois cas normaux qui n'ont aucun test aujourd'hui : texte saisi
(style enregistré), `-` (style effacé), réponse vide (style gardé).

## Étape 4 — Enregistrement impossible (W3)

**Problème.** `os.replace` (`carnet.py:137`) lève `PermissionError` sous Windows si le
fichier est ouvert ailleurs. `App.exporter` ne protège pas non plus l'écriture.

**À faire.**

1. Dans `Carnet.sauver` : en cas de `PermissionError`, réessayer 3 fois avec 0,1 s
   d'attente, puis laisser remonter. Supprimer le fichier `.tmp` si l'écriture échoue.
2. Dans `App.exporter` : attraper `OSError` et répondre
   `Impossible d'écrire <chemin> : <raison>`.
3. Dans la boucle interactive de `cli.py` : attraper `OSError` autour de `executer`,
   afficher `Impossible d'enregistrer le carnet : <raison>. Ferme le programme qui
   utilise ce fichier ; l'enregistrement sera refait à la prochaine saisie.` et continuer
   la boucle.

**Tests.** Remplacer `os.replace` dans le module `carnet` (`monkeypatch`) par une fonction
qui échoue deux fois puis réussit : `sauver` réussit. Qui échoue toujours :
`PermissionError` remonte et le `.tmp` a disparu. Remplacer aussi `time.sleep` pour ne pas
ralentir les tests. Export vers un chemin dont le parent est un fichier : message
d'erreur, pas d'exception.

## Étape 5 — Nom de joueur qui commence par une commande (B2)

**Problème.** `analyser` (`app.py:55`) ne regarde que le premier mot : `Show Me` lance
`show Me`, et un joueur nommé `Q` fait quitter.

**À faire.** Ajouter un paramètre facultatif : `analyser(ligne, noms_connus=())`. Si la
ligne entière, sans la casse, est égale à un nom connu, renvoyer `("croiser", ligne)`.
Sinon, comportement actuel. `executer` passe `app.noms()`. `player <nom>` reste valable.

**Tests** (`tests/test_app.py`). Le test existant `test_analyser_commandes` doit rester
vert sans modification (`analyser("Q")` rend toujours `("quit", "")` quand aucun joueur ne
s'appelle `Q`). Ajouter : avec `noms_connus=["Show Me", "Q"]`, `show me` et `q` rendent
`croiser` ; `show Bob` rend toujours `("show", "Bob")`.

## Étape 6 — Homonymes dans le classement (B3)

**Problème.** L'API contient des noms en double (vérifié : deux `Marmelaaada` en 1v1,
n°1 et n°51). `Classement.rang` (`classement.py:46`) renvoie le premier, donc la fiche du
n°51 annonce « #1 ».

**À faire.**

1. Ajouter `Classement.rangs(nom, mode) -> list[Rang]` (tous, dans l'ordre). Garder `rang`
   qui renvoie le premier ou `None`, pour ne pas casser les appels existants.
2. Dans `App._ligne_rangs` (`app.py:99`), quand il y a plusieurs rangs, afficher par
   exemple : `1v1 : #1 (758 pts) ou #51 (403 pts) — 2 joueurs portent ce nom`.
   Chaque rang garde sa couleur (`role_rang`).
3. Dans le texte d'aide du menu de complétion (`cli.py`, `_meta`), afficher `1v1 #1/#51`.

**Tests.** `rangs` avec un nom en double rend deux `Rang`. La fiche contient les deux
positions et la mention. Le test de `tests/test_couleurs.py` (même texte avec et sans
couleur) doit être étendu à ce cas.

## Étape 7 — Erreurs réseau et cache (B8)

**Problème.** `charger_classement` (`classement.py:113`) ne couvre pas toutes les erreurs,
et l'écriture du cache n'est pas protégée.

**À faire.**

1. Sortir de `fetch_http` une fonction pure `lire_reponse(corps) -> list` : elle lève
   `ErreurClassement` si `corps` n'est pas un objet, si `error` n'est pas 0, si `data`
   n'est pas une liste. Elle ne garde que les lignes qui sont des objets avec `name` en
   texte non vide et `rating` entier, et passe `name` par `sans_controle`.
2. `fetch_http` convertit `http.client.HTTPException` en `ErreurClassement`.
3. Dans `charger_classement`, entourer l'écriture du cache d'un `try/except OSError`
   (échec ignoré : le classement téléchargé reste utilisé).
4. `_lire_cache` : attraper aussi `TypeError` et `AttributeError`, et refuser un cache dont
   `lignes` n'a pas la forme attendue (rendre `None`).

**Tests** (`tests/test_classement.py`). `lire_reponse` : une liste à la racine, une erreur
d'API, des lignes mal formées (ignorées), un nom avec `\x1b` (nettoyé). Cache impossible à
écrire (`cache = tmp_path / "fichier" / "c.json"` où `fichier` est un fichier) : le
classement est quand même rendu, sans message d'erreur. Cache contenant `[]` : traité
comme absent.

## Étape 8 — `update` sans internet (B7)

**Problème.** `update` répond « Déjà à jour » quand GitHub est injoignable, parce que
`nouvelle_version` rend `None` dans les deux cas.

**À faire.** Dans `executer` (commande `update`), appeler d'abord
`lire_version_publiee(fetch_pyproject)`. Si elle rend `None` : afficher
`Impossible de vérifier la dernière version (pas d'internet ?). Réessaie plus tard.` et
rester dans l'outil. Sinon, comparer avec `est_plus_recente`. Ne pas changer la
vérification silencieuse du démarrage (ADR 0006). Si cela simplifie le test, mettre la
décision dans une fonction pure de `version.py` qui rend l'un des trois états.

**Tests** (`tests/test_version.py`). Les trois cas : injoignable, à jour, nouvelle version.

## Étape 9 — Version et documentation

1. `pyproject.toml` : `version = "0.2.1"`, puis `uv lock`.
2. `README.md` : rien à changer en principe ; vérifier que les exemples restent exacts
   (notamment l'affichage d'une fiche).
3. `docs/installation-windows.md`, section Dépannage : ajouter deux entrées courtes,
   « Ton carnet est illisible » et « Erreur inattendue » (où trouver `erreur.log`).
4. Pas d'ADR : aucune de ces corrections n'est une décision difficile à défaire.

---

## Critères de fin

- `uv run pytest` : tout passe, et chaque étape a ajouté ses tests.
- Ces commandes n'affichent plus aucun `Traceback` (à lancer avec
  `SUPERSELECTION_DIR=/tmp/essai`) :
  - `uv run superselection list < /dev/null` sur un dossier vide ;
  - `uv run superselection list` avec un `carnet.json` contenant `{` ;
  - `uv run superselection import l.json` où `l.json` contient `[]`.
- `git log` : un commit `fix:` par étape, sans `Co-Authored-By`, rien de poussé.

## À faire vérifier par le propriétaire sous Windows

L'agent ne peut pas l'exécuter. À lister dans le compte rendu final :

1. Lancer par le raccourci du bureau avec un carnet abîmé : la fenêtre reste ouverte et
   affiche le message.
2. Ctrl+C à « Son style ? » : retour à l'invite `adversaire >`.
3. Ouvrir `carnet.json` dans Excel (qui verrouille le fichier), taper un nom : message
   d'erreur, pas de fermeture.
4. `update` avec le Wi-Fi coupé : message « Impossible de vérifier… ».
