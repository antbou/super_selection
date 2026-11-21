"""Nettoyage du texte venu de l'extérieur (fichiers, API, saisie)."""

from __future__ import annotations

import unicodedata


def sans_controle(texte: str) -> str:
    """Retire les caractères de contrôle (catégorie Unicode Cc), dont les séquences d'échappement."""
    return "".join(c for c in texte if unicodedata.category(c) != "Cc")


def _latin(c: str) -> bool:
    return ("0" <= c <= "9") or unicodedata.name(c, "").startswith("LATIN")


def cle_alphabetique(nom: str) -> tuple:
    """Tri alphabétique sans casse ni accents, en ignorant les signes (« [IMP] Pizza » à I).
    Les noms qui ne commencent pas par une lettre latine ou un chiffre (chinois, cyrillique…) vont à la fin."""
    base = "".join(
        c for c in unicodedata.normalize("NFKD", nom).casefold() if c.isalnum()
    )
    return (not (base and _latin(base[0])), base, nom.casefold())


def largeur(texte: str) -> int:
    """Largeur à l'écran : les caractères larges (chinois, japonais…) prennent deux colonnes."""
    return sum(
        0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1
        for c in texte
    )


def ajuster(texte: str, colonnes: int) -> str:
    """Complète avec des espaces jusqu'à `colonnes` colonnes d'écran."""
    return texte + " " * max(0, colonnes - largeur(texte))


def tronquer(texte: str, maximum: int) -> str:
    return texte if len(texte) <= maximum else texte[: maximum - 1] + "…"
