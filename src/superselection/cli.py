"""Point d'entrée : boucle interactive avec auto-complétion (Linux, macOS, Windows)."""

from __future__ import annotations

import builtins
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from platformdirs import user_cache_dir, user_data_dir

from .app import AIDE, COMMANDES, NOMS_COMMANDES, App, analyser
from .carnet import Carnet
from .classement import MODES, charger_classement, fetch_http
from .couleurs import colorer_aide, peindre
from .styles import aide_styles, tags_commencant_par

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
    commande, argument = analyser(ligne)
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
    elif commande == "show":
        afficher(app.voir(argument) if argument else c("Indique un nom.  ex : show [IMP] Pizza", "info"))
    elif commande == "croiser":
        if not argument:
            afficher(c("Indique un nom.  ex : player list", "info"))
            return True
        afficher(app.croiser(argument))
        nom = app._nom_canonique(argument)
        actuel = app.mon_style(nom)
        question = (
            "  Nouveau style ? " + c("(Tab = mots-clés, Entrée = garder, - = effacer)", "info") + " > "
            if actuel
            else "  Son style ? " + c("(Tab = mots-clés, Entrée = passer)", "info") + " > "
        )
        reponse = demander(question, "").strip()
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


def main(argv: list | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
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

    if chemin_carnet.exists():
        carnet = Carnet.charger(chemin_carnet)
    else:
        afficher("Bienvenue ! Premier lancement.")
        pseudo = ""
        while not pseudo:
            pseudo = input("Ton pseudo (il signe tes notes quand tu partages ton carnet) : ").strip()
        carnet = Carnet(auteur=pseudo)
        carnet.sauver(chemin_carnet)
        afficher(c(f"Carnet créé : {chemin_carnet}", "ok"))

    afficher("Chargement du classement top 100…", end=" ", flush=True)
    classement, message = charger_classement(cache / "classement.json", fetch_http, maintenant())
    afficher(c(message, "erreur") if message else c(f"saison {classement.saison} OK.", "ok"))

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
        if not executer(app, ligne, demander):
            break
    afficher("À plus !")


if __name__ == "__main__":
    main()
