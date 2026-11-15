"""Classement officiel top 100 de War Selection (API publique ratings.warselect.io)."""

from __future__ import annotations

import http.client
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .texte import sans_controle

API = "https://ratings.warselect.io/webapi/top100{mode}?season={saison}"
MODES = ("1v1", "2v2")

# Un fetcher renvoie les lignes {"name", "rating"} d'un mode pour une saison
# (liste vide si la saison n'existe pas encore). Injecté pour les tests.
Fetcher = Callable[[str, int], list]


class ErreurClassement(Exception):
    pass


def lire_reponse(corps) -> list:
    """Extrait les lignes valides {"name", "rating"} d'une réponse de l'API."""
    if not isinstance(corps, dict):
        raise ErreurClassement("réponse inattendue de l'API")
    if corps.get("error", 0) != 0 or not isinstance(corps.get("data"), list):
        raise ErreurClassement(str(corps.get("description") or "réponse inattendue de l'API"))
    lignes = []
    for ligne in corps["data"]:
        if not isinstance(ligne, dict):
            continue
        nom, points = ligne.get("name"), ligne.get("rating")
        if not isinstance(nom, str) or isinstance(points, bool) or not isinstance(points, int):
            continue
        nom = sans_controle(nom).strip()
        if nom:
            lignes.append({"name": nom, "rating": points})
    return lignes


def fetch_http(mode: str, saison: int) -> list:
    requete = urllib.request.Request(
        API.format(mode=mode, saison=saison), headers={"User-Agent": "superselection"}
    )
    try:
        with urllib.request.urlopen(requete, timeout=10) as reponse:
            corps = json.load(reponse)
    except http.client.HTTPException as erreur:
        raise ErreurClassement(f"réponse HTTP invalide ({erreur})") from erreur
    return lire_reponse(corps)


@dataclass(frozen=True)
class Rang:
    position: int
    points: int


@dataclass
class Classement:
    saison: int
    lignes: dict  # mode -> liste de {"name", "rating"}, dans l'ordre du classement
    recupere_le: str

    def rangs(self, nom: str, mode: str) -> list:
        """Tous les rangs portant ce nom (des homonymes existent), dans l'ordre du classement."""
        cle = nom.casefold()
        return [
            Rang(position, ligne["rating"])
            for position, ligne in enumerate(self.lignes.get(mode, []), start=1)
            if ligne["name"].casefold() == cle
        ]

    def rang(self, nom: str, mode: str) -> Rang | None:
        """Le premier rang de ce nom, ou None."""
        trouves = self.rangs(nom, mode)
        return trouves[0] if trouves else None

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
        saison, lignes, recupere_le = brut["saison"], brut["lignes"], brut["recupere_le"]
        if (
            isinstance(saison, bool)
            or not isinstance(saison, int)
            or not isinstance(recupere_le, str)
            or not isinstance(lignes, dict)
        ):
            return None
        for mode in MODES:
            for ligne in lignes.get(mode, []):
                if not isinstance(ligne["name"], str) or not isinstance(ligne["rating"], int):
                    return None
        return Classement(saison=saison, lignes=lignes, recupere_le=recupere_le)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
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
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(
                {"saison": saison, "lignes": lignes, "recupere_le": maintenant}, ensure_ascii=False
            ),
            encoding="utf-8",
        )
    except OSError:
        pass  # cache impossible à écrire : le classement téléchargé reste utilisé
    return classement, None


def charger_saison(
    dossier: Path, fetch: Fetcher, saison: int, maintenant: str
) -> Classement | None:
    """Classement d'une saison passée (ADR 0012). Une saison finie ne change plus : cache définitif.

    Renvoie None si la saison n'existe pas ou si le réseau échoue sans cache.
    """
    cache = dossier / f"saison-{saison}.json"
    deja = _lire_cache(cache)
    if deja and deja.saison == saison:
        return deja
    try:
        lignes = {mode: fetch(mode, saison) for mode in MODES}
    except (OSError, ErreurClassement, ValueError):
        return None
    if not lignes["1v1"]:
        return None
    classement = Classement(saison=saison, lignes=lignes, recupere_le=maintenant)
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(
                {"saison": saison, "lignes": lignes, "recupere_le": maintenant}, ensure_ascii=False
            ),
            encoding="utf-8",
        )
    except OSError:
        pass
    return classement
