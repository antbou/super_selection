# Installer superselection sur Windows

Installation sur un poste sans rien de préinstallé : ni Python, ni Git, ni droits
administrateur. Le script installe tout.

## 1. Ouvrir PowerShell

Touche Windows, saisir `PowerShell` (ou `Terminal` sur Windows 11), puis Entrée.

## 2. Coller la ligne suivante, puis Entrée

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/antbou/super_selection/main/install.ps1 | iex"
```

Clic droit dans la fenêtre = coller. La première installation dure environ une minute
(téléchargement de Python). Attendre le message **Termine !**

## 3. Fermer la fenêtre, en ouvrir une nouvelle, puis lancer

```powershell
superselection
```

Au premier lancement, l'outil demande un pseudo (il signe tes traits et notes). Ensuite,
saisir le nom d'un adversaire ; `help` affiche les commandes.

---

## Mettre à jour

Quand l'outil annonce « Nouvelle version disponible », lancer `update`. Une nouvelle
fenêtre effectue la mise à jour et relance l'outil. Le carnet est conservé. Coller à nouveau
la ligne de l'étape 2 donne le même résultat.

## Lancer d'un double-clic

Créer un raccourci sur le bureau vers `C:\Users\<utilisateur>\.local\bin\superselection.exe`.

## Emplacement du carnet

`%APPDATA%\superselection\notebook.json` (avant la 0.15.0 : `carnet.json`, converti
au premier lancement et gardé sous `carnet.v1.bak.json`). Pour ouvrir le dossier : touche Windows + R, coller
`%APPDATA%\superselection`, puis Entrée. Copier ce fichier pour une sauvegarde.

## Désinstaller

```powershell
uv tool uninstall superselection
```

Le carnet reste dans `%APPDATA%\superselection` ; supprimer ce dossier pour tout effacer.

## Dépannage

**« superselection n'est pas reconnu… »**

1. Fermer **toutes** les fenêtres PowerShell et en ouvrir une nouvelle : le PATH n'est lu qu'à l'ouverture.
2. Si l'erreur persiste, ajouter le dossier au PATH à la main :
   - touche Windows, saisir `variables d'environnement`, ouvrir **Modifier les variables
     d'environnement pour votre compte** ;
   - sélectionner **Path** → **Modifier** → **Nouveau**, coller `%USERPROFILE%\.local\bin` ;
   - OK, OK, puis rouvrir PowerShell.

**Les noms chinois ou russes s'affichent en carrés `□`**

Utiliser **Windows Terminal** (inclus dans Windows 11, gratuit sur le Microsoft Store pour
Windows 10). Si ça persiste : Paramètres → profil → Apparence → police **MS Gothic**.

**Nom chinois ou russe impossible à saisir**

Capturer le nom et copier son texte (Outil Capture → **Actions de texte**, ou PowerToys
**Text Extractor** avec `Windows + Maj + T`), puis le coller avec un clic droit.
Détails dans le [README](../README.md#noms-en-caractères-non-saisissables-chinois-russe).

**« (classement indisponible) » au démarrage**

Pas d'internet, ou le site du classement est en panne. Le carnet reste utilisable ;
relancer avec `refresh` plus tard.

**« Carnet illisible »**

Le fichier `notebook.json` (ou l'ancien `carnet.json` à convertir) est abîmé (ou n'est pas un carnet). Le message donne son chemin et
la raison. Le fichier n'est jamais modifié : le corriger, ou le renommer pour repartir d'un
carnet vide. La fenêtre reste ouverte jusqu'à l'appui sur Entrée.

**« Erreur inattendue »**

Le détail technique est écrit dans `erreur.log`, dans le même dossier que `notebook.json`
(le message indique le chemin exact ; en général `%APPDATA%\superselection`). Joindre ce
fichier à tout signalement.

**Le script échoue**

Installation manuelle, en deux commandes :

```powershell
winget install --id=astral-sh.uv -e
```

Fermer et rouvrir PowerShell, puis :

```powershell
uv tool install https://github.com/antbou/super_selection/archive/refs/heads/main.zip
uv tool update-shell
```
