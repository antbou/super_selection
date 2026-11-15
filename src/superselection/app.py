"""Les commandes, sans aucune entrée/sortie terminal (testable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .carnet import Carnet, Joueur
from .classement import Classement

AIDE = """\
Tape le nom d'un adversaire : je te dis s'il est dans le top 100, je compte
la rencontre, puis tu notes son style (Entrée = garder, « - » = effacer).
Tab complète les noms (top 100 + joueurs déjà croisés).

  <nom>             croiser un joueur        ex : [IMP] Pizza
  voir <nom>        voir sa fiche sans compter de rencontre
  liste             tous les joueurs déjà croisés
  export <fichier>  envoyer ton carnet à un pote   ex : export antho.json
  import <fichier>  fusionner le carnet d'un pote  ex : import kevin.json
  maj               recharger le classement
  aide              cette aide
  quitter           sortir (ou Ctrl+D)

Joueur qui s'appelle comme une commande ?  joueur liste"""

COMMANDES = {
    "voir": "voir",
    "liste": "liste",
    "export": "export",
    "import": "import",
    "maj": "maj",
    "aide": "aide",
    "help": "aide",
    "?": "aide",
    "quitter": "quitter",
    "q": "quitter",
    "exit": "quitter",
    "joueur": "croiser",
}


def analyser(ligne: str) -> tuple:
    """Découpe une ligne saisie en (commande, argument)."""
    ligne = ligne.strip()
    if not ligne:
        return "rien", ""
    mot, _, reste = ligne.partition(" ")
    commande = COMMANDES.get(mot.casefold())
    if commande is None:
        return "croiser", ligne
    reste = reste.strip()
    if commande in ("import", "export"):
        reste = reste.strip("\"'")
    return commande, reste


def _date_fr(iso: str | None) -> str:
    if not iso:
        return "?"
    annee, mois, jour = iso[:10].split("-")
    return f"{jour}/{mois}/{annee}"


class App:
    def __init__(
        self,
        carnet: Carnet,
        chemin_carnet: Path,
        classement: Classement | None,
        aujourd_hui: Callable[[], str],
        maintenant: Callable[[], str],
    ):
        self.carnet = carnet
        self.chemin_carnet = Path(chemin_carnet)
        self.classement = classement
        self.aujourd_hui = aujourd_hui
        self.maintenant = maintenant

    # --- affichage --------------------------------------------------------

    def _ligne_rangs(self, nom: str) -> str:
        if self.classement is None:
            return "  (classement indisponible)"
        morceaux = []
        for mode in ("1v1", "2v2"):
            rang = self.classement.rang(nom, mode)
            morceaux.append(
                f"{mode} : #{rang.position} ({rang.points} pts)" if rang else f"{mode} : hors top 100"
            )
        return "  " + "   ·   ".join(morceaux)

    def _fiche(self, nom: str, joueur: Joueur | None, vient_de_croiser: bool = False) -> str:
        lignes = [nom, self._ligne_rangs(nom)]
        if joueur is None or joueur.rencontres == 0:
            lignes.append("  Jamais croisé.")
        elif joueur.rencontres == 1 and vient_de_croiser:
            lignes.append("  Première rencontre.")
        else:
            lignes.append(
                f"  Croisé {joueur.rencontres} fois — dernière fois le {_date_fr(joueur.derniere)}"
            )
        styles = joueur.styles if joueur else {}
        if not styles:
            lignes.append("  Style : pas encore noté")
        for auteur, note in sorted(styles.items(), key=lambda a: a[0] != self.carnet.auteur):
            qui = "toi" if auteur == self.carnet.auteur else auteur
            lignes.append(f"  Style ({qui}) : {note.texte}")
        return "\n".join(lignes)

    def _nom_canonique(self, nom: str) -> str:
        nom = nom.strip()
        if self.classement and (officiel := self.classement.nom_officiel(nom)):
            return officiel
        if joueur := self.carnet.trouver(nom):
            return joueur.nom
        return nom

    # --- commandes --------------------------------------------------------

    def croiser(self, nom: str) -> str:
        nom = self._nom_canonique(nom)
        joueur = self.carnet.croiser(nom, jour=self.aujourd_hui())
        self.carnet.sauver(self.chemin_carnet)
        return self._fiche(joueur.nom, joueur, vient_de_croiser=True)

    def voir(self, nom: str) -> str:
        nom = self._nom_canonique(nom)
        return self._fiche(nom, self.carnet.trouver(nom))

    def mon_style(self, nom: str) -> str:
        joueur = self.carnet.trouver(nom)
        note = joueur.styles.get(self.carnet.auteur) if joueur else None
        return note.texte if note else ""

    def noter(self, nom: str, texte: str) -> None:
        self.carnet.noter(self._nom_canonique(nom), texte, maintenant=self.maintenant())
        self.carnet.sauver(self.chemin_carnet)

    def liste(self) -> str:
        joueurs = [j for j in self.carnet.recents() if j.rencontres or j.styles]
        if not joueurs:
            return "Aucun joueur dans ton carnet pour l'instant."
        largeur = min(max(len(j.nom) for j in joueurs), 30)
        lignes = [f"{len(joueurs)} joueur(s) :"]
        for j in joueurs:
            styles = " | ".join(
                f"{'toi' if a == self.carnet.auteur else a}: {n.texte}" for a, n in j.styles.items()
            )
            vu = f"{j.rencontres}x, {_date_fr(j.derniere)}" if j.rencontres else "jamais croisé"
            lignes.append(f"  {j.nom:<{largeur}}  {vu:<16}  {styles}")
        return "\n".join(lignes)

    def exporter(self, chemin: str) -> str:
        if not chemin:
            return "Indique un fichier.  ex : export antho.json"
        cible = Path(chemin).expanduser()
        if cible.suffix == "":
            cible = cible.with_suffix(".json")
        self.carnet.sauver(cible)
        return f"Carnet exporté dans {cible.resolve()} — envoie ce fichier à ton pote."

    def importer(self, chemin: str) -> str:
        if not chemin:
            return "Indique un fichier.  ex : import kevin.json"
        source = Path(chemin).expanduser()
        try:
            autre = Carnet.charger(source)
        except FileNotFoundError:
            return f"Fichier introuvable : {source}"
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return f"Ce fichier n'est pas un carnet superselection : {source}"
        bilan = self.carnet.fusionner(autre)
        self.carnet.sauver(self.chemin_carnet)
        return (
            f"Carnet de {autre.auteur} fusionné : {bilan.joueurs_ajoutes} joueur(s) ajouté(s), "
            f"{bilan.notes_ajoutees} note(s) ajoutée(s), {bilan.notes_maj} note(s) mise(s) à jour. "
            "Tes notes n'ont pas été touchées."
        )

    def noms(self) -> list:
        noms = {j.nom for j in self.carnet.joueurs}
        if self.classement:
            noms |= self.classement.noms()
        return sorted(noms, key=str.casefold)
