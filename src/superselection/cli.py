"""Point d'entrée : boucle interactive avec auto-complétion (Linux, macOS, Windows)."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from platformdirs import user_cache_dir, user_data_dir

from .app import AIDE, COMMANDES, App, analyser
from .carnet import Carnet
from .classement import MODES, charger_classement, fetch_http

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


def executer(app: App, ligne: str, demander: Demander) -> bool:
    """Exécute une ligne. Renvoie False pour quitter."""
    commande, argument = analyser(ligne)
    if commande == "rien":
        return True
    if commande == "quitter":
        return False
    if commande == "aide":
        print(AIDE)
    elif commande == "liste":
        print(app.liste())
    elif commande == "export":
        print(app.exporter(argument))
    elif commande == "import":
        print(app.importer(argument))
    elif commande == "maj":
        app.classement, message = charger_classement(
            dossiers()[1] / "classement.json", fetch_http, maintenant()
        )
        print(message or f"Classement rechargé (saison {app.classement.saison}).")
    elif commande == "voir":
        print(app.voir(argument) if argument else "Indique un nom.  ex : voir [IMP] Pizza")
    elif commande == "croiser":
        if not argument:
            print("Indique un nom.  ex : joueur liste")
            return True
        print(app.croiser(argument))
        nom = app._nom_canonique(argument)
        actuel = app.mon_style(nom)
        question = (
            "  Nouveau style ? (Entrée = garder, - = effacer) > "
            if actuel
            else "  Son style ? (Entrée = passer) > "
        )
        reponse = demander(question, "").strip()
        if reponse == "-" and actuel:
            app.noter(nom, "")
            print("  Style effacé.")
        elif reponse and reponse != "-" and reponse != actuel:
            app.noter(nom, reponse)
            print("  Style enregistré.")
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
            elif commande in ("voir", "croiser"):
                yield from self._noms(reste)
            elif texte:
                if not espace:
                    for c in ("voir", "liste", "export", "import", "maj", "aide", "quitter"):
                        if c.startswith(texte.casefold()):
                            yield Completion(c, start_position=-len(texte), display_meta="commande")
                yield from self._noms(texte)

    return PromptSession(completer=Completeur(), complete_while_typing=True)


def main(argv: list | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")  # vieille console Windows : pas de crash sur 妮蔻
        except AttributeError:
            pass

    donnees, cache = dossiers()
    chemin_carnet = donnees / "carnet.json"
    interactif = sys.stdin.isatty()

    if chemin_carnet.exists():
        carnet = Carnet.charger(chemin_carnet)
    else:
        print("Bienvenue ! Premier lancement.")
        pseudo = ""
        while not pseudo:
            pseudo = input("Ton pseudo (il signe tes notes quand tu partages ton carnet) : ").strip()
        carnet = Carnet(auteur=pseudo)
        carnet.sauver(chemin_carnet)
        print(f"Carnet créé : {chemin_carnet}")

    print("Chargement du classement top 100…", end=" ", flush=True)
    classement, message = charger_classement(cache / "classement.json", fetch_http, maintenant())
    print(message or f"saison {classement.saison} OK.")

    app = App(carnet, chemin_carnet, classement, aujourd_hui=aujourd_hui, maintenant=maintenant)

    if interactif:
        session = _session(app)

        def demander(question: str, defaut: str) -> str:
            return session.prompt(question, default=defaut, completer=None)

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

    print("Tape un nom de joueur (Tab pour compléter), « aide » pour les commandes.")
    while True:
        try:
            ligne = session.prompt("adversaire > ")
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        if not executer(app, ligne, demander):
            break
    print("À plus !")


if __name__ == "__main__":
    main()
