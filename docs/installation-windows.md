# Installer superselection sur Windows (en partant de zéro)

Ce guide suppose que tu n'as **rien** d'installé : ni Python, ni Git, ni outil de dev.
Compte environ 5 minutes. Tu n'as besoin d'aucun droit administrateur.

## 1. Ouvrir un terminal

- **Windows 11** : touche Windows, tape `Terminal`, puis Entrée.
- **Windows 10** : installe d'abord **Windows Terminal** depuis le Microsoft Store (gratuit),
  puis ouvre-le comme ci-dessus. L'ancienne fenêtre « Invite de commandes » fonctionne aussi,
  mais elle affiche mal les noms chinois ou cyrilliques.

Le terminal s'ouvre sur **PowerShell** : c'est ce qu'il faut.

## 2. Installer uv

`uv` installe tout seul la bonne version de Python et l'outil. Colle cette ligne dans le
terminal (clic droit = coller), puis Entrée :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Alternative, si tu préfères `winget` (déjà présent sur Windows 10/11 à jour) :

```powershell
winget install --id=astral-sh.uv -e
```

**Ferme le terminal et rouvre-le**, sinon Windows ne trouvera pas la commande `uv`. Vérifie :

```powershell
uv --version
```

Tu dois voir quelque chose comme `uv 0.13.4`. Si tu vois « uv n'est pas reconnu… », va à
la section [Dépannage](#dépannage).

## 3. Récupérer le projet

Ton pote t'envoie le dossier du projet en `.zip` (ou tu le télécharges depuis GitHub avec
**Code → Download ZIP**).

1. Clic droit sur le `.zip` → **Extraire tout…** → choisis par exemple `C:\Users\<toi>\superselection`.
2. Ouvre ce dossier dans l'Explorateur : tu dois y voir `pyproject.toml`, `README.md` et `src`.

Si tu as extrait le zip et que tu vois un seul sous-dossier (par ex. `superselection-main`),
entre dedans : c'est lui, le dossier du projet.

## 4. Installer superselection

Ouvre un terminal **dans le dossier du projet** :

- **Windows 11** : dans l'Explorateur, clic droit dans le dossier → **Ouvrir dans le Terminal**.
- Sinon : dans le terminal, tape `cd` suivi du chemin du dossier, par exemple :

  ```powershell
  cd C:\Users\<toi>\superselection
  ```

Puis :

```powershell
uv tool install .
```

(Le point final compte : il veut dire « ce dossier ».) La première fois, uv télécharge Python,
ce qui prend une minute.

## 5. Mettre la commande dans le PATH

uv installe la commande dans `C:\Users\<toi>\.local\bin`. Pour que Windows la trouve depuis
n'importe quel dossier, lance une fois :

```powershell
uv tool update-shell
```

**Ferme le terminal et rouvre-le.**

## 6. Lancer

Dans n'importe quel terminal :

```powershell
superselection
```

Au premier lancement, l'outil te demande ton pseudo (il signe tes notes quand tu partages ton
carnet). Ensuite tape le nom d'un adversaire, et `aide` pour voir toutes les commandes.

Astuce : pour lancer l'outil d'un double-clic, crée un raccourci sur le bureau vers
`C:\Users\<toi>\.local\bin\superselection.exe`.

## Mettre à jour

Remplace le dossier du projet par la nouvelle version, ouvre un terminal dedans et lance :

```powershell
uv tool install . --reinstall
```

Ton carnet est conservé : il n'est pas dans le dossier du projet.

## Où est mon carnet ?

Dans `%APPDATA%\superselection\carnet.json`. Pour l'ouvrir : touche Windows + R, colle
`%APPDATA%\superselection`, puis Entrée. Copie ce fichier pour faire une sauvegarde.

## Désinstaller

```powershell
uv tool uninstall superselection
```

Le carnet reste dans `%APPDATA%\superselection` ; supprime ce dossier si tu veux tout effacer.

## Dépannage

**« uv n'est pas reconnu » ou « superselection n'est pas reconnu »**

1. Ferme **toutes** les fenêtres de terminal et rouvre-en une : le PATH n'est lu qu'à l'ouverture.
2. Toujours pas ? Lance `uv tool update-shell` (si `uv` marche), puis rouvre le terminal.
3. En dernier recours, ajoute le dossier au PATH à la main :
   - touche Windows, tape `variables d'environnement`, ouvre **Modifier les variables
     d'environnement pour votre compte** ;
   - sélectionne **Path** → **Modifier** → **Nouveau**, colle `%USERPROFILE%\.local\bin` ;
   - OK, OK, puis rouvre le terminal.

**« l'exécution de scripts est désactivée sur ce système »**

Utilise exactement la commande de l'étape 2 (avec `-ExecutionPolicy ByPass`), ou passe par
`winget`.

**Les noms chinois ou russes s'affichent en carrés `□`**

Utilise Windows Terminal (pas l'ancienne console). Si ça persiste : Paramètres de Windows
Terminal → ton profil → Apparence → police **Cascadia Mono** ou **MS Gothic**.

**« Chargement du classement… (classement indisponible) »**

Pas d'accès internet, ou le site du classement est en panne. L'outil fonctionne quand même
(carnet, styles) ; tape `maj` plus tard pour recharger le classement.

**`uv tool install .` dit qu'il ne trouve pas `pyproject.toml`**

Tu n'es pas dans le bon dossier : tape `dir` et vérifie que tu vois `pyproject.toml`. Sinon,
refais l'étape 4 avec le bon chemin.
