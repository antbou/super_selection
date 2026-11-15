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
from .classement import MODES, charger_classement, charger_saison, fetch_http
from .couleurs import colorer_aide, peindre, sans_couleur
from .traits import aide_traits, tags_commencant_par
from .texte import sans_controle
from .version import etat_version, fetch_pyproject, lancer_mise_a_jour, nouvelle_version, version_installee

# (question, valeur par défaut, genre) -> réponse ; genre : "trait" (mots-clés), "nom" (noms), "texte" (rien)
Demander = Callable[..., str]


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


def _noter(app: App, nom: str, reponse: str) -> None:
    erreur = app.noter(nom, reponse)
    if erreur:
        afficher("  " + erreur.replace("\n", "\n  "))
    else:
        afficher("  " + c("Trait enregistré." if reponse else "Trait effacé.", "ok"))


def _questions(app: App, nom: str, demander: Demander) -> None:
    """Demande le trait puis la note perso ; Ctrl+C / Ctrl+D : on garde tout."""
    actuel = app.mon_trait(nom)
    question = (
        "  Nouveau trait ? " + c("(Tab = mots-clés, Entrée = garder, - = effacer)", "info") + " > "
        if actuel
        else "  Son trait ? " + c("(Tab = mots-clés, Entrée = passer)", "info") + " > "
    )
    try:
        reponse = demander(question, "", genre="trait").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if reponse == "-" and actuel:
        app.noter(nom, "")
        afficher("  " + c("Trait effacé.", "ok"))
    elif reponse and reponse != "-" and reponse != actuel:
        _noter(app, nom, reponse)
    memo = app.mon_memo(nom)
    question = (
        "  Nouvelle note ? " + c("(texte privé, Entrée = garder, - = effacer)", "info") + " > "
        if memo
        else "  Une note ? " + c("(texte libre privé, Entrée = passer)", "info") + " > "
    )
    try:
        reponse = demander(question, "", genre="texte").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if reponse == "-" and memo:
        afficher("  " + app.memoriser(nom, ""))
    elif reponse and reponse != "-" and reponse != memo:
        afficher("  " + app.memoriser(nom, reponse))


def _editer(app: App, nom: str, demander: Demander) -> None:
    """Fiche puis nom, trait et note déjà remplis : Entrée garde, on corrige sur place, vide = effacer."""
    afficher(app.modifier(nom))
    if app.carnet.trouver(nom) is None:
        return
    try:
        nouveau = demander("  Nom   > ", nom, genre="nom").strip()
        if nouveau and nouveau != nom:
            afficher("  " + app.renommer(nom, nouveau))
            if (joueur := app.carnet.trouver(nouveau)) is not None and app.carnet.trouver(nom) is None:
                nom = joueur.nom
        trait = app.mon_trait(nom)
        reponse = demander("  Trait > ", trait, genre="trait").strip()
        if reponse == "-":  # comme à la rencontre : « - » efface
            reponse = ""
        if reponse != trait:
            _noter(app, nom, reponse)
        memo = app.mon_memo(nom)
        reponse = demander("  Note  > ", memo, genre="texte").strip()
        if reponse == "-":
            reponse = ""
        if reponse != memo:
            afficher("  " + app.memoriser(nom, reponse))
    except (KeyboardInterrupt, EOFError):
        return  # Ctrl+C / Ctrl+D : on garde ce qui est déjà enregistré


def executer(app: App, ligne: str, demander: Demander) -> bool:
    """Exécute une ligne. Renvoie False pour quitter."""
    commande, argument = analyser(ligne, app.noms())
    if commande == "rien":
        return True
    if commande == "quit":
        return False
    if commande == "help":
        afficher(colorer_aide(AIDE) if _COULEUR else AIDE)
    elif commande == "traits":
        afficher(aide_traits())
    elif commande == "list":
        afficher(app.liste())
    elif commande == "delete":
        if not argument:
            afficher(c("Indique un nom.  ex : delete Pizza", "info"))
        elif (joueur := app.carnet.trouver(argument)) is None:
            afficher(app.supprimer(argument))
        else:
            question = (
                f"  Supprimer {joueur.nom} ({joueur.rencontres} rencontre(s), {len(joueur.traits)} trait(s)) ? "
                + c("(o = oui, Entrée = non)", "info") + " > "
            )
            try:
                reponse = demander(question, "", genre="texte").strip().casefold()
            except (KeyboardInterrupt, EOFError):
                reponse = ""
            afficher(app.supprimer(argument) if reponse in ("o", "oui", "y", "yes") else c("Annulé.", "info"))
    elif commande == "reset":
        nombre = len(app.carnet.joueurs)
        if nombre == 0:
            afficher(c("Le carnet est déjà vide.", "info"))
        else:
            question = (
                c(f"  Supprimer TOUT le carnet ({nombre} joueur(s), rencontres et traits) ? Irréversible. ", "erreur")
                + c("(tape « oui », Entrée = non)", "info") + " > "
            )
            try:
                reponse = demander(question, "", genre="texte").strip().casefold()
            except (KeyboardInterrupt, EOFError):
                reponse = ""
            afficher(app.vider() if reponse == "oui" else c("Annulé.", "info"))
    elif commande == "edit":
        if not argument:
            afficher(c("Indique un nom.  ex : edit [IMP] Pizza", "info"))
            return True
        _editer(app, app.nom_canonique(argument), demander)
    elif commande == "rename":
        afficher(c("`rename` n'existe plus : utilise « edit <nom> » pour changer un nom.", "info"))
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
        etat, nouvelle = etat_version(actuelle, fetch_pyproject)
        if etat == "injoignable":
            afficher(c("Impossible de vérifier la dernière version (pas d'internet ?). Réessaie plus tard.", "erreur"))
            return True
        if etat == "a_jour":
            afficher(c(f"Déjà à jour (version {actuelle}).", "ok"))
            return True
        afficher(f"Mise à jour {actuelle} -> {nouvelle}…")
        afficher(c(lancer_mise_a_jour(), "ok"))
        return False
    elif commande == "top":
        mode, filtre = app.lire_top(argument)
        if filtre or not sys.stdin.isatty():
            afficher(app.top(mode, filtre))
        else:
            _recherche_top(app, mode)
    elif commande == "show":
        afficher(app.voir(argument) if argument else c("Indique un nom.  ex : show [IMP] Pizza", "info"))
    elif commande == "croiser":
        if not argument:
            afficher(c("Indique un nom.  ex : player list", "info"))
            return True
        afficher(app.croiser(argument))
        _questions(app, app.nom_canonique(argument), demander)
    return True


DEBOUNCE = 0.12  # secondes entre la dernière frappe et le filtrage


def _recherche_top(app: App, mode: str) -> None:
    """Écran du top 100 : on tape, la liste se filtre (avec debounce). Tab = 1v1/2v2, Échap = sortir."""
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import BufferControl, FormattedTextControl, HSplit, Layout, VSplit, Window

    etat = {"mode": mode, "filtre": "", "minuteur": None, "defilement": 0}
    couleur = _COULEUR

    def lignes_visibles() -> list:
        rendu_top = app.top(etat["mode"], etat["filtre"])
        return (rendu_top if couleur else sans_couleur(rendu_top)).split("\n")

    def rendu():
        return ANSI("\n".join(lignes_visibles()[etat["defilement"]:]))

    saisie = Buffer()
    invite = Window(FormattedTextControl(lambda: ANSI(c("recherche > ", "invite"))), width=12, height=1)

    def planifier(_):
        if etat["minuteur"]:
            etat["minuteur"].cancel()

        def appliquer():
            etat["filtre"], etat["defilement"] = saisie.text, 0
            application.invalidate()

        etat["minuteur"] = application.loop.call_later(DEBOUNCE, appliquer)

    saisie.on_text_changed += planifier

    saisie_fenetre = Window(BufferControl(saisie), height=1)
    touches = KeyBindings()

    @touches.add("tab")
    def _(event):
        etat["mode"] = "2v2" if etat["mode"] == "1v1" else "1v1"
        etat["defilement"] = 0

    @touches.add("down")
    @touches.add("pagedown")
    def _(event):
        etat["defilement"] = min(etat["defilement"] + 5, max(len(lignes_visibles()) - 2, 0))

    @touches.add("up")
    @touches.add("pageup")
    def _(event):
        etat["defilement"] = max(etat["defilement"] - 5, 0)

    @touches.add("escape", eager=True)
    @touches.add("enter")
    @touches.add("c-c")
    @touches.add("c-d")
    def _(event):
        event.app.exit()

    barre = FormattedTextControl(lambda: ANSI(c(f"  {etat['mode']}", "invite") + c("  Tab = 1v1/2v2 · ↑↓ défiler · Échap = sortir", "info")))
    layout = Layout(
        HSplit([
            Window(FormattedTextControl(rendu)),
            Window(barre, height=1),
            VSplit([invite, saisie_fenetre]),
        ]),
        focused_element=saisie_fenetre,
    )
    application = Application(layout=layout, key_bindings=touches, full_screen=True)
    application.run()


def _completeurs(app: App):
    """Les trois compléteurs : noms + commandes, noms seuls (champ « Nom » d'edit), mots-clés de trait."""
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.document import Document

    chemins = PathCompleter(expanduser=True)

    class Completeur(Completer):
        def _meta(self, nom: str) -> str:
            if app.classement is None:
                return ""
            rangs = [
                f"{mode} " + "/".join(f"#{r.position}" for r in trouves)
                for mode in MODES
                if (trouves := app.classement.rangs(nom, mode))
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
            elif commande in ("show", "edit", "croiser", "delete"):
                yield from self._noms(reste)
            elif texte:
                if not espace:
                    for c in NOMS_COMMANDES:
                        if c.startswith(texte.casefold()):
                            yield Completion(c, start_position=-len(texte), display_meta="commande")
                yield from self._noms(texte)

    class CompleteurTrait(Completer):
        """Complète le dernier mot avec les mots-clés de trait (aggressive, defence…)."""

        def get_completions(self, document, complete_event):
            mot = re.search(r"\w*$", document.text_before_cursor).group(0)
            for tag in tags_commencant_par(mot):  # mot vide : les cinq, sans taper de lettre
                yield Completion(tag.nom, start_position=-len(mot), display_meta=f"{tag.emoji} {tag.sens}")

    class CompleteurNom(Completer):
        """Seulement des noms (pas de commandes) : on corrige un nom, on ne tape pas une ligne."""

        def get_completions(self, document, complete_event):
            yield from Completeur()._noms(document.text_before_cursor.lstrip())

    return Completeur(), CompleteurNom(), CompleteurTrait()


def _session(app: App):
    """Renvoie (session principale, demander). Une session par genre de question, compléteur fixé
    à la construction : prompt() garde sur la session tout ce qu'on lui passe."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.history import DummyHistory

    completeur, completeur_nom, completeur_trait = _completeurs(app)
    principale = PromptSession(completer=completeur, complete_while_typing=True)
    sessions = {
        "trait": PromptSession(completer=completeur_trait, complete_while_typing=True, history=DummyHistory()),
        "nom": PromptSession(completer=completeur_nom, complete_while_typing=True, history=DummyHistory()),
        "texte": PromptSession(history=DummyHistory()),
    }

    def demander(question: str, defaut: str, genre: str = "texte") -> str:
        session = sessions[genre]
        if genre == "trait":  # les cinq traits s'affichent dès l'ouverture, sans taper de lettre
            return session.prompt(
                ANSI(question),
                default=defaut,
                pre_run=lambda: session.app.current_buffer.start_completion(select_first=False),
            )
        return session.prompt(ANSI(question), default=defaut)

    return principale, demander


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
                input("Ton pseudo (il signe tes traits quand tu partages ton carnet) : ")
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
        carnet,
        chemin_carnet,
        classement,
        maintenant=maintenant,
        couleur=_COULEUR,
        saison_passee=lambda n: charger_saison(cache, fetch_http, n, maintenant()),
    )

    if interactif:
        from prompt_toolkit.formatted_text import ANSI

        session, demander = _session(app)

    else:

        def demander(question: str, defaut: str, genre: str = "texte") -> str:
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
