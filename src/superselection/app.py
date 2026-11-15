"""Les commandes, sans aucune entrée/sortie terminal (testable)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .carnet import Carnet, Joueur
from .classement import MODES, Classement
from .couleurs import peindre, role_rang
from .styles import decorer
from .texte import sans_controle

AIDE = """\
Tape le nom d'un adversaire : je te dis s'il est dans le top 100, je compte
la rencontre, puis tu notes son style et une note perso (Entrée = garder, « - » = effacer).
Tab complète les noms (top 100 + joueurs déjà croisés).

  <nom>             croiser un joueur              ex : [IMP] Pizza
  top [1v1|2v2]     le top 100 complet, avec recherche en tapant (Tab = changer de mode)
  show <nom>        voir sa fiche (3 dernières saisons) sans compter de rencontre
  list              tous les joueurs déjà croisés
  delete <nom>      retirer un joueur du carnet (après confirmation)
  reset             vider tout le carnet (après confirmation)
  rename <a> > <b>  renommer un joueur (ex : rename Pizza > [IMP] Pizza)
  export <fichier>  envoyer ton carnet à un pote   ex : export antho.json
  import <fichier>  fusionner le carnet d'un pote  ex : import kevin.json
  styles            les mots-clés de style et leurs emojis (🔥 aggressive, 🛡️ defence, 🐣 noob…)
  refresh           recharger le classement
  update            installer la dernière version
  version           voir la version installée
  help              cette aide
  quit              sortir (ou Ctrl+D)

Joueur qui s'appelle comme une commande ?  player list"""

# mot tapé -> commande
COMMANDES = {
    "show": "show",
    "top": "top",
    "list": "list",
    "delete": "delete",
    "reset": "reset",
    "rename": "rename",
    "export": "export",
    "import": "import",
    "styles": "styles",
    "refresh": "refresh",
    "update": "update",
    "version": "version",
    "help": "help",
    "?": "help",
    "quit": "quit",
    "exit": "quit",
    "q": "quit",
    "player": "croiser",
}

# proposées par l'auto-complétion
NOMS_COMMANDES = ("show", "top", "list", "delete", "reset", "rename", "styles", "export", "import", "refresh", "update", "version", "help", "quit")


def analyser(ligne: str, noms_connus=()) -> tuple:
    """Découpe une ligne saisie en (commande, argument).

    Une ligne qui est exactement le nom d'un joueur connu (à la casse près) est toujours
    une rencontre, même si elle commence par une commande (« Show Me », « Q »).
    """
    ligne = ligne.strip()
    if not ligne:
        return "rien", ""
    if ligne.casefold() in {n.casefold() for n in noms_connus}:
        return "croiser", ligne
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
        maintenant: Callable[[], str],
        couleur: bool = False,
        saison_passee: Callable[[int], Classement | None] | None = None,
    ):
        self.carnet = carnet
        self.chemin_carnet = Path(chemin_carnet)
        self.classement = classement
        self.maintenant = maintenant
        self.couleur = couleur
        self.saison_passee = saison_passee

    def _c(self, texte: str, role: str) -> str:
        return peindre(texte, role, self.couleur)

    # --- affichage --------------------------------------------------------

    def _ligne_rangs(self, nom: str, classement: Classement | None = None, prefixe: str = "") -> str:
        classement = classement or self.classement
        if classement is None:
            return "  " + self._c("(classement indisponible)", "info")
        morceaux = []
        for mode in ("1v1", "2v2"):
            rangs = classement.rangs(nom, mode)
            if rangs:
                ou = self._c(" ou ", "info")
                texte = ou.join(
                    self._c(f"#{r.position}", role_rang(r.position))
                    + self._c(f" ({r.points} pts)", "info")
                    for r in rangs
                )
                if len(rangs) > 1:
                    texte += self._c(f" — {len(rangs)} joueurs portent ce nom", "info")
                morceaux.append(f"{mode} : " + texte)
            else:
                morceaux.append(f"{mode} : " + self._c("hors top 100", "hors"))
        return "  " + prefixe + self._c("   ·   ", "info").join(morceaux)

    def _lignes_saisons(self, nom: str) -> list:
        """Rangs de la saison en cours et des 2 précédentes, une ligne par saison (ADR 0012)."""
        actuelle = self.classement.saison
        lignes = []
        for saison in (actuelle, actuelle - 1, actuelle - 2):
            if saison < 1:
                break
            etiquette = self._c(f"Saison {saison} : ", "info")
            ancien = self.classement if saison == actuelle else (
                self.saison_passee(saison) if self.saison_passee else None
            )
            if ancien is None:
                lignes.append("  " + self._c(f"Saison {saison} : indisponible", "info"))
            else:
                lignes.append(self._ligne_rangs(nom, ancien, etiquette))
        return lignes

    def _fiche(
        self,
        nom: str,
        joueur: Joueur | None,
        vient_de_croiser: bool = False,
        deja_compte: bool = False,
        historique: bool = False,
    ) -> str:
        lignes = [self._c(nom, "nom")]
        if historique and self.classement is not None:
            lignes += self._lignes_saisons(nom)
        else:
            lignes.append(self._ligne_rangs(nom))
        if joueur is None or joueur.rencontres == 0:
            lignes.append("  " + self._c("Jamais croisé.", "info"))
        elif deja_compte:
            lignes.append(
                f"  Croisé {joueur.rencontres} fois — "
                + self._c("rencontre déjà comptée il y a moins de 30 minutes.", "info")
            )
        elif joueur.rencontres == 1 and vient_de_croiser:
            lignes.append("  " + self._c("Première rencontre.", "ok"))
        else:
            lignes.append(
                f"  Croisé {joueur.rencontres} fois — dernière fois le {_date_fr(joueur.derniere)}"
            )
        if joueur and joueur.memo:
            lignes.append("  Note : " + joueur.memo)
        styles = joueur.styles if joueur else {}
        if not styles:
            lignes.append("  Style : " + self._c("pas encore noté", "info"))
        for auteur, note in sorted(styles.items(), key=lambda a: a[0] != self.carnet.auteur):
            qui = "toi" if auteur == self.carnet.auteur else auteur
            lignes.append(f"  Style ({self._c(qui, 'auteur')}) : " + self._c(decorer(note.texte), "style"))
        return "\n".join(lignes)

    def nom_canonique(self, nom: str) -> str:
        nom = nom.strip()
        if self.classement and (officiel := self.classement.nom_officiel(nom)):
            return officiel
        if joueur := self.carnet.trouver(nom):
            return joueur.nom
        return nom

    # --- commandes --------------------------------------------------------

    def _noms_proches(self, nom: str) -> list:
        cle = nom.casefold()
        proches = [n for n in self.noms() if n.casefold() != cle and (cle in n.casefold() or n.casefold() in cle)]
        return proches[:5]

    def croiser(self, nom: str) -> str:
        nom = self.nom_canonique(nom)
        inconnu = self.carnet.trouver(nom) is None and not (
            self.classement and self.classement.nom_officiel(nom)
        )
        avant = (j.rencontres if (j := self.carnet.trouver(nom)) else 0)
        joueur = self.carnet.croiser(nom, quand=self.maintenant())
        deja_compte = joueur.rencontres == avant
        if not deja_compte:
            self.carnet.sauver(self.chemin_carnet)
        fiche = self._fiche(joueur.nom, joueur, vient_de_croiser=True, deja_compte=deja_compte)
        if inconnu:
            fiche += "\n  " + self._c("Nouveau joueur.", "info")
            if proches := self._noms_proches(nom):
                fiche += self._c(" Noms proches : ", "info") + ", ".join(proches)
                fiche += self._c(" (si c'est le même : delete puis rename)", "info")
        return fiche

    def voir(self, nom: str) -> str:
        nom = self.nom_canonique(nom)
        return self._fiche(nom, self.carnet.trouver(nom), historique=True)

    @staticmethod
    def lire_top(argument: str) -> tuple:
        """Découpe l'argument de `top` en (mode, filtre). Mode 1v1 par défaut."""
        mot, _, reste = argument.strip().partition(" ")
        if mot.casefold() in MODES:
            return mot.casefold(), reste.strip()
        return "1v1", argument.strip()

    def top(self, mode: str, filtre: str = "") -> str:
        """Le top 100 d'un mode ; `filtre` garde les noms qui le contiennent (rang d'origine conservé)."""
        if self.classement is None:
            return self._c("Classement indisponible (essaie « refresh »).", "erreur")
        cle = filtre.strip().casefold()
        vus = {j.nom.casefold(): j.rencontres for j in self.carnet.joueurs if j.rencontres}
        lignes = []
        for position, ligne in enumerate(self.classement.lignes.get(mode, []), start=1):
            if cle in ligne["name"].casefold():
                vu = self._c(f"  vu {vus[ligne['name'].casefold()]}x", "info") if ligne["name"].casefold() in vus else ""
                lignes.append(
                    self._c(f"#{position:<4}", role_rang(position))
                    + self._c(ligne["name"], "nom")
                    + self._c(f"  {ligne['rating']} pts", "info")
                    + vu
                )
        titre = f"Top 100 {mode} (saison {self.classement.saison})"
        if cle:
            titre += f" — « {filtre.strip()} » : {len(lignes)}"
        if not lignes:
            return titre + "\n  " + self._c("Aucun joueur ne correspond.", "info")
        return titre + "\n" + "\n".join("  " + l for l in lignes)

    def mon_style(self, nom: str) -> str:
        joueur = self.carnet.trouver(nom)
        note = joueur.styles.get(self.carnet.auteur) if joueur else None
        return note.texte if note else ""

    def mon_memo(self, nom: str) -> str:
        joueur = self.carnet.trouver(nom)
        return joueur.memo if joueur else ""

    def memoriser(self, nom: str, texte: str) -> str:
        nom = self.nom_canonique(nom)
        self.carnet.memoriser(nom, texte)
        if self.carnet.trouver(nom) is None:
            return self._c("Rien à effacer : joueur absent du carnet.", "info")
        self.carnet.sauver(self.chemin_carnet)
        if self.mon_memo(nom):
            return self._c(f"Note enregistrée pour {nom}.", "ok")
        return self._c(f"Note effacée pour {nom}.", "ok")

    def noter(self, nom: str, texte: str) -> None:
        self.carnet.noter(self.nom_canonique(nom), texte, maintenant=self.maintenant())
        self.carnet.sauver(self.chemin_carnet)

    def supprimer(self, nom: str) -> str:
        joueur = self.carnet.supprimer(nom.strip())
        if joueur is None:
            return self._c(f"« {nom.strip()} » n'est pas dans ton carnet.", "erreur")
        self.carnet.sauver(self.chemin_carnet)
        return self._c(f"{joueur.nom} retiré du carnet.", "ok")

    def vider(self) -> str:
        nombre = self.carnet.vider()
        self.carnet.sauver(self.chemin_carnet)
        return self._c(f"Carnet vidé ({nombre} joueur(s) retiré(s)). Ton pseudo est gardé.", "ok")

    def renommer(self, argument: str) -> str:
        ancien, separateur, nouveau = (p.strip() for p in argument.partition(">"))
        if not separateur or not ancien or not sans_controle(nouveau).strip():
            return "Indique l'ancien et le nouveau nom.  ex : rename Pizza > [IMP] Pizza"
        joueur = self.carnet.trouver(ancien)
        if joueur is None:
            return self._c(f"« {ancien} » n'est pas dans ton carnet.", "erreur")
        nouveau = sans_controle(nouveau).strip()
        if self.classement and (officiel := self.classement.nom_officiel(nouveau)):
            nouveau = officiel  # casse exacte du classement ; sinon tel que tapé
        try:
            self.carnet.renommer(ancien, nouveau)
        except ValueError:
            return self._c(f"« {nouveau} » existe déjà dans ton carnet : supprime l'un des deux d'abord.", "erreur")
        self.carnet.sauver(self.chemin_carnet)
        return self._c(f"{ancien} renommé en {nouveau}.", "ok")

    def liste(self) -> str:
        joueurs = [j for j in self.carnet.recents() if j.rencontres or j.styles or j.memo]
        if not joueurs:
            return "Aucun joueur dans ton carnet pour l'instant."
        largeur = min(max(len(j.nom) for j in joueurs), 30)
        lignes = [f"{len(joueurs)} joueur(s) :"]
        for j in joueurs:
            styles = self._c(" | ", "info").join(
                self._c("toi" if a == self.carnet.auteur else a, "auteur") + ": " + decorer(n.texte)
                for a, n in j.styles.items()
            )
            vu = f"{j.rencontres}x, {_date_fr(j.derniere)}" if j.rencontres else "jamais croisé"
            lignes.append(f"  {self._c(f'{j.nom:<{largeur}}', 'nom')}  {self._c(f'{vu:<16}', 'info')}  {styles}")
        return "\n".join(lignes)

    def exporter(self, chemin: str) -> str:
        if not chemin:
            return "Indique un fichier.  ex : export antho.json"
        cible = Path(chemin).expanduser()
        if cible.suffix == "":
            cible = cible.with_suffix(".json")
        try:
            self.carnet.sauver(cible, avec_memos=False)
        except OSError as erreur:
            return self._c(f"Impossible d'écrire {cible} : {erreur.strerror or erreur}", "erreur")
        return f"Carnet exporté dans {cible.resolve()} — envoie ce fichier à ton pote."

    def importer(self, chemin: str) -> str:
        if not chemin:
            return "Indique un fichier.  ex : import kevin.json"
        source = Path(chemin).expanduser()
        try:
            autre = Carnet.charger(source)
        except FileNotFoundError:
            return self._c(f"Fichier introuvable : {source}", "erreur")
        except (ValueError, OSError) as erreur:  # JSONDecodeError et CarnetInvalide sont des ValueError
            return self._c(
                f"Ce fichier n'est pas un carnet superselection : {source} ({erreur})", "erreur"
            )
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
