"""Les commandes, sans aucune entrée/sortie terminal (testable)."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

HISTORIQUE_MAX = 10  # versions passées affichées dans show et edit

from .carnet import Carnet, Conflit, Joueur, Revision
from .classement import MODES, Classement
from .couleurs import peindre, role_rang
from .traits import aide_traits, decorer, valider
from .texte import ajuster, cle_alphabetique, largeur, sans_controle, tronquer

AIDE = """\
Saisir le nom d'un adversaire : affiche son rang dans le top 100, compte la
rencontre, puis demande le trait et la note (Entrée = garder, « - » = effacer).
Trait et note sont communs : la version la plus récente l'emporte, show garde l'historique.
Tab complète les noms (top 100 + joueurs déjà croisés).

  <nom>             croiser un joueur              ex : [IMP] Pizza
  top [1v1|2v2]     afficher le top 100, recherche en tapant (Tab = changer de mode)
  show <nom>        afficher la fiche (saisons, historique), sans compter
  edit <nom>        modifier nom, trait et note (champs pré-remplis), sans compter
  list              lister les joueurs déjà croisés
  delete <nom>      supprimer un joueur du carnet (confirmation)
  reset             vider le carnet (confirmation)
  export [fichier]  exporter le carnet (sur le Bureau)   ex : export antho.json
  import <fichier>  fusionner un carnet exporté (conflits : choix proposé)  ex : import kevin.json
  refresh           recharger le classement
  update [--force]  installer la dernière version (--force : réinstaller sans vérifier)
  version           afficher la version installée
  help              afficher cette aide
  quit              quitter (ou Ctrl+D)

Nom de joueur identique à une commande :  player list"""

# mot tapé -> commande
COMMANDES = {
    "show": "show",
    "edit": "edit",
    "top": "top",
    "list": "list",
    "delete": "delete",
    "reset": "reset",
    "export": "export",
    "import": "import",
    "traits": "traits",  # supprimé (ADR 0020) : renvoie vers Tab à la saisie du trait, plus annoncé
    "styles": "traits",  # ancien nom (ADR 0017), plus annoncé
    "rename": "rename",  # supprimé (ADR 0016) : renvoie vers edit, plus annoncé
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
NOMS_COMMANDES = ("show", "edit", "top", "list", "delete", "reset", "export", "import", "refresh", "update", "version", "help", "quit")


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


def sans_fin(texte: str) -> str:
    return texte.rstrip(" ")


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
        bureau: Path | None = None,
    ):
        self.carnet = carnet
        self.chemin_carnet = Path(chemin_carnet)
        self.classement = classement
        self.maintenant = maintenant
        self.couleur = couleur
        self.saison_passee = saison_passee
        self.bureau = bureau  # dossier par défaut de l'export (None : dossier courant)
        self._saisons_passees: dict = {}  # numéro de saison -> Classement | None, pour la session
        self._transactions = 0  # > 0 : les commandes modifient la mémoire, rien n'est écrit sur disque

    def _sauver(self) -> None:
        if not self._transactions:
            self.carnet.sauver(self.chemin_carnet)

    @contextmanager
    def transaction(self):
        """Tout ou rien (ADR 0018) : à la sortie normale on écrit le carnet une fois ; sur
        n'importe quelle exception (Ctrl+C, Ctrl+D, bug) le carnet revient à son état d'entrée,
        mémoire et disque, puis l'exception repart."""
        instantane = copy.deepcopy(self.carnet.__dict__)
        avant = self.carnet.vers_dict()
        self._transactions += 1
        try:
            yield
        except BaseException:
            self.carnet.__dict__.clear()
            self.carnet.__dict__.update(instantane)
            raise
        finally:
            self._transactions -= 1
        if not self._transactions and self.carnet.vers_dict() != avant:
            self.carnet.sauver(self.chemin_carnet)

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

    def _saisons_passees_chargees(self, saisons: list) -> dict:
        """Classements des saisons passées, mémorisés pour la session (même un échec : serveur muet =
        une seule attente). Les saisons manquantes sont téléchargées en parallèle."""
        if self.saison_passee is None:
            return {}
        manquantes = [n for n in saisons if n not in self._saisons_passees]
        if manquantes:
            with ThreadPoolExecutor(max_workers=8) as groupe:
                for n, classement in zip(manquantes, groupe.map(self.saison_passee, manquantes)):
                    self._saisons_passees[n] = classement
        return {n: self._saisons_passees[n] for n in saisons}

    def changer_classement(self, classement: Classement | None) -> None:
        self.classement = classement
        self._saisons_passees.clear()

    def _lignes_saisons(self, nom: str) -> list:
        """La saison en cours, puis chaque saison passée où le joueur est dans le top 100,
        de la plus récente à la plus ancienne (ADR 0019)."""
        actuelle = self.classement.saison
        lignes = [self._ligne_rangs(nom, self.classement, self._c("Saison actuelle : ", "info"))]
        passees = self._saisons_passees_chargees(list(range(actuelle - 1, 0, -1)))
        if self.saison_passee is None:
            return lignes
        trouvees, indisponibles = 0, []
        for saison, ancien in passees.items():
            if ancien is None:
                indisponibles.append(str(saison))
            elif any(ancien.rangs(nom, mode) for mode in MODES):
                trouvees += 1
                lignes.append(self._ligne_rangs(nom, ancien, self._c(f"Saison {saison} : ", "info")))
        if not trouvees:
            lignes.append("  " + self._c("Saisons passées : jamais dans le top 100", "info"))
        if indisponibles:
            lignes.append("  " + self._c("Saisons indisponibles : " + ", ".join(indisponibles), "info"))
        return lignes

    def _fiche(
        self,
        nom: str,
        joueur: Joueur | None,
        vient_de_croiser: bool = False,
        deja_compte: bool = False,
        historique: bool = False,
        versions: bool = False,
    ) -> str:
        """`historique` : saisons passées et détail des rencontres (show) ;
        `versions` : anciennes versions du trait et de la note (show et edit)."""
        lignes = [self._c(nom, "nom")]
        if historique and self.classement is not None:
            lignes += self._lignes_saisons(nom)
        else:
            lignes.append(self._ligne_rangs(nom))
        croise_par = self._croise_par(joueur) if joueur else []
        if historique and croise_par:  # show : qui l'a croisé (moi, puis les auteurs importés)
            lignes.append(
                "  Croisé par " + ", ".join(self._c(n, "auteur") for n in croise_par) + "."
            )
        if joueur is None or joueur.rencontres == 0:
            if not (historique and croise_par):
                texte = f"Croisé par {', '.join(croise_par)}." if croise_par else "Jamais croisé."
                lignes.append("  " + self._c(texte, "info"))
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
        if historique and joueur and joueur.autres_rencontres:
            autres = sorted(joueur.autres_rencontres.items(), key=lambda a: a[0].casefold())
            lignes.append(
                "  Rencontres des autres : "
                + ", ".join(f"{self._c(a, 'auteur')} {r.nombre} fois ({_date_fr(r.derniere)})" for a, r in autres)
            )
        note = joueur.version("note") if joueur else None
        if note and note.texte:
            lignes.append("  Note : " + note.texte + self._signature(note))
        trait = joueur.version("trait") if joueur else None
        if trait and trait.texte:
            lignes.append("  Trait : " + self._c(decorer(trait.texte), "trait") + self._signature(trait))
        else:
            lignes.append("  Trait : " + self._c("pas encore noté", "info"))
        if versions and joueur:
            lignes += self._lignes_historique(joueur)
        return "\n".join(lignes)

    def _signature(self, version: Revision) -> str:
        return self._c(f"  ({version.auteur}, {_date_fr(version.maj)})", "info")

    def _lignes_historique(self, joueur: Joueur) -> list:
        """Les versions remplacées du trait et de la note, de la plus récente à la plus ancienne."""
        passees = [(r, "trait") for r in joueur.historique_trait[:-1]]
        passees += [(r, "note") for r in joueur.historique_note[:-1]]
        if not passees:
            return []
        passees.sort(key=lambda v: v[0].maj, reverse=True)
        colonne = max(largeur(r.auteur) for r, _ in passees[:HISTORIQUE_MAX])
        lignes = ["  " + self._c(f"Historique ({len(passees)} version(s) remplacée(s)) :", "info")]
        for r, champ in passees[:HISTORIQUE_MAX]:
            if r.texte:
                texte = self._c(decorer(r.texte), "trait") if champ == "trait" else r.texte
            else:
                texte = self._c("(effacé)" if champ == "trait" else "(effacée)", "info")
            lignes.append(
                f"    {_date_fr(r.maj)}  " + self._c(ajuster(r.auteur, colonne), "auteur")
                + f"  {champ:<5} : " + texte
            )
        return lignes

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
            self._sauver()
        fiche = self._fiche(joueur.nom, joueur, vient_de_croiser=True, deja_compte=deja_compte)
        if inconnu:
            fiche += "\n  " + self._c("Nouveau joueur.", "info")
            if proches := self._noms_proches(nom):
                fiche += self._c(" Noms proches : ", "info") + ", ".join(proches)
                fiche += self._c(f" (même joueur ? delete {nom}, puis saisir le bon nom)", "info")
        return fiche

    def voir(self, nom: str) -> str:
        nom = self.nom_canonique(nom)
        return self._fiche(nom, self.carnet.trouver(nom), historique=True, versions=True)

    def modifier(self, nom: str) -> str:
        """Fiche d'un joueur déjà croisé, avant de changer son nom, son trait ou sa note : ne compte rien."""
        nom = self.nom_canonique(nom)
        joueur = self.carnet.trouver(nom)
        if joueur is None:
            return self._c(f"« {nom} » n'est pas dans le carnet : saisir d'abord son nom.", "erreur")
        return self._fiche(joueur.nom, joueur, versions=True)

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
            return self._c("Classement indisponible (réessayer avec « refresh »).", "erreur")
        cle = filtre.strip().casefold()
        vus = {j.nom.casefold(): j.rencontres for j in self.carnet.joueurs if j.rencontres}
        gardees = [
            (position, ligne)
            for position, ligne in enumerate(self.classement.lignes.get(mode, []), start=1)
            if cle in ligne["name"].casefold()
        ]
        titre = f"Top 100 {mode} (saison {self.classement.saison})"
        if cle:
            titre += f" — « {filtre.strip()} » : {len(gardees)}"
        if not gardees:
            return titre + "\n  " + self._c("Aucun joueur ne correspond.", "info")
        colonne = max(3, min(max(largeur(l["name"]) for _, l in gardees), 30))  # au moins « Nom »
        lignes = [
            self._c("Rang", "entete") + " " + self._c("Nom", "entete") + " " * (colonne - 3 + 2) + self._c("Points", "entete")
        ]
        for position, ligne in gardees:
            vu = self._c(f"  vu {vus[ligne['name'].casefold()]}x", "info") if ligne["name"].casefold() in vus else ""
            lignes.append(
                self._c(f"#{position:<4}", role_rang(position))
                + self._c(ajuster(ligne["name"], colonne), "nom")
                + self._c(f"  {ligne['rating']} pts", "info")
                + vu
            )
        return titre + "\n" + "\n".join("  " + l for l in lignes)

    def trait_actuel(self, nom: str) -> str:
        """Le trait commun actuel (la version la plus récente, quel que soit son auteur)."""
        joueur = self.carnet.trouver(nom)
        return joueur.trait if joueur else ""

    def note_actuelle(self, nom: str) -> str:
        joueur = self.carnet.trouver(nom)
        return joueur.note if joueur else ""

    def memoriser(self, nom: str, texte: str) -> str:
        nom = self.nom_canonique(nom)
        self.carnet.memoriser(nom, texte, maintenant=self.maintenant())
        if self.carnet.trouver(nom) is None:
            return self._c("Rien à effacer : joueur absent du carnet.", "info")
        self._sauver()
        if self.note_actuelle(nom):
            return self._c(f"Note enregistrée pour {nom}.", "ok")
        return self._c(f"Note effacée pour {nom}.", "ok")

    def noter(self, nom: str, texte: str) -> str:
        """Enregistre le trait (mots-clés seulement, ADR 0017). Renvoie un message d'erreur, ou « » si tout va bien."""
        canonique, inconnus = valider(texte)
        if texte.strip() and not canonique and not inconnus:  # « , » ou « ; » : aucun mot, on n'efface pas
            return self._c("Trait refusé : aucun mot-clé.", "erreur") + "\n" + aide_traits()
        if inconnus:
            mots = ", ".join(f"« {m} »" for m in inconnus)
            return self._c(f"Trait refusé : {mots} inconnu(s). ", "erreur") + "\n" + aide_traits()
        self.carnet.noter(self.nom_canonique(nom), canonique, maintenant=self.maintenant())
        self._sauver()
        return ""

    def supprimer(self, nom: str) -> str:
        joueur = self.carnet.supprimer(nom.strip())
        if joueur is None:
            return self._c(f"« {nom.strip()} » n'est pas dans le carnet.", "erreur")
        self._sauver()
        return self._c(f"{joueur.nom} retiré du carnet.", "ok")

    def vider(self) -> str:
        nombre = self.carnet.vider()
        self._sauver()
        return self._c(f"Carnet vidé ({nombre} joueur(s) retiré(s)). Pseudo conservé.", "ok")

    def renommer(self, ancien: str, nouveau: str) -> str:
        ancien = ancien.strip()
        if not sans_controle(nouveau).strip():
            return self._c("Nouveau nom manquant.", "erreur")
        joueur = self.carnet.trouver(ancien)
        if joueur is None:
            return self._c(f"« {ancien} » n'est pas dans le carnet.", "erreur")
        nouveau = sans_controle(nouveau).strip()
        if self.classement and (officiel := self.classement.nom_officiel(nouveau)):
            nouveau = officiel  # casse exacte du classement ; sinon tel que tapé
        try:
            self.carnet.renommer(ancien, nouveau)
        except ValueError:
            return self._c(f"« {nouveau} » existe déjà dans le carnet : supprimer l'un des deux d'abord.", "erreur")
        self._sauver()
        return self._c(f"{ancien} renommé en {nouveau}.", "ok")

    def _croise_par(self, joueur: Joueur) -> list:
        """Qui connaît ce joueur : le propriétaire s'il l'a croisé (ou noté), puis les autres qui l'ont
        croisé ou ont écrit une version de son trait ou de sa note."""
        moi = self.carnet.auteur
        auteurs = joueur.auteurs()
        noms = [moi] if (joueur.rencontres or any(a.casefold() == moi.casefold() for a in auteurs)) else []
        autres = {
            a.casefold(): a for a in [*joueur.autres_rencontres, *auteurs] if a.casefold() != moi.casefold()
        }
        return noms + sorted(autres.values(), key=str.casefold)

    def liste(self) -> str:
        """Joueurs du carnet par ordre alphabétique, écritures non latines à la fin, avec un en-tête.
        Concise : version actuelle seulement, ni auteurs ni historique (ils restent dans `show`)."""
        joueurs = sorted(
            (j for j in self.carnet.joueurs if j.rencontres or j.historique_trait or j.historique_note),
            key=lambda j: cle_alphabetique(j.nom),
        )
        if not joueurs:
            return "Aucun joueur dans le carnet."
        cellules = [
            (
                j.nom,
                decorer(j.trait),
                tronquer(j.note, 50),
                f"{j.rencontres}x, {_date_fr(j.derniere)}" if j.rencontres else "",
            )
            for j in joueurs
        ]
        en_tete = ("Nom", "Traits", "Note", "Vu")
        plafonds = (30, 60, 50, 16)
        colonnes = [min(max(largeur(c[i]) for c in cellules + [en_tete]), plafonds[i]) for i in range(4)]
        roles = ("nom", "trait", None, "info")

        def rangee(textes, roles) -> str:
            # la dernière colonne n'est pas complétée : rien en fin de ligne, en couleur comme sans
            # couleur sur le texte seul, espaces de remplissage ensuite (pas de soulignement qui déborde)
            morceaux = [
                (self._c(t, r) if r else t) + " " * max(0, l - largeur(t))
                for t, l, r in zip(textes, colonnes, roles)
            ]
            return sans_fin("  " + "  ".join(morceaux))

        lignes = [f"{len(joueurs)} joueur(s) :", rangee(en_tete, ("entete",) * 4)]
        lignes += [rangee(c, roles) for c in cellules]
        return "\n".join(lignes)

    def exporter(self, chemin: str) -> str:
        # sans fichier : <pseudo>.json ; un nom seul (chemin relatif) va sur le Bureau
        cible = Path(chemin or self.carnet.auteur).expanduser()
        if not cible.is_absolute() and self.bureau is not None:
            cible = self.bureau / cible
        if cible.suffix == "":
            cible = cible.with_suffix(".json")
        if cible.resolve() == self.chemin_carnet.resolve():
            return self._c("Export impossible : ce fichier est le carnet lui-même.", "erreur")
        try:
            self.carnet.sauver(cible)
        except OSError as erreur:
            return self._c(f"Impossible d'écrire {cible} : {erreur.strerror or erreur}", "erreur")
        return (
            f"Carnet exporté dans {cible.resolve()}.\n"
            + self._c("Notes et historique inclus : lisibles par toute personne qui reçoit le fichier.", "info")
        )

    def importer(self, chemin: str, decider: Callable[[list, str], list] | None = None) -> str:
        """Fusionne un carnet exporté : la version la plus récente l'emporte (ADR 0022).

        S'il y a des conflits (chacun a modifié de son côté), `decider(conflits, son_pseudo)` renvoie un choix
        par conflit (« recente », « sans_suppression », « mienne », « sienne », « fusion ») ;
        sans `decider`, la plus récente gagne. Ctrl+C dans `decider` remonte (l'appelant annule).
        """
        if not chemin:
            return "Fichier manquant.  ex : import kevin.json"
        source = Path(chemin).expanduser()
        try:
            autre = Carnet.charger(source)
        except FileNotFoundError:
            return self._c(f"Fichier introuvable : {source}", "erreur")
        except (ValueError, OSError) as erreur:  # JSONDecodeError et CarnetInvalide sont des ValueError
            return self._c(
                f"Ce fichier n'est pas un carnet superselection : {source} ({erreur})", "erreur"
            )
        conflits = self.carnet.conflits(autre)
        choix = decider(conflits, autre.auteur) if (conflits and decider) else ["recente"] * len(conflits)
        bilan = self.carnet.fusionner(autre)
        maintenant = self.maintenant()
        appliques = sum(self.carnet.resoudre(c, ch, maintenant) for c, ch in zip(conflits, choix))
        self._sauver()
        message = (
            f"Carnet de {autre.auteur} fusionné : {bilan.joueurs_ajoutes} joueur(s) ajouté(s), "
            f"{bilan.versions_ajoutees} version(s) ajoutée(s) à l'historique, "
            f"{bilan.traits_maj} trait(s) et {bilan.notes_maj} note(s) changé(s) "
            "(la version la plus récente l'emporte)."
        )
        if conflits:
            message += f" {len(conflits)} conflit(s), {appliques} choix enregistré(s) comme nouvelle version."
        return message

    def resume_conflits(self, conflits: list, auteur: str) -> str:
        """« 3 conflit(s) avec Paul (2 note(s), 1 trait(s)), dont 1 suppression. »"""
        notes = sum(c.champ == "note" for c in conflits)
        suppressions = sum(not c.sienne.texte for c in conflits)
        texte = f"{len(conflits)} conflit(s) avec {auteur} ({notes} note(s), {len(conflits) - notes} trait(s))"
        if suppressions:
            texte += f", dont {suppressions} suppression(s)"
        return texte + "."

    def decrire_conflit(self, conflit: Conflit) -> str:
        """Les deux versions côte à côte, numérotées comme le choix proposé (1 = la mienne)."""
        lignes = [self._c(conflit.nom, "nom") + f" — {conflit.champ}"]
        versions = (conflit.mienne, conflit.sienne)
        colonne = max(largeur(v.auteur) for v in versions)
        for numero, v in enumerate(versions, start=1):
            if v.texte:
                texte = self._c(decorer(v.texte), "trait") if conflit.champ == "trait" else v.texte
            else:
                texte = self._c("(supprimé)" if conflit.champ == "trait" else "(supprimée)", "info")
            lignes.append(
                f"  {numero}. " + self._c(ajuster(v.auteur, colonne), "auteur")
                + f" ({_date_fr(v.maj)}) : " + texte
            )
        return "\n".join(lignes)

    def noms(self) -> list:
        noms = {j.nom for j in self.carnet.joueurs}
        if self.classement:
            noms |= self.classement.noms()
        return sorted(noms, key=str.casefold)
