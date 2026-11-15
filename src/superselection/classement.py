"""Classement officiel top 100 de War Selection (API publique ratings.warselect.io)."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

API = "https://ratings.warselect.io/webapi/top100{mode}?season={saison}"
MODES = ("1v1", "2v2")

# Un fetcher renvoie les lignes {"name", "rating"} d'un mode pour une saison
# (liste vide si la saison n'existe pas encore). Injecté pour les tests.
Fetcher = Callable[[str, int], list]


class ErreurClassement(Exception):
    pass


def fetch_http(mode: str, saison: int) -> list:
    requete = urllib.request.Request(
        API.format(mode=mode, saison=saison), headers={"User-Agent": "superselection"}
    )
    with urllib.request.urlopen(requete, timeout=10) as reponse:
        corps = json.load(reponse)
    if corps.get("error", 0) != 0 or not isinstance(corps.get("data"), list):
        raise ErreurClassement(corps.get("description") or "réponse inattendue de l'API")
    return corps["data"]


@dataclass(frozen=True)
class Rang:
    position: int
    points: int


@dataclass
class Classement:
    saison: int
    lignes: dict  # mode -> liste de {"name", "rating"}, dans l'ordre du classement
    recupere_le: str

    def rang(self, nom: str, mode: str) -> Rang | None:
        cle = nom.casefold()
        for position, ligne in enumerate(self.lignes.get(mode, []), start=1):
            if ligne["name"].casefold() == cle:
                return Rang(position, ligne["rating"])
        return None

    def nom_officiel(self, nom: str) -> str | None:
        cle = nom.casefold()
        for mode in MODES:
            for ligne in self.lignes.get(mode, []):
                if ligne["name"].casefold() == cle:
                    return ligne["name"]
        return None

    def noms(self) -> set:
        return {ligne["name"] for mode in MODES for ligne in self.lignes.get(mode, [])}


def derniere_saison(fetch: Fetcher, depuis: int | None = None) -> int:
    """Numéro de la saison la plus récente qui a des joueurs classés en 1v1."""
    deja_vues: dict = {}

    def existe(saison: int) -> bool:
        if saison not in deja_vues:
            deja_vues[saison] = len(fetch("1v1", saison)) > 0
        return deja_vues[saison]

    if depuis and existe(depuis):
        saison = depuis
        while existe(saison + 1):
            saison += 1
        return saison

    if not existe(1):
        raise ErreurClassement("aucune saison trouvée")
    bas, haut = 1, 2
    while existe(haut):
        bas, haut = haut, haut * 2
    while haut - bas > 1:
        milieu = (bas + haut) // 2
        if existe(milieu):
            bas = milieu
        else:
            haut = milieu
    return bas


def _lire_cache(cache: Path) -> Classement | None:
    try:
        brut = json.loads(cache.read_text(encoding="utf-8"))
        return Classement(saison=brut["saison"], lignes=brut["lignes"], recupere_le=brut["recupere_le"])
    except (OSError, ValueError, KeyError):
        return None


def charger_classement(
    cache: Path, fetch: Fetcher, maintenant: str
) -> tuple:
    """Télécharge la saison en cours ; en cas d'échec, se rabat sur le cache.

    Renvoie (classement ou None, message à afficher ou None).
    """
    ancien = _lire_cache(cache)
    try:
        saison = derniere_saison(fetch, depuis=ancien.saison if ancien else None)
        lignes = {mode: fetch(mode, saison) for mode in MODES}
    except (OSError, ErreurClassement, ValueError) as erreur:
        if ancien:
            return ancien, f"(hors ligne : classement du {ancien.recupere_le[:16].replace('T', ' ')})"
        return None, f"(classement indisponible : {erreur})"

    classement = Classement(saison=saison, lignes=lignes, recupere_le=maintenant)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps(
            {"saison": saison, "lignes": lignes, "recupere_le": maintenant}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    return classement, None
