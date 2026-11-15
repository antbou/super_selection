# superselection

CLI Python (uv) : carnet d'adversaires pour War Selection. Tout le texte visible par
l'utilisateur, le code (noms) et la doc sont en **français**.

## Commandes

- Tests : `uv run pytest`
- Lancer : `uv run superselection` (données isolées : `SUPERSELECTION_DIR=/tmp/x uv run superselection`)

## Architecture

- `classement.py` : API top 100 (`fetch_http`), détection de la saison, cache hors ligne.
- `carnet.py` : modèle `Carnet`/`Joueur`/`Note`, JSON, fusion.
- `app.py` : commandes pures qui renvoient du texte (`App`, `analyser`). Toute logique ici, testée.
- `cli.py` : seule couche terminal (prompt_toolkit, auto-complétion, `main`). Garder mince.

Vocabulaire : `GLOSSARY.md`. Utiliser ces termes dans le code et la doc.

Décisions : `docs/adr/` (une décision par fichier, numérotée). Les lire avant de remettre un choix en cause ; ajouter un ADR quand une décision est difficile à défaire, surprenante, et issue d'un vrai compromis.

## Règles

- TDD : écrire le test d'abord (`tests/`), le réseau est toujours injecté (`Fetcher`), jamais appelé en test.
- Doit marcher sous Windows : `pathlib`, `encoding="utf-8"` partout, pas de commande shell, pas de dépendance POSIX.
- Rester simple : l'utilisateur veut taper un nom, voir le rang, noter un style. Pas de mode 2v2 spécial.
- Commandes en anglais (`show`, `list`, `help`…), tous les messages en français.
- Installation Windows = une ligne (`install.ps1`, garder ce script en ASCII). Ne rien ajouter qui demande Python ou Git à l'utilisateur.
- Les notes du propriétaire ne sont jamais écrasées par un import.
- Chaque changement visible publié sur `main` : augmenter `version` dans `pyproject.toml` (+ `uv lock`), sinon personne n'est prévenu. `update` est la seule commande qui lance un programme externe (uv / PowerShell).
- Couleurs : seulement via `couleurs.peindre` ; le texte doit rester identique sans couleur (`sans_couleur`).
