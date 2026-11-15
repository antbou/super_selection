"""Mots-clés de style connus et leur emoji (le style reste un texte libre)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    nom: str  # mot conseillé, proposé par l'auto-complétion
    emoji: str
    sens: str  # explication affichée par la commande `styles`
    variantes: tuple = ()  # autres orthographes reconnues


TAGS = (
    Tag("aggressive", "🔥", "attaque tout le temps", ("aggresive", "agressive", "aggro", "agro", "agressif")),
    Tag("defence", "🛡️", "joue défensif, tient bien ses positions", ("defense", "def", "defensive", "défense", "défensif", "defensif")),
    Tag("noob", "🐣", "débutant / faible", ("nul", "newbie", "bad")),
    Tag("tryhard", "😤", "joue à fond, ne lâche rien", ("tryharder",)),
    Tag("pro", "👑", "très fort", ("strong", "fort")),
)

_PAR_MOT = {}
for _tag in TAGS:
    for _mot in (_tag.nom, *_tag.variantes):
        _PAR_MOT[_mot.casefold()] = _tag

_MOT = re.compile(r"\w+", re.UNICODE)


def decorer(texte: str) -> str:
    """Ajoute l'emoji devant chaque mot-clé reconnu : « aggressive » -> « 🔥 aggressive »."""

    def remplacer(m: re.Match) -> str:
        tag = _PAR_MOT.get(m.group(0).casefold())
        return f"{tag.emoji} {m.group(0)}" if tag else m.group(0)

    return _MOT.sub(remplacer, texte)


def tags_commencant_par(debut: str) -> list:
    debut = debut.casefold()
    return [t for t in TAGS if t.nom.startswith(debut)]


def aide_styles() -> str:
    lignes = ["Mots-clés de style (Tab les complète quand tu notes un style) :"]
    for t in TAGS:
        lignes.append(f"  {t.emoji}  {t.nom:<11} {t.sens}")
    lignes.append("Tu peux en mettre plusieurs et ajouter du texte : « aggressive, tryhard, rush archers ».")
    return "\n".join(lignes)
