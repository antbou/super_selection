"""Couleurs du terminal (codes ANSI). Le texte reste identique une fois les couleurs retirées."""

from __future__ import annotations

import re

# rôle -> code ANSI
ROLES = {
    "nom": "1;96",  # nom du joueur : cyan vif, gras
    "top10": "1;93",  # rang 1 à 10 : jaune vif, gras
    "top50": "1;92",  # rang 11 à 50 : vert vif
    "top100": "92",  # rang 51 à 100 : vert
    "hors": "2",  # hors top 100 : grisé
    "info": "2",  # texte secondaire : grisé
    "auteur": "95",  # pseudos des auteurs (« Antho », « Kevin ») : magenta
    "trait": "97",  # texte du trait : blanc
    "commande": "93",  # commandes dans l'aide : jaune
    "ok": "92",  # confirmation : vert
    "erreur": "91",  # erreur : rouge
    "invite": "1;96",  # « adversaire > »
}

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def peindre(texte: str, role: str, actif: bool = True) -> str:
    if not actif or not texte:
        return texte
    return f"\x1b[{ROLES[role]}m{texte}\x1b[0m"


def sans_couleur(texte: str) -> str:
    return _ANSI.sub("", texte)


def role_rang(position: int) -> str:
    if position <= 10:
        return "top10"
    if position <= 50:
        return "top50"
    return "top100"


def colorer_aide(texte: str) -> str:
    """Met en jaune le premier mot des lignes indentées de l'aide (les commandes)."""
    return re.sub(r"(?m)^(  )(\S+(?: <\w+>)?)", lambda m: m.group(1) + peindre(m.group(2), "commande"), texte)
