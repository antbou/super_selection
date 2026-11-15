"""Carnet : les adversaires déjà croisés, leurs rencontres et les styles notés."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

VERSION = 1


@dataclass
class Note:
    texte: str
    maj: str  # date-heure ISO de la dernière modification


@dataclass
class Joueur:
    nom: str
    rencontres: int = 0  # seulement les rencontres du propriétaire du carnet
    derniere: str | None = None  # date ISO de la dernière rencontre
    styles: dict = field(default_factory=dict)  # auteur -> Note


@dataclass
class Bilan:
    joueurs_ajoutes: int = 0
    notes_ajoutees: int = 0
    notes_maj: int = 0


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

    def croiser(self, nom: str, jour: str) -> Joueur:
        joueur = self._obtenir(nom)
        joueur.rencontres += 1
        joueur.derniere = jour
        return joueur

    def noter(self, nom: str, texte: str, maintenant: str) -> None:
        """Remplace mon style pour ce joueur ; un texte vide l'efface."""
        joueur = self._obtenir(nom)
        texte = texte.strip()
        if texte:
            joueur.styles[self.auteur] = Note(texte=texte, maj=maintenant)
        else:
            joueur.styles.pop(self.auteur, None)

    def recents(self) -> list:
        return sorted(self.joueurs, key=lambda j: (j.derniere or "", j.nom.casefold()), reverse=True)

    def fusionner(self, autre: "Carnet") -> Bilan:
        """Ajoute les joueurs et les notes d'un autre carnet.

        Mes propres notes ne sont jamais écrasées ; la note d'un autre auteur
        n'est remplacée que par une version plus récente.
        """
        bilan = Bilan()
        moi = self.auteur.casefold()
        for sien in autre.joueurs:
            if not any(a.casefold() != moi for a in sien.styles):
                continue  # rien d'utile à récupérer sur ce joueur
            mien = self.trouver(sien.nom)
            if mien is None:
                mien = self._obtenir(sien.nom)
                bilan.joueurs_ajoutes += 1
            for auteur, note in sien.styles.items():
                if auteur.casefold() == moi:
                    continue
                actuelle = mien.styles.get(auteur)
                if actuelle is None:
                    mien.styles[auteur] = Note(note.texte, note.maj)
                    bilan.notes_ajoutees += 1
                elif note.maj > actuelle.maj and note.texte != actuelle.texte:
                    mien.styles[auteur] = Note(note.texte, note.maj)
                    bilan.notes_maj += 1
        return bilan

    # --- fichier JSON -----------------------------------------------------

    def vers_dict(self) -> dict:
        return {
            "version": VERSION,
            "auteur": self.auteur,
            "joueurs": [
                {
                    "nom": j.nom,
                    "rencontres": j.rencontres,
                    "derniere": j.derniere,
                    "styles": {a: {"texte": n.texte, "maj": n.maj} for a, n in j.styles.items()},
                }
                for j in self.recents()
            ],
        }

    @classmethod
    def depuis_dict(cls, brut: dict) -> "Carnet":
        joueurs = [
            Joueur(
                nom=j["nom"],
                rencontres=j.get("rencontres", 0),
                derniere=j.get("derniere"),
                styles={a: Note(n["texte"], n.get("maj", "")) for a, n in j.get("styles", {}).items()},
            )
            for j in brut.get("joueurs", [])
        ]
        return cls(auteur=brut.get("auteur", "?"), joueurs=joueurs)

    def sauver(self, chemin: Path) -> None:
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_name(chemin.name + ".tmp")
        temporaire.write_text(
            json.dumps(self.vers_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporaire, chemin)

    @classmethod
    def charger(cls, chemin: Path) -> "Carnet":
        return cls.depuis_dict(json.loads(Path(chemin).read_text(encoding="utf-8")))
