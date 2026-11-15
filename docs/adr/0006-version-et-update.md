# Nouvelle version détectée via pyproject.toml sur main, update dans une nouvelle fenêtre sous Windows

Au lancement, l'outil lit `version` dans le `pyproject.toml` de `main` (raw.githubusercontent.com) et prévient si elle est plus récente que la version installée. Cette vérification tourne pendant le chargement du classement et ne dit rien en cas d'erreur. Il n'y a pas de releases GitHub : c'est cohérent avec l'installation depuis le zip de `main` (ADR 0005). Il faut donc augmenter `version` à chaque changement publié, sinon personne n'est prévenu.

`update` réinstalle avec uv. Sous Windows, `superselection.exe` est verrouillé tant qu'il tourne : `update` ouvre donc une nouvelle fenêtre PowerShell qui relance `install.ps1` puis l'outil, et la fenêtre actuelle se ferme. `update` est la seule commande qui lance un programme externe.

## Conséquences

Les installations en 0.1.0 (avant cette fonction) ne sont jamais prévenues : il faut les réinstaller une fois à la main.
