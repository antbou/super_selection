"""Carnet : les adversaires déjà croisés, leurs rencontres et les traits notés."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .texte import sans_controle

VERSION = 1
FENETRE_RENCONTRE = timedelta(minutes=30)  # retaper un nom dans ce délai ne compte pas


class CarnetInvalide(ValueError):
    """Le contenu lu n'a pas la forme d'un carnet."""


@dataclass
class Note:
    texte: str
    maj: str  # date-heure ISO de la dernière modification


@dataclass
class Joueur:
    nom: str
    rencontres: int = 0  # seulement les rencontres du propriétaire du carnet
    derniere: str | None = None  # date ISO de la dernière rencontre
    traits: dict = field(default_factory=dict)  # auteur -> Note
    memo: str = ""  # note perso du propriétaire : jamais exportée ni fusionnée


@dataclass
class Bilan:
    joueurs_ajoutes: int = 0
    traits_ajoutes: int = 0
    traits_maj: int = 0


class Carnet:
    def __init__(self, auteur: str, joueurs: list | None = None):
        self.auteur = auteur
        self._joueurs: dict = {}
        for joueur in joueurs or []:
            self._joueurs[joueur.nom.casefold()] = joueur

    @property
    def joueurs(self) -> list:
        return list(self._joueurs.values())

    def trouver(self, nom: str) -> Joueur | None:
        return self._joueurs.get(nom.casefold())

    def _obtenir(self, nom: str) -> Joueur:
        joueur = self.trouver(nom)
        if joueur is None:
            joueur = Joueur(nom=nom)
            self._joueurs[nom.casefold()] = joueur
        return joueur

    def croiser(self, nom: str, quand: str) -> Joueur:
        """Compte une rencontre, sauf si la précédente date de moins de 30 minutes.

        `quand` est une date-heure ISO ; `derniere` garde alors l'heure (une date seule,
        d'un ancien carnet, ne bloque jamais le comptage).
        """
        joueur = self._obtenir(nom)
        if not _trop_proche(joueur.derniere, quand):
            joueur.rencontres += 1
            joueur.derniere = quand
        return joueur

    def supprimer(self, nom: str) -> Joueur | None:
        """Retire un joueur du carnet (rencontres et traits). Renvoie le joueur retiré."""
        return self._joueurs.pop(nom.casefold(), None)

    def vider(self) -> int:
        """Retire tous les joueurs (le pseudo de l'auteur reste). Renvoie le nombre retiré."""
        nombre = len(self._joueurs)
        self._joueurs.clear()
        return nombre

    def renommer(self, ancien: str, nouveau: str) -> None:
        """Change le nom d'un joueur en gardant ses rencontres et ses traits.

        Lève KeyError si `ancien` est absent, ValueError si `nouveau` désigne un autre joueur.
        """
        joueur = self._joueurs[ancien.casefold()]
        if nouveau.casefold() != ancien.casefold() and nouveau.casefold() in self._joueurs:
            raise ValueError(nouveau)
        del self._joueurs[ancien.casefold()]
        joueur.nom = nouveau
        self._joueurs[nouveau.casefold()] = joueur

    def noter(self, nom: str, texte: str, maintenant: str) -> None:
        """Remplace mon trait pour ce joueur ; un texte vide l'efface."""
        joueur = self._obtenir(nom)
        texte = texte.strip()
        if texte:
            joueur.traits[self.auteur] = Note(texte=texte, maj=maintenant)
        else:
            joueur.traits.pop(self.auteur, None)

    def memoriser(self, nom: str, texte: str) -> None:
        """Remplace ma note perso pour ce joueur ; un texte vide l'efface (sans créer le joueur)."""
        texte = sans_controle(texte).strip()
        if texte:
            self._obtenir(nom).memo = texte
        elif (joueur := self.trouver(nom)) is not None:
            joueur.memo = ""

    def recents(self) -> list:
        return sorted(self.joueurs, key=lambda j: (j.derniere or "", j.nom.casefold()), reverse=True)

    def fusionner(self, autre: "Carnet") -> Bilan:
        """Ajoute les joueurs et les traits d'un autre carnet.

        Mes propres traits ne sont jamais écrasés ; le trait d'un autre auteur
        n'est remplacée que par une version plus récente.
        """
        bilan = Bilan()
        moi = self.auteur.casefold()
        for sien in autre.joueurs:
            if not any(a.casefold() != moi for a in sien.traits):
                continue  # rien d'utile à récupérer sur ce joueur
            mien = self.trouver(sien.nom)
            if mien is None:
                mien = self._obtenir(sien.nom)
                bilan.joueurs_ajoutes += 1
            for auteur, note in sien.traits.items():
                if auteur.casefold() == moi:
                    continue
                actuelle = mien.traits.get(auteur)
                if actuelle is None:
                    mien.traits[auteur] = Note(note.texte, note.maj)
                    bilan.traits_ajoutes += 1
                elif note.maj > actuelle.maj and note.texte != actuelle.texte:
                    mien.traits[auteur] = Note(note.texte, note.maj)
                    bilan.traits_maj += 1
        return bilan

    # --- fichier JSON -----------------------------------------------------

    def vers_dict(self, avec_memos: bool = True) -> dict:
        return {
            "version": VERSION,
            "auteur": self.auteur,
            "joueurs": [
                {
                    "nom": j.nom,
                    "rencontres": j.rencontres,
                    "derniere": j.derniere,
                    "styles": {a: {"texte": n.texte, "maj": n.maj} for a, n in j.traits.items()},
                    **({"memo": j.memo} if avec_memos and j.memo else {}),
                }
                for j in self.recents()
            ],
        }

    @classmethod
    def depuis_dict(cls, brut) -> "Carnet":
        if not isinstance(brut, dict):
            raise CarnetInvalide("le fichier doit contenir un objet JSON")
        auteur = brut.get("auteur", "?")
        if not isinstance(auteur, str):
            raise CarnetInvalide("« auteur » doit être un texte")
        brut_joueurs = brut.get("joueurs", [])
        if not isinstance(brut_joueurs, list):
            raise CarnetInvalide("« joueurs » doit être une liste")
        joueurs = [_lire_joueur(n, j) for n, j in enumerate(brut_joueurs, start=1)]
        return cls(auteur=sans_controle(auteur).strip() or "?", joueurs=joueurs)

    def sauver(self, chemin: Path, avec_memos: bool = True) -> None:
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_name(chemin.name + ".tmp")
        try:
            temporaire.write_text(
                json.dumps(self.vers_dict(avec_memos), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for essai in range(3):
                try:
                    os.replace(temporaire, chemin)
                    return
                except PermissionError:  # Windows : fichier ouvert ailleurs (Excel, antivirus…)
                    if essai == 2:
                        raise
                    time.sleep(0.1)
        except OSError:
            temporaire.unlink(missing_ok=True)
            raise

    @classmethod
    def charger(cls, chemin: Path) -> "Carnet":
        try:
            # OSError (dont FileNotFoundError) remonte ; le reste est un fichier invalide
            brut = json.loads(Path(chemin).read_text(encoding="utf-8"))
        except ValueError as erreur:  # JSONDecodeError, UnicodeDecodeError
            raise CarnetInvalide(f"JSON invalide : {erreur}") from erreur
        return cls.depuis_dict(brut)


def _lire_joueur(numero: int, brut) -> Joueur:
    if not isinstance(brut, dict):
        raise CarnetInvalide(f"joueur n°{numero} : doit être un objet")
    nom = brut.get("nom")
    nom = sans_controle(nom).strip() if isinstance(nom, str) else ""
    if not nom:
        raise CarnetInvalide(f"joueur n°{numero} : « nom » doit être un texte non vide")
    lieu = f"joueur n°{numero} (« {nom} »)"

    rencontres = brut.get("rencontres", 0)
    if isinstance(rencontres, bool) or not isinstance(rencontres, int) or rencontres < 0:
        raise CarnetInvalide(f"{lieu} : « rencontres » doit être un nombre entier positif ou nul")

    derniere = brut.get("derniere")
    if derniere is not None and not (
        isinstance(derniere, str) and re.match(r"\d{4}-\d{2}-\d{2}", derniere)
    ):
        raise CarnetInvalide(f"{lieu} : « derniere » doit être une date AAAA-MM-JJ ou null")

    brut_traits = brut.get("styles", {})
    if not isinstance(brut_traits, dict):
        raise CarnetInvalide(f"{lieu} : « styles » doit être un objet")
    traits = {}
    for auteur, note in brut_traits.items():
        if not isinstance(note, dict) or not isinstance(note.get("texte"), str):
            raise CarnetInvalide(f"{lieu} : le trait de « {auteur} » doit avoir un « texte »")
        maj = note.get("maj", "")
        if not isinstance(maj, str):
            raise CarnetInvalide(f"{lieu} : « maj » du trait de « {auteur} » doit être un texte")
        traits[sans_controle(auteur).strip()] = Note(sans_controle(note["texte"]).strip(), maj)
    memo = brut.get("memo", "")
    if not isinstance(memo, str):
        raise CarnetInvalide(f"{lieu} : « memo » doit être un texte")
    return Joueur(nom=nom, rencontres=rencontres, derniere=derniere, traits=traits, memo=sans_controle(memo).strip())


def _trop_proche(derniere: str | None, quand: str) -> bool:
    if not derniere or len(derniere) <= 10 or len(quand) <= 10:  # pas d'heure connue
        return False
    try:
        ecart = datetime.fromisoformat(quand) - datetime.fromisoformat(derniere)
    except ValueError:
        return False
    return timedelta(0) <= ecart < FENETRE_RENCONTRE
