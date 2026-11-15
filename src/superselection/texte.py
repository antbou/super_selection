"""Nettoyage du texte venu de l'extérieur (fichiers, API, saisie)."""

from __future__ import annotations

import unicodedata


def sans_controle(texte: str) -> str:
    """Retire les caractères de contrôle (catégorie Unicode Cc), dont les séquences d'échappement."""
    return "".join(c for c in texte if unicodedata.category(c) != "Cc")
