# Installation avec uv depuis le zip GitHub, sans PyPI ni .exe

L'outil s'installe avec `uv tool install <zip de main sur GitHub>`. Sous Windows, on passe par une seule ligne PowerShell (`install.ps1`) qui installe uv si besoin et règle le PATH. uv télécharge lui-même Python, donc l'utilisateur n'a rien à installer : ni Python, ni Git, ni droits administrateur.

## Options écartées

- **PyPI** : demande un compte et une publication à chaque version, pour un outil entre amis.
- **.exe PyInstaller** : plus lourd à construire, souvent signalé par les antivirus, et sans mise à jour simple.

## Conséquences

- Publier une version, c'est pousser sur `main`.
- `install.ps1` doit rester en ASCII (PowerShell 5.1 lit mal l'UTF-8 sans BOM) ; les fins de ligne sont indifférentes (avec `irm … | iex` le script passe comme une chaîne).
