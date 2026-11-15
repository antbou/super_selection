# Installer superselection sur Windows

Pour quelqu'un qui n'a **rien** d'installé. Pas de Python, pas de Git, pas de droits
administrateur : le script s'occupe de tout.

## 1. Ouvrir PowerShell

Touche Windows, tape `PowerShell` (ou `Terminal` sur Windows 11), puis Entrée.

## 2. Coller cette ligne, puis Entrée

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/antbou/super_selection/main/install.ps1 | iex"
```

Clic droit dans la fenêtre = coller. La première fois, ça prend environ une minute (Python
est téléchargé). Attends le message **Terminé !**

## 3. Fermer la fenêtre, en rouvrir une, et lancer

```powershell
superselection
```

Au premier lancement, l'outil te demande ton pseudo (il signe tes notes quand tu partages ton
carnet). Ensuite tape le nom d'un adversaire, et `help` pour voir les commandes.

C'est tout.

---

## Mettre à jour

Recolle la même ligne qu'à l'étape 2. Ton carnet est conservé.

## Lancer d'un double-clic

Crée un raccourci sur le bureau vers `C:\Users\<toi>\.local\bin\superselection.exe`.

## Où est mon carnet ?

`%APPDATA%\superselection\carnet.json`. Pour ouvrir le dossier : touche Windows + R, colle
`%APPDATA%\superselection`, puis Entrée. Copie ce fichier pour faire une sauvegarde.

## Désinstaller

```powershell
uv tool uninstall superselection
```

Le carnet reste dans `%APPDATA%\superselection` ; supprime ce dossier pour tout effacer.

## Dépannage

**« superselection n'est pas reconnu… »**

1. Ferme **toutes** les fenêtres PowerShell et rouvre-en une : le PATH n'est lu qu'à l'ouverture.
2. Toujours pas ? Ajoute le dossier au PATH à la main :
   - touche Windows, tape `variables d'environnement`, ouvre **Modifier les variables
     d'environnement pour votre compte** ;
   - sélectionne **Path** → **Modifier** → **Nouveau**, colle `%USERPROFILE%\.local\bin` ;
   - OK, OK, puis rouvre PowerShell.

**Les noms chinois ou russes s'affichent en carrés `□`**

Utilise **Windows Terminal** (inclus dans Windows 11, gratuit sur le Microsoft Store pour
Windows 10). Si ça persiste : Paramètres → ton profil → Apparence → police **MS Gothic**.

**« (classement indisponible) » au démarrage**

Pas d'internet, ou le site du classement est en panne. Le carnet fonctionne quand même ;
tape `refresh` plus tard.

**Le script échoue**

Installation manuelle, en deux commandes :

```powershell
winget install --id=astral-sh.uv -e
```

Ferme et rouvre PowerShell, puis :

```powershell
uv tool install https://github.com/antbou/super_selection/archive/refs/heads/main.zip
uv tool update-shell
```
