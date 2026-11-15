"""Version installée, version publiée sur GitHub, et mise à jour."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from typing import Callable

DEPOT = "antbou/super_selection"
ZIP = f"https://github.com/{DEPOT}/archive/refs/heads/main.zip"
PYPROJECT = f"https://raw.githubusercontent.com/{DEPOT}/main/pyproject.toml"
INSTALL_PS1 = f"https://raw.githubusercontent.com/{DEPOT}/main/install.ps1"

LireTexte = Callable[[], str]


def version_installee() -> str:
    try:
        return version("superselection")
    except PackageNotFoundError:
        return "0.0.0"


def fetch_pyproject() -> str:
    requete = urllib.request.Request(PYPROJECT, headers={"User-Agent": "superselection"})
    with urllib.request.urlopen(requete, timeout=3) as reponse:
        return reponse.read().decode("utf-8")


def _nombres(v: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", v))


def est_plus_recente(a: str, b: str) -> bool:
    """Vrai si la version a est plus récente que b."""
    return _nombres(a) > _nombres(b)


def lire_version_publiee(lire: LireTexte) -> str | None:
    try:
        texte = lire()
    except Exception:  # pas d'internet, GitHub en panne… : on ne dérange pas
        return None
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', texte)
    return m.group(1) if m else None


def nouvelle_version(installee: str, lire: LireTexte) -> str | None:
    """La version publiée si elle est plus récente que celle installée, sinon None."""
    publiee = lire_version_publiee(lire)
    return publiee if publiee and est_plus_recente(publiee, installee) else None


def etat_version(installee: str, lire: LireTexte) -> tuple:
    """(état, version publiée) avec état = "injoignable", "a_jour" ou "nouvelle"."""
    publiee = lire_version_publiee(lire)
    if publiee is None:
        return "injoignable", None
    if est_plus_recente(publiee, installee):
        return "nouvelle", publiee
    return "a_jour", publiee


def lancer_mise_a_jour() -> tuple:
    """Lance la mise à jour. Renvoie (réussi, message) ; en cas de succès l'application doit ensuite quitter."""
    try:
        if os.name == "nt":
            # Sous Windows, superselection.exe est verrouillé tant qu'il tourne : on relance
            # l'installateur dans une nouvelle fenêtre, qui attend que celle-ci soit fermée.
            # On relance par le chemin complet (le PATH hérité n'a pas toujours .local\bin).
            commande = (
                f"Start-Sleep 2; irm {INSTALL_PS1} | iex; "
                '$exe = "$env:USERPROFILE\\.local\\bin\\superselection.exe"; '
                "if (Test-Path $exe) { & $exe } else { superselection }"
            )
            subprocess.Popen(
                ["powershell", "-NoExit", "-ExecutionPolicy", "ByPass", "-Command", commande],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return True, "Mise à jour lancée dans une nouvelle fenêtre. Celle-ci va se fermer."
        uv = shutil.which("uv")
        if uv is None:
            return False, f"uv introuvable. Mise à jour manuelle : uv tool install --force {ZIP}"
        resultat = subprocess.run([uv, "tool", "install", "--force", "--reinstall", "--refresh", ZIP])
    except OSError as erreur:
        return False, f"Impossible de lancer la mise à jour : {erreur.strerror or erreur}"
    if resultat.returncode != 0:
        return False, "La mise à jour a échoué (voir le message ci-dessus)."
    return True, "Mise à jour terminée. Relancer superselection."
