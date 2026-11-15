"""Point d'entrée : boucle interactive avec auto-complétion (Linux, macOS, Windows)."""

from __future__ import annotations

import builtins
import os
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Callable

from platformdirs import user_cache_dir, user_data_dir

from .app import AIDE, COMMANDES, NOMS_COMMANDES, App, analyser
from .carnet import Carnet, CarnetInvalide
from .classement import MODES, charger_classement, fetch_http
from .couleurs import colorer_aide, peindre
from .styles import aide_styles, tags_commencant_par
from .texte import sans_controle
from .version import fetch_pyproject, lancer_mise_a_jour, nouvelle_version, version_installee

Demander = Callable[[str, str], str]  # (question, valeur par défaut) -> réponse


def dossiers() -> tuple:
    racine = os.environ.get("SUPERSELECTION_DIR")
    if racine:
        return Path(racine), Path(racine)
    return (
        Path(user_data_dir("superselection", appauthor=False, roaming=True)),
        Path(user_cache_dir("superselection", appauthor=False)),
    )


def maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def aujourd_hui() -> str:
    return datetime.now().date().isoformat()


_COULEUR = False  # activé par main() si le terminal le permet


def couleur_possible() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def afficher(*morceaux, end: str = "\n", flush: bool = False) -> None:
    """print() qui passe par prompt_toolkit en couleur (marche aussi sur les vieilles consoles Windows)."""
    texte = " ".join(str(m) for m in morceaux)
    if _COULEUR:
        from prompt_toolkit import print_formatted_text
        from prompt_toolkit.formatted_text import ANSI

        print_formatted_text(ANSI(texte), end=end, flush=flush)
    else:
        builtins.print(texte, end=end, flush=flush)


def c(texte: str, role: str) -> str:
    return peindre(texte, role, _COULEUR)


def executer(app: App, ligne: str, demander: Demander) -> bool:
    """Exécute une ligne. Renvoie False pour quitter."""
    commande, argument = analyser(ligne, app.noms())
    if commande == "rien":
        return True
    if commande == "quit":
        return False
    if commande == "help":
        afficher(colorer_aide(AIDE) if _COULEUR else AIDE)
    elif commande == "styles":
        afficher(aide_styles())
    elif commande == "list":
        afficher(app.liste())
    elif commande == "export":
        afficher(app.exporter(argument))
    elif commande == "import":
        afficher(app.importer(argument))
    elif commande == "refresh":
        app.classement, message = charger_classement(
            dossiers()[1] / "classement.json", fetch_http, maintenant()
        )
        afficher(c(message, "erreur") if message else c(f"Classement rechargé (saison {app.classement.saison}).", "ok"))
    elif commande == "version":
        afficher(f"superselection {version_installee()}")
    elif commande == "update":
        actuelle = version_installee()
        nouvelle = nouvelle_version(actuelle, fetch_pyproject)
        if nouvelle is None:
            afficher(c(f"Déjà à jour (version {actuelle}).", "ok"))
            return True
        afficher(f"Mise à jour {actuelle} -> {nouvelle}…")
        afficher(c(lancer_mise_a_jour(), "ok"))
        return False
    elif commande == "show":
        afficher(app.voir(argument) if argument else c("Indique un nom.  ex : show [IMP] Pizza", "info"))
    elif commande == "croiser":
        if not argument:
            afficher(c("Indique un nom.  ex : player list", "info"))
            return True
        afficher(app.croiser(argument))
        nom = app.nom_canonique(argument)
        actuel = app.mon_style(nom)
        question = (
            "  Nouveau style ? " + c("(Tab = mots-clés, Entrée = garder, - = effacer)", "info") + " > "
            if actuel
            else "  Son style ? " + c("(Tab = mots-clés, Entrée = passer)", "info") + " > "
        )
        try:
            reponse = demander(question, "").strip()
        except (KeyboardInterrupt, EOFError):
            reponse = ""  # Ctrl+C / Ctrl+D : on garde le style actuel
        if reponse == "-" and actuel:
            app.noter(nom, "")
            afficher("  " + c("Style effacé.", "ok"))
        elif reponse and reponse != "-" and reponse != actuel:
            app.noter(nom, reponse)
            afficher("  " + c("Style enregistré.", "ok"))
    return True


def _session(app: App):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.document import Document

    chemins = PathCompleter(expanduser=True)

    class Completeur(Completer):
        def _meta(self, nom: str) -> str:
            if app.classement is None:
                return ""
            rangs = [
                f"{mode} #{r.position}" for mode in MODES if (r := app.classement.rang(nom, mode))
            ]
            joueur = app.carnet.trouver(nom)
            if joueur and joueur.rencontres:
                rangs.append(f"vu {joueur.rencontres}x")
            return " · ".join(rangs)

        def _noms(self, fragment: str):
            cle = fragment.casefold()
            trouves = [n for n in app.noms() if cle in n.casefold()]
            trouves.sort(key=lambda n: (not n.casefold().startswith(cle), n.casefold()))
            for nom in trouves[:40]:
                yield Completion(nom, start_position=-len(fragment), display_meta=self._meta(nom))

        def get_completions(self, document, complete_event):
            texte = document.text_before_cursor.lstrip()
            mot, espace, reste = texte.partition(" ")
            commande = COMMANDES.get(mot.casefold()) if espace else None
            if commande in ("import", "export"):
                yield from chemins.get_completions(Document(reste), complete_event)
            elif commande in ("show", "croiser"):
                yield from self._noms(reste)
            elif texte:
                if not espace:
                    for c in NOMS_COMMANDES:
                        if c.startswith(texte.casefold()):
                            yield Completion(c, start_position=-len(texte), display_meta="commande")
                yield from self._noms(texte)

    class CompleteurStyle(Completer):
        """Complète le dernier mot avec les mots-clés de style (aggressive, defence…)."""

        def get_completions(self, document, complete_event):
            mot = re.search(r"\w*$", document.text_before_cursor).group(0)
            if not mot:
                return
            for tag in tags_commencant_par(mot):
                yield Completion(tag.nom, start_position=-len(mot), display_meta=f"{tag.emoji} {tag.sens}")

    return PromptSession(completer=Completeur(), complete_while_typing=True), CompleteurStyle()


def _attendre_fermeture() -> None:
    """Garde la fenêtre ouverte (raccourci Windows) pour que l'erreur reste lisible."""
    if sys.stdin.isatty():
        try:
            input("Appuie sur Entrée pour fermer…")
        except (EOFError, KeyboardInterrupt):
            pass


def main(argv: list | None = None) -> None:
    try:
        _principal(sys.argv[1:] if argv is None else argv)
    except CarnetInvalide as erreur:
        _echec_carnet(erreur)
    except Exception as erreur:  # dernier filet : jamais de traceback brut devant l'utilisateur
        _echec_inattendu(erreur)


def _echec_carnet(erreur: Exception) -> None:
    afficher(c(f"Ton carnet est illisible : {dossiers()[0] / 'carnet.json'}", "erreur"))
    afficher(f"  {erreur}")
    afficher("Corrige ce fichier ou renomme-le pour repartir d'un carnet vide.")
    _attendre_fermeture()
    sys.exit(1)


def _echec_inattendu(erreur: Exception) -> None:
    afficher(c(f"Erreur inattendue : {type(erreur).__name__} : {erreur}", "erreur"))
    journal = dossiers()[0] / "erreur.log"
    try:
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(
            "".join(traceback.format_exception(type(erreur), erreur, erreur.__traceback__)),
            encoding="utf-8",
        )
        afficher(f"Détail écrit dans : {journal}")
    except OSError:
        pass
    _attendre_fermeture()
    sys.exit(1)


def _charger_carnet(chemin_carnet: Path, interactif: bool) -> Carnet | None:
    """Le carnet existant, un carnet neuf après le premier lancement, ou None si on doit sortir."""
    if chemin_carnet.exists():
        try:
            return Carnet.charger(chemin_carnet)
        except OSError as erreur:
            raise CarnetInvalide(str(erreur)) from erreur
    if not interactif:
        afficher(
            "Premier lancement : lance « superselection » dans un terminal pour choisir ton pseudo."
        )
        sys.exit(1)
    afficher("Bienvenue ! Premier lancement.")
    pseudo = ""
    while not pseudo:
        try:
            pseudo = sans_controle(
                input("Ton pseudo (il signe tes notes quand tu partages ton carnet) : ")
            ).strip()
        except (KeyboardInterrupt, EOFError):
            afficher("")
            return None
    carnet = Carnet(auteur=pseudo)
    carnet.sauver(chemin_carnet)
    afficher(c(f"Carnet créé : {chemin_carnet}", "ok"))
    return carnet


def _principal(argv: list) -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")  # vieille console Windows : pas de crash sur 妮蔻
        except AttributeError:
            pass

    global _COULEUR
    _COULEUR = couleur_possible()

    donnees, cache = dossiers()
    chemin_carnet = donnees / "carnet.json"
    interactif = sys.stdin.isatty()

    carnet = _charger_carnet(chemin_carnet, interactif)
    if carnet is None:
        return

    afficher("Chargement du classement top 100…", end=" ", flush=True)
    with ThreadPoolExecutor(max_workers=1) as fond:  # vérifie la version pendant le chargement
        verif = fond.submit(nouvelle_version, version_installee(), fetch_pyproject)
        classement, message = charger_classement(cache / "classement.json", fetch_http, maintenant())
        afficher(c(message, "erreur") if message else c(f"saison {classement.saison} OK.", "ok"))
        nouvelle = verif.result()
    if nouvelle:
        afficher(
            c(f"Nouvelle version {nouvelle} disponible", "top10")
            + f" (tu as {version_installee()}) : tape « {c('update', 'commande')} »."
        )

    app = App(
        carnet, chemin_carnet, classement, aujourd_hui=aujourd_hui, maintenant=maintenant, couleur=_COULEUR
    )

    if interactif:
        from prompt_toolkit.formatted_text import ANSI

        session, completeur_style = _session(app)

        def demander(question: str, defaut: str) -> str:
            return session.prompt(ANSI(question), default=defaut, completer=completeur_style)

    else:

        def demander(question: str, defaut: str) -> str:
            return defaut

    if argv:
        executer(app, " ".join(argv), demander)
        return

    if not interactif:
        for ligne in sys.stdin:
            if not executer(app, ligne, demander):
                break
        return

    afficher("Tape un nom de joueur " + c("(Tab pour compléter)", "info") + ", « " + c("help", "commande") + " » pour les commandes.")
    while True:
        try:
            ligne = session.prompt(ANSI(c("adversaire", "invite") + " > "))
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        try:
            if not executer(app, ligne, demander):
                break
        except OSError as erreur:
            afficher(
                c(
                    f"Impossible d'enregistrer le carnet : {erreur.strerror or erreur}. "
                    "Ferme le programme qui utilise ce fichier ; l'enregistrement sera "
                    "refait à la prochaine saisie.",
                    "erreur",
                )
            )
    afficher("À plus !")


if __name__ == "__main__":
    main()
