"""Carnet : les adversaires déjà croisés, leurs rencontres, leur trait et leur note communs.

Le trait et la note d'un joueur sont communs à tous ceux qui s'échangent le carnet : chaque
modification ajoute une **version** signée et datée à l'**historique**, et la version la plus
récente l'emporte (ADR 0022). Le fichier est au format 2, champs en anglais (ADR 0023).
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .texte import sans_controle

VERSION = 2
FICHIER = "notebook.json"
ANCIEN_FICHIER = "carnet.json"  # format 1, migré au premier lancement
SAUVEGARDE_ANCIEN = "carnet.v1.bak.json"
FENETRE_RENCONTRE = timedelta(minutes=30)  # retaper un nom dans ce délai ne compte pas
CHAMPS = ("trait", "note")


class CarnetInvalide(ValueError):
    """Le contenu lu n'a pas la forme d'un carnet."""


@dataclass(frozen=True)
class Revision:
    """Une version d'un trait ou d'une note : texte (vide = effacé), auteur, date-heure ISO."""

    texte: str
    auteur: str
    maj: str


@dataclass
class Rencontres:
    """Les rencontres d'une autre personne avec un joueur (importées, jamais modifiées ici)."""

    nombre: int
    derniere: str | None


@dataclass
class Joueur:
    nom: str
    rencontres: int = 0  # mes rencontres (propriétaire du carnet)
    derniere: str | None = None  # date ISO de ma dernière rencontre
    autres_rencontres: dict = field(default_factory=dict)  # auteur -> Rencontres
    historique_trait: list = field(default_factory=list)  # Revision, de la plus ancienne à la plus récente
    historique_note: list = field(default_factory=list)

    def historique(self, champ: str) -> list:
        return self.historique_trait if champ == "trait" else self.historique_note

    def version(self, champ: str) -> Revision | None:
        """La version actuelle (la plus récente) du trait ou de la note."""
        historique = self.historique(champ)
        return historique[-1] if historique else None

    @property
    def trait(self) -> str:
        return v.texte if (v := self.version("trait")) else ""

    @property
    def note(self) -> str:
        return v.texte if (v := self.version("note")) else ""

    def auteurs(self) -> list:
        """Tous ceux qui ont écrit une version du trait ou de la note, sans doublon à la casse près."""
        vus = {}
        for r in [*self.historique_trait, *self.historique_note]:
            vus.setdefault(r.auteur.casefold(), r.auteur)
        return list(vus.values())


@dataclass
class Conflit:
    """Chacun a modifié de son côté : ma version actuelle et la sienne, nouvelle pour moi, diffèrent."""

    nom: str
    champ: str  # "trait" ou "note"
    mienne: Revision
    sienne: Revision


@dataclass
class Bilan:
    joueurs_ajoutes: int = 0
    versions_ajoutees: int = 0
    traits_maj: int = 0  # trait actuel changé par l'import
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
        """Retire un joueur du carnet (rencontres et historiques). Renvoie le joueur retiré."""
        return self._joueurs.pop(nom.casefold(), None)

    def vider(self) -> int:
        """Retire tous les joueurs (le pseudo de l'auteur reste). Renvoie le nombre retiré."""
        nombre = len(self._joueurs)
        self._joueurs.clear()
        return nombre

    def renommer(self, ancien: str, nouveau: str) -> None:
        """Change le nom d'un joueur en gardant ses rencontres et ses historiques.

        Lève KeyError si `ancien` est absent, ValueError si `nouveau` désigne un autre joueur.
        """
        joueur = self._joueurs[ancien.casefold()]
        if nouveau.casefold() != ancien.casefold() and nouveau.casefold() in self._joueurs:
            raise ValueError(nouveau)
        del self._joueurs[ancien.casefold()]
        joueur.nom = nouveau
        self._joueurs[nouveau.casefold()] = joueur

    def imposer(self, nom: str, champ: str, texte: str, maintenant: str) -> bool:
        """Ajoute ma version du trait ou de la note si elle change la valeur actuelle ; vide = effacer.

        Ma version passe toujours devant (même si une version importée est datée du futur, horloge
        décalée). Un texte vide pour un joueur absent ne crée pas le joueur. Renvoie True si ajoutée.
        """
        texte = sans_controle(texte).strip()
        joueur = self.trouver(nom)
        if joueur is None and not texte:
            return False
        joueur = joueur or self._obtenir(nom)
        historique = joueur.historique(champ)
        actuelle = historique[-1] if historique else None
        if (actuelle.texte if actuelle else "") == texte:
            return False
        maj = max(maintenant, actuelle.maj) if actuelle else maintenant
        historique.append(Revision(texte, self.auteur, maj))
        return True

    def noter(self, nom: str, texte: str, maintenant: str) -> bool:
        """Nouvelle version du trait ; un texte vide l'efface (l'historique garde l'ancienne)."""
        return self.imposer(nom, "trait", texte, maintenant)

    def memoriser(self, nom: str, texte: str, maintenant: str = "") -> bool:
        """Nouvelle version de la note ; un texte vide l'efface (l'historique garde l'ancienne)."""
        return self.imposer(nom, "note", texte, maintenant)

    def recents(self) -> list:
        return sorted(self.joueurs, key=lambda j: (j.derniere or "", j.nom.casefold()), reverse=True)

    # --- import -----------------------------------------------------------

    def conflits(self, autre: "Carnet") -> list:
        """Les traits et notes que chacun a modifiés de son côté (à calculer avant `fusionner`).

        Comme une avance rapide dans Git, pas de conflit si l'un a déjà vu la version actuelle
        de l'autre : sa version est dans mon historique (je l'ai remplacée) ou la mienne est dans
        le sien (il l'a remplacée). Pas de conflit non plus à valeur égale.
        """
        trouves = []
        for sien in autre.joueurs:
            mien = self.trouver(sien.nom)
            if mien is None:
                continue
            for champ in CHAMPS:
                sienne, mienne = sien.version(champ), mien.version(champ)
                if sienne is None or mienne is None:
                    continue
                if sienne in mien.historique(champ) or mienne in sien.historique(champ):
                    continue
                if sienne.texte != mienne.texte:
                    trouves.append(Conflit(mien.nom, champ, mienne, sienne))
        return trouves

    def fusionner(self, autre: "Carnet") -> Bilan:
        """Ajoute les joueurs, les versions et les rencontres d'un autre carnet (ADR 0022).

        Toute version nouvelle va dans l'historique ; la plus récente devient la version
        actuelle. Mes rencontres ne sont jamais touchées. Un joueur sans trait ni note n'est
        pas ajouté (mais ses rencontres le sont s'il est déjà dans mon carnet).
        """
        bilan = Bilan()
        for sien in autre.joueurs:
            mien = self.trouver(sien.nom)
            if mien is None:
                if not (sien.historique_trait or sien.historique_note):
                    continue  # rien d'utile à récupérer sur ce joueur
                mien = self._obtenir(sien.nom)
                bilan.joueurs_ajoutes += 1
            for champ in CHAMPS:
                avant = mien.trait if champ == "trait" else mien.note
                historique = mien.historique(champ)
                nouvelles = [r for r in sien.historique(champ) if r not in historique]
                historique.extend(nouvelles)
                historique.sort(key=lambda r: r.maj)  # stable : à date égale, l'ordre d'arrivée
                bilan.versions_ajoutees += len(nouvelles)
                if (mien.trait if champ == "trait" else mien.note) != avant:
                    if champ == "trait":
                        bilan.traits_maj += 1
                    else:
                        bilan.notes_maj += 1
            self._fusionner_rencontres(mien, sien, autre.auteur)
        return bilan

    def _fusionner_rencontres(self, mien: Joueur, sien: Joueur, son_auteur: str) -> None:
        siennes = dict(sien.autres_rencontres)
        if sien.rencontres:
            siennes[son_auteur] = Rencontres(sien.rencontres, sien.derniere)
        moi = self.auteur.casefold()
        for auteur, rencontres in siennes.items():
            if auteur.casefold() == moi:
                continue  # mes rencontres ne viennent que de moi
            cle = next((a for a in mien.autres_rencontres if a.casefold() == auteur.casefold()), auteur)
            actuelles = mien.autres_rencontres.get(cle)
            if actuelles is None or (rencontres.derniere or "") > (actuelles.derniere or ""):
                mien.autres_rencontres[cle] = Rencontres(rencontres.nombre, rencontres.derniere)

    def resoudre(self, conflit: Conflit, choix: str, maintenant: str) -> bool:
        """Applique un choix sur un conflit, après `fusionner`. Renvoie True si une version est ajoutée.

        - « recente » : la plus récente gagne (rien à faire, c'est déjà le cas) ;
        - « sans_suppression » : si la plus récente est sa suppression, ma version revient ;
        - « mienne », « sienne » : cette valeur gagne ;
        - « fusion » : les deux réunies (mots-clés pour le trait, « a / b » pour la note).

        Un choix différent de la plus récente devient une nouvelle version, signée par moi et
        datée de maintenant : il gagnera aussi chez les autres à leur prochain import.
        """
        joueur = self.trouver(conflit.nom)
        if joueur is None or choix == "recente":
            return False
        mienne, sienne = conflit.mienne.texte, conflit.sienne.texte
        if choix == "sans_suppression":
            actuel = joueur.trait if conflit.champ == "trait" else joueur.note
            if sienne or actuel:
                return False
            texte = mienne
        elif choix == "mienne":
            texte = mienne
        elif choix == "sienne":
            texte = sienne
        elif choix == "fusion":
            texte = reunir(conflit.champ, mienne, sienne)
        else:
            raise ValueError(choix)
        return self.imposer(joueur.nom, conflit.champ, texte, maintenant)

    # --- fichier JSON -----------------------------------------------------

    def vers_dict(self) -> dict:
        return {
            "version": VERSION,
            "owner": self.auteur,
            "players": [self._joueur_vers_dict(j) for j in self.recents()],
        }

    def _joueur_vers_dict(self, j: Joueur) -> dict:
        rencontres = {}
        if j.rencontres:
            rencontres[self.auteur] = {"count": j.rencontres, "last": j.derniere}
        for auteur, r in j.autres_rencontres.items():
            rencontres[auteur] = {"count": r.nombre, "last": r.derniere}
        brut = {"name": j.nom}
        if rencontres:
            brut["encountered_by"] = rencontres
        for champ in CHAMPS:
            if historique := j.historique(champ):
                brut[f"{champ}_history"] = [{"text": r.texte, "by": r.auteur, "at": r.maj} for r in historique]
        return brut

    @classmethod
    def depuis_dict(cls, brut) -> "Carnet":
        """Lit un carnet au format 2, ou au format 1 (ancien `carnet.json`, converti)."""
        if not isinstance(brut, dict):
            raise CarnetInvalide("le fichier doit contenir un objet JSON")
        if "players" not in brut and "owner" not in brut:
            return _depuis_format_1(brut)
        auteur = brut.get("owner", "?")
        if not isinstance(auteur, str):
            raise CarnetInvalide("« owner » doit être un texte")
        auteur = sans_controle(auteur).strip() or "?"
        brut_joueurs = brut.get("players", [])
        if not isinstance(brut_joueurs, list):
            raise CarnetInvalide("« players » doit être une liste")
        joueurs = [_lire_joueur(n, j, auteur) for n, j in enumerate(brut_joueurs, start=1)]
        return cls(auteur=auteur, joueurs=joueurs)

    def sauver(self, chemin: Path) -> None:
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_name(chemin.name + ".tmp")
        try:
            temporaire.write_text(
                json.dumps(self.vers_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
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


def reunir(champ: str, a: str, b: str) -> str:
    """Le choix « fusionner » : mots-clés des deux traits, ou les deux notes « a / b » (sans doublon)."""
    if champ == "trait":
        mots = (m.strip() for t in (a, b) for m in t.split(","))
        return ", ".join(dict.fromkeys(m for m in mots if m))
    return " / ".join(dict.fromkeys(t for t in (a, b) if t))


def migrer_ancien_fichier(dossier: Path) -> Path | None:
    """Convertit `carnet.json` (format 1) en `notebook.json`, puis garde l'ancien sous
    `carnet.v1.bak.json`. Renvoie le chemin de la sauvegarde, ou None s'il n'y avait rien à faire.

    Un ancien fichier illisible lève CarnetInvalide sans rien toucher.
    """
    dossier = Path(dossier)
    ancien, nouveau = dossier / ANCIEN_FICHIER, dossier / FICHIER
    if nouveau.exists() or not ancien.exists():
        return None
    try:
        carnet = Carnet.charger(ancien)
    except (OSError, CarnetInvalide) as erreur:
        raise CarnetInvalide(f"ancien carnet {ancien} : {erreur}") from erreur
    carnet.sauver(nouveau)
    sauvegarde = dossier / SAUVEGARDE_ANCIEN
    os.replace(ancien, sauvegarde)
    return sauvegarde


# --- lecture du format 2 -------------------------------------------------------


def _date_ou_rien(valeur) -> bool:
    return valeur is None or (isinstance(valeur, str) and re.match(r"\d{4}-\d{2}-\d{2}", valeur) is not None)


def _nom(brut, cle: str, numero: int) -> str:
    nom = brut.get(cle)
    nom = sans_controle(nom).strip() if isinstance(nom, str) else ""
    if not nom:
        raise CarnetInvalide(f"joueur n°{numero} : « {cle} » doit être un texte non vide")
    return nom


def _lire_joueur(numero: int, brut, proprietaire: str) -> Joueur:
    if not isinstance(brut, dict):
        raise CarnetInvalide(f"joueur n°{numero} : doit être un objet")
    nom = _nom(brut, "name", numero)
    lieu = f"joueur n°{numero} (« {nom} »)"
    joueur = Joueur(nom=nom)

    rencontres = brut.get("encountered_by", {})
    if not isinstance(rencontres, dict):
        raise CarnetInvalide(f"{lieu} : « encountered_by » doit être un objet")
    for auteur, r in rencontres.items():
        if not isinstance(r, dict):
            raise CarnetInvalide(f"{lieu} : rencontres de « {auteur} » : doit être un objet")
        nombre, derniere = r.get("count", 0), r.get("last")
        if isinstance(nombre, bool) or not isinstance(nombre, int) or nombre < 0:
            raise CarnetInvalide(f"{lieu} : « count » de « {auteur} » doit être un nombre entier positif ou nul")
        if not _date_ou_rien(derniere):
            raise CarnetInvalide(f"{lieu} : « last » de « {auteur} » doit être une date AAAA-MM-JJ ou null")
        auteur = sans_controle(auteur).strip()
        if auteur.casefold() == proprietaire.casefold():
            joueur.rencontres, joueur.derniere = nombre, derniere
        elif auteur:
            joueur.autres_rencontres[auteur] = Rencontres(nombre, derniere)

    for champ in CHAMPS:
        cle = f"{champ}_history"
        historique = brut.get(cle, [])
        if not isinstance(historique, list):
            raise CarnetInvalide(f"{lieu} : « {cle} » doit être une liste")
        lues = []
        for r in historique:
            if not isinstance(r, dict) or not isinstance(r.get("text"), str):
                raise CarnetInvalide(f"{lieu} : chaque version de « {cle} » doit avoir un « text »")
            auteur, maj = r.get("by", "?"), r.get("at", "")
            if not isinstance(auteur, str) or not isinstance(maj, str):
                raise CarnetInvalide(f"{lieu} : « by » et « at » de « {cle} » doivent être des textes")
            lues.append(Revision(sans_controle(r["text"]).strip(), sans_controle(auteur).strip() or "?", maj))
        lues.sort(key=lambda r: r.maj)
        joueur.historique(champ).extend(lues)
    return joueur


# --- lecture du format 1 (carnet.json, en français) ----------------------------


def _depuis_format_1(brut: dict) -> Carnet:
    """Ancien format : un trait et une note par auteur. Chacun devient une version de l'historique
    commun ; la plus récente devient la version actuelle (ADR 0023)."""
    auteur = brut.get("auteur", "?")
    if not isinstance(auteur, str):
        raise CarnetInvalide("« auteur » doit être un texte")
    auteur = sans_controle(auteur).strip() or "?"
    brut_joueurs = brut.get("joueurs", [])
    if not isinstance(brut_joueurs, list):
        raise CarnetInvalide("« joueurs » doit être une liste")
    joueurs = [_lire_joueur_1(n, j, auteur) for n, j in enumerate(brut_joueurs, start=1)]
    return Carnet(auteur=auteur, joueurs=joueurs)


def _lire_joueur_1(numero: int, brut, proprietaire: str) -> Joueur:
    if not isinstance(brut, dict):
        raise CarnetInvalide(f"joueur n°{numero} : doit être un objet")
    nom = _nom(brut, "nom", numero)
    lieu = f"joueur n°{numero} (« {nom} »)"

    rencontres = brut.get("rencontres", 0)
    if isinstance(rencontres, bool) or not isinstance(rencontres, int) or rencontres < 0:
        raise CarnetInvalide(f"{lieu} : « rencontres » doit être un nombre entier positif ou nul")
    derniere = brut.get("derniere")
    if not _date_ou_rien(derniere):
        raise CarnetInvalide(f"{lieu} : « derniere » doit être une date AAAA-MM-JJ ou null")

    traits = _lire_signes_1(brut.get("styles", {}), lieu, "styles", "le trait")
    notes = _lire_signes_1(brut.get("notes", {}), lieu, "notes", "la note")
    memo, memo_maj = brut.get("memo", ""), brut.get("memo_maj", "")
    if not isinstance(memo, str):
        raise CarnetInvalide(f"{lieu} : « memo » doit être un texte")
    if not isinstance(memo_maj, str):
        raise CarnetInvalide(f"{lieu} : « memo_maj » doit être un texte")
    memo = sans_controle(memo).strip()
    if memo:
        notes.append(Revision(memo, proprietaire, memo_maj))
    return Joueur(
        nom=nom,
        rencontres=rencontres,
        derniere=derniere,
        historique_trait=sorted(traits, key=lambda r: r.maj),
        historique_note=sorted(notes, key=lambda r: r.maj),
    )


def _lire_signes_1(brut, lieu: str, cle: str, quoi: str) -> list:
    """Lit un objet auteur -> {"texte", "maj"} du format 1 en versions (textes vides ignorés)."""
    if not isinstance(brut, dict):
        raise CarnetInvalide(f"{lieu} : « {cle} » doit être un objet")
    versions = []
    for auteur, note in brut.items():
        if not isinstance(note, dict) or not isinstance(note.get("texte"), str):
            raise CarnetInvalide(f"{lieu} : {quoi} de « {auteur} » doit avoir un « texte »")
        maj = note.get("maj", "")
        if not isinstance(maj, str):
            raise CarnetInvalide(f"{lieu} : « maj » de {quoi} de « {auteur} » doit être un texte")
        texte = sans_controle(note["texte"]).strip()
        if texte:
            versions.append(Revision(texte, sans_controle(auteur).strip() or "?", maj))
    return versions


def _trop_proche(derniere: str | None, quand: str) -> bool:
    if not derniere or len(derniere) <= 10 or len(quand) <= 10:  # pas d'heure connue
        return False
    try:
        ecart = datetime.fromisoformat(quand) - datetime.fromisoformat(derniere)
    except ValueError:
        return False
    return timedelta(0) <= ecart < FENETRE_RENCONTRE
