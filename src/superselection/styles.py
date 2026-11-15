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
    Tag("aggressive", "🔥", "attaque tout le temps", ("aggresive", "agressive", "aggro", "agressif")),
    Tag("rush", "⚡", "attaque très tôt", ("rusher", "early")),
    Tag("defence", "🛡️", "joue défensif, tient bien ses positions", ("defense", "def", "defensive", "défensif", "defensif")),
    Tag("passive", "😴", "attend, attaque peu", ("passif", "afk")),
    Tag("turtle", "🐢", "s'enferme et construit", ("tortue",)),
    Tag("eco", "💰", "mise sur l'économie", ("economy", "boom", "greedy")),
    Tag("spam", "🔁", "spamme une seule unité", ()),
    Tag("cheese", "🧀", "stratégie piège / surprise", ("cheesy",)),
    Tag("micro", "🎯", "très bon contrôle des unités", ()),
    Tag("pro", "👑", "très fort", ("strong", "fort", "good", "tryhard")),
    Tag("noob", "🐣", "débutant / faible", ("nul", "bad", "newbie", "weak")),
    Tag("smurf", "🎭", "compte secondaire d'un bon joueur", ()),
    Tag("toxic", "☠️", "insulte / mauvais joueur", ("toxique", "troll")),
    Tag("team", "🤝", "bon joueur d'équipe en 2v2", ("teamplay",)),
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
    lignes.append("Le style reste libre : tu peux écrire « aggressive, rush archers, noob en 2v2 ».")
    return "\n".join(lignes)
