"""Les commandes, sans aucune entrée/sortie terminal (testable)."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from .carnet import Carnet, Joueur
from .classement import MODES, Classement
from .couleurs import peindre, role_rang
from .traits import aide_traits, decorer, valider
from .texte import ajuster, cle_alphabetique, largeur, sans_controle, tronquer

AIDE = """\
Saisir le nom d'un adversaire : affiche son rang dans le top 100, compte la
rencontre, puis demande un trait et une note perso (Entrée = garder, « - » = effacer).
Tab complète les noms (top 100 + joueurs déjà croisés).

  <nom>             croiser un joueur              ex : [IMP] Pizza
  top [1v1|2v2]     afficher le top 100, recherche en tapant (Tab = changer de mode)
  show <nom>        afficher la fiche (saisons dans le top 100), sans compter
  edit <nom>        modifier nom, trait et note (champs pré-remplis), sans compter
  list              lister les joueurs déjà croisés
  delete <nom>      supprimer un joueur du carnet (confirmation)
  reset             vider le carnet (confirmation)
  export <fichier>  exporter le carnet vers un fichier   ex : export antho.json
  import <fichier>  fusionner un carnet exporté          ex : import kevin.json
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
    ):
        self.carnet = carnet
        self.chemin_carnet = Path(chemin_carnet)
        self.classement = classement
        self.maintenant = maintenant
        self.couleur = couleur
        self.saison_passee = saison_passee
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
        lignes = [self._ligne_rangs(nom, self.classement, self._c(f"Saison {actuelle} : ", "info"))]
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
    ) -> str:
        lignes = [self._c(nom, "nom")]
        if historique and self.classement is not None:
            lignes += self._lignes_saisons(nom)
        else:
            lignes.append(self._ligne_rangs(nom))
        if joueur is None or joueur.rencontres == 0:
            autres = self._croise_par(joueur) if joueur else []
            texte = f"Croisé par {', '.join(autres)}." if autres else "Jamais croisé."
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
        if joueur and joueur.memo:
            lignes.append("  Note : " + joueur.memo)
        traits = joueur.traits if joueur else {}
        if not traits:
            lignes.append("  Trait : " + self._c("pas encore noté", "info"))
        for auteur, note in sorted(traits.items(), key=lambda a: a[0] != self.carnet.auteur):
            lignes.append(f"  Trait ({self._c(auteur, 'auteur')}) : " + self._c(decorer(note.texte), "trait"))
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
        return self._fiche(nom, self.carnet.trouver(nom), historique=True)

    def modifier(self, nom: str) -> str:
        """Fiche d'un joueur déjà croisé, avant de changer son nom, son trait ou sa note : ne compte rien."""
        nom = self.nom_canonique(nom)
        joueur = self.carnet.trouver(nom)
        if joueur is None:
            return self._c(f"« {nom} » n'est pas dans le carnet : saisir d'abord son nom.", "erreur")
        return self._fiche(joueur.nom, joueur)

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
        colonne = min(max(largeur(l["name"]) for _, l in gardees), 30)
        lignes = [self._c("Rang " + ajuster("Nom", colonne) + "  Points", "info")]
        for position, ligne in gardees:
            vu = self._c(f"  vu {vus[ligne['name'].casefold()]}x", "info") if ligne["name"].casefold() in vus else ""
            lignes.append(
                self._c(f"#{position:<4}", role_rang(position))
                + self._c(ajuster(ligne["name"], colonne), "nom")
                + self._c(f"  {ligne['rating']} pts", "info")
                + vu
            )
        return titre + "\n" + "\n".join("  " + l for l in lignes)

    def mon_trait(self, nom: str) -> str:
        joueur = self.carnet.trouver(nom)
        note = joueur.traits.get(self.carnet.auteur) if joueur else None
        return note.texte if note else ""

    def mon_memo(self, nom: str) -> str:
        joueur = self.carnet.trouver(nom)
        return joueur.memo if joueur else ""

    def memoriser(self, nom: str, texte: str) -> str:
        nom = self.nom_canonique(nom)
        self.carnet.memoriser(nom, texte)
        if self.carnet.trouver(nom) is None:
            return self._c("Rien à effacer : joueur absent du carnet.", "info")
        self._sauver()
        if self.mon_memo(nom):
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
        """Qui connaît ce joueur : le propriétaire s'il l'a croisé (ou noté), puis les auteurs des traits importés."""
        moi = self.carnet.auteur
        noms = [moi] if (joueur.rencontres or joueur.memo or moi in joueur.traits) else []
        return noms + sorted((a for a in joueur.traits if a != moi), key=str.casefold)

    def liste(self) -> str:
        """Joueurs du carnet par ordre alphabétique, écritures non latines à la fin, avec un en-tête.
        Concise : ni « croisé par » ni auteur des traits (ils restent dans `show`)."""
        joueurs = sorted(
            (j for j in self.carnet.joueurs if j.rencontres or j.traits or j.memo),
            key=lambda j: cle_alphabetique(j.nom),
        )
        if not joueurs:
            return "Aucun joueur dans le carnet."
        def traits(j: Joueur) -> str:
            # sans les auteurs (concis) : mon trait d'abord, chaque trait identique une seule fois
            textes = dict.fromkeys(
                decorer(n.texte)
                for _, n in sorted(j.traits.items(), key=lambda a: a[0] != self.carnet.auteur)
            )
            return " | ".join(textes)

        cellules = [
            (
                j.nom,
                tronquer(j.memo, 50),
                traits(j),
                f"{j.rencontres}x, {_date_fr(j.derniere)}" if j.rencontres else "",
            )
            for j in joueurs
        ]
        en_tete = ("Nom", "Note", "Traits", "Vu")
        plafonds = (30, 50, 60, 16)
        colonnes = [min(max(largeur(c[i]) for c in cellules + [en_tete]), plafonds[i]) for i in range(4)]
        roles = ("nom", None, "trait", "info")

        def rangee(textes, colorer: bool) -> str:
            # la dernière colonne n'est pas complétée : rien en fin de ligne, en couleur comme sans
            morceaux = [ajuster(t, l) for t, l in zip(textes[:-1], colonnes)] + [textes[-1]]
            if colorer:
                morceaux = [self._c(m, r) if r and m.strip() else m for m, r in zip(morceaux, roles)]
            return sans_fin("  " + "  ".join(morceaux))

        lignes = [f"{len(joueurs)} joueur(s) :", self._c(rangee(en_tete, False), "info")]
        lignes += [rangee(c, True) for c in cellules]
        return "\n".join(lignes)

    def exporter(self, chemin: str) -> str:
        if not chemin:
            return "Fichier manquant.  ex : export antho.json"
        cible = Path(chemin).expanduser()
        if cible.suffix == "":
            cible = cible.with_suffix(".json")
        if cible.resolve() == self.chemin_carnet.resolve():
            return self._c("Export impossible : ce fichier est le carnet lui-même.", "erreur")
        try:
            self.carnet.sauver(cible, avec_memos=False)
        except OSError as erreur:
            return self._c(f"Impossible d'écrire {cible} : {erreur.strerror or erreur}", "erreur")
        return f"Carnet exporté dans {cible.resolve()}."

    def importer(self, chemin: str) -> str:
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
        bilan = self.carnet.fusionner(autre)
        self._sauver()
        return (
            f"Carnet de {autre.auteur} fusionné : {bilan.joueurs_ajoutes} joueur(s) ajouté(s), "
            f"{bilan.traits_ajoutes} trait(s) ajouté(s), {bilan.traits_maj} trait(s) mis à jour. "
            "Traits et notes perso existants inchangés."
        )

    def noms(self) -> list:
        noms = {j.nom for j in self.carnet.joueurs}
        if self.classement:
            noms |= self.classement.noms()
        return sorted(noms, key=str.casefold)
