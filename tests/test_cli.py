import pytest

from superselection import cli


@pytest.fixture
def isole(tmp_path, monkeypatch):
    """Dossier de données isolé, réseau coupé, pas de terminal."""
    monkeypatch.setenv("SUPERSELECTION_DIR", str(tmp_path))
    monkeypatch.setenv("NO_COLOR", "1")

    def panne(*args, **kwargs):
        raise OSError("pas de réseau")

    monkeypatch.setattr(cli, "fetch_http", panne)
    monkeypatch.setattr(cli, "fetch_pyproject", panne)
    return tmp_path


def test_carnet_illisible_message_sans_traceback(isole, capsys):
    carnet = isole / "notebook.json"
    carnet.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    sortie_texte = capsys.readouterr().out
    assert str(carnet) in sortie_texte
    assert "Traceback" not in sortie_texte
    assert carnet.read_text(encoding="utf-8") == "{"


def test_carnet_invalide_message_sans_traceback(isole, capsys):
    (isole / "notebook.json").write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    assert "illisible" in capsys.readouterr().out


def test_premier_lancement_sans_terminal(isole, capsys):
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    assert "Premier lancement : exécuter « superselection » dans un terminal" in capsys.readouterr().out
    assert not (isole / "notebook.json").exists()


def test_premier_lancement_ctrl_c_sur_le_pseudo(isole, monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def interrompu(_invite=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrompu)
    cli.main([])  # sort proprement
    assert not (isole / "notebook.json").exists()


def test_exception_inattendue_ecrit_erreur_log(isole, monkeypatch, capsys):
    (isole / "notebook.json").write_text('{"version": 2, "owner": "Antho", "players": []}', encoding="utf-8")

    def casse(*args, **kwargs):
        raise RuntimeError("boum")

    monkeypatch.setattr(cli, "charger_classement", casse)
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    sortie_texte = capsys.readouterr().out
    assert "Erreur inattendue : RuntimeError : boum" in sortie_texte
    assert "Traceback" not in sortie_texte
    journal = isole / "erreur.log"
    assert "RuntimeError" in journal.read_text(encoding="utf-8")
    assert str(journal) in sortie_texte


# --- executer : saisie du trait ------------------------------------------------

from test_app import nouvelle_app


def _trait(app, nom):
    joueur = app.carnet.trouver(nom)
    return (joueur.trait or None) if joueur else None


@pytest.mark.parametrize("erreur", [KeyboardInterrupt, EOFError])
def test_ctrl_c_ou_ctrl_d_sur_le_trait_annule_tout_le_nouveau_joueur(tmp_path, erreur, capsys):
    app = nouvelle_app(tmp_path)

    def demander(question, defaut, genre="texte"):
        raise erreur

    assert cli.executer(app, "Bob", demander) is True
    assert app.carnet.trouver("Bob") is None  # ni rencontre, ni joueur
    assert "Annulé" in capsys.readouterr().out
    assert not app.chemin_carnet.exists()  # rien n'a été écrit


def test_ctrl_c_sur_le_trait_annule_la_rencontre_et_garde_le_trait_actuel(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")

    def demander(question, defaut, genre="texte"):
        raise KeyboardInterrupt

    assert cli.executer(app, "Bob", demander) is True
    assert _trait(app, "Bob") == "noob"
    assert app.carnet.trouver("Bob").rencontres == 1


def test_trait_saisi_est_enregistre(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d, genre="texte": "noob, pro")
    assert _trait(app, "Bob") == "noob, pro"


def test_tiret_efface_le_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d, genre="texte": "noob")
    cli.executer(app, "Bob", lambda q, d, genre="texte": "-")
    assert _trait(app, "Bob") is None


def test_reponse_vide_garde_le_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d, genre="texte": "noob")
    app.maintenant = lambda: "2026-11-15T21:00"
    cli.executer(app, "Bob", lambda q, d, genre="texte": "")
    assert _trait(app, "Bob") == "noob"
    assert app.carnet.trouver("Bob").rencontres == 2


def test_boucle_interactive_continue_si_l_enregistrement_echoue(isole, monkeypatch, capsys):
    (isole / "notebook.json").write_text('{"version": 2, "owner": "Antho", "players": []}', encoding="utf-8")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    lignes = iter(["Bob", "quit"])

    class FausseSession:
        def prompt(self, *args, **kwargs):
            return next(lignes)

    monkeypatch.setattr(cli, "_session", lambda app: (FausseSession(), lambda q, d, genre="texte": d))

    def sauver_impossible(self, chemin):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(cli.Carnet, "sauver", sauver_impossible)
    cli.main([])
    sortie = capsys.readouterr().out
    assert "Impossible d'enregistrer le carnet" in sortie
    assert "Fermer le programme" in sortie


def test_joueur_nomme_comme_une_commande_est_croise(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Show Me")
    app.maintenant = lambda: "2026-11-15T21:00"
    assert cli.executer(app, "show me", lambda q, d, genre="texte": "") is True
    assert app.carnet.trouver("Show Me").rencontres == 2


def test_update_sans_internet_reste_dans_l_outil(tmp_path, monkeypatch, capsys):
    def panne():
        raise OSError("pas d'internet")

    monkeypatch.setattr(cli, "fetch_pyproject", panne)
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "update", lambda q, d, genre="texte": "") is True
    sortie = capsys.readouterr().out
    assert "Impossible de vérifier la dernière version" in sortie
    assert "Déjà à jour" not in sortie


# --- delete / rename -----------------------------------------------------------


@pytest.mark.parametrize("reponse,reste", [("o", None), ("", "Bob"), ("n", "Bob")])
def test_delete_demande_confirmation(tmp_path, reponse, reste):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    questions = []

    def demander(question, defaut, genre="texte"):
        questions.append(question)
        return reponse

    assert cli.executer(app, "delete bob", demander) is True
    assert len(questions) == 1
    assert (app.carnet.trouver("Bob") and "Bob") == reste


def test_delete_ctrl_c_annule(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")

    def demander(question, defaut, genre="texte"):
        raise KeyboardInterrupt

    cli.executer(app, "delete Bob", demander)
    assert app.carnet.trouver("Bob") is not None


def test_edit_renomme_puis_note_sans_recompter(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Pizza")
    reponses = iter(["Pizza2", "noob", ""])  # nom, trait, note
    cli.executer(app, "edit Pizza", lambda q, d, genre="texte": next(reponses))
    assert app.carnet.trouver("Pizza") is None
    assert app.carnet.trouver("Pizza2").rencontres == 1
    assert _trait(app, "Pizza2") == "noob"


@pytest.mark.parametrize("reponse,reste", [("oui", 0), ("o", 2), ("", 2), ("non", 2)])
def test_reset_demande_confirmation(tmp_path, reponse, reste):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.croiser("Alice")
    cli.executer(app, "reset", lambda question, defaut, genre="texte": reponse)
    assert len(app.carnet.joueurs) == reste
    from superselection.carnet import Carnet

    assert len(Carnet.charger(app.chemin_carnet).joueurs) == reste
    assert app.carnet.auteur == "Antho"


def test_reset_ctrl_c_annule(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")

    def demander(question, defaut, genre="texte"):
        raise KeyboardInterrupt

    cli.executer(app, "reset", demander)
    assert app.carnet.trouver("Bob") is not None


def test_reset_carnet_vide_ne_demande_rien(tmp_path, capsys):
    app = nouvelle_app(tmp_path)

    def demander(question, defaut, genre="texte"):
        raise AssertionError("pas de question")

    cli.executer(app, "reset", demander)
    assert "déjà vide" in capsys.readouterr().out


def _repondre(**reponses):
    """demander() qui répond selon le mot-clé présent dans la question (Trait / Note)."""
    questions = []

    def demander(question, defaut, genre="texte"):
        questions.append(question)
        for mot, reponse in reponses.items():
            if mot in question.casefold():
                return reponse
        return ""

    demander.questions = questions
    return demander


def test_croiser_propose_aussi_une_note(tmp_path):
    app = nouvelle_app(tmp_path)
    demander = _repondre(trait="noob", note="m'a insulté")
    cli.executer(app, "Bob", demander)
    assert _trait(app, "Bob") == "noob"
    assert app.note_actuelle("Bob") == "m'a insulté"
    assert len(demander.questions) == 2


def test_croiser_note_vide_ou_tiret(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", _repondre(note="x"))
    cli.executer(app, "Bob", _repondre(note=""))
    assert app.note_actuelle("Bob") == "x"
    cli.executer(app, "Bob", _repondre(note="-"))
    assert app.note_actuelle("Bob") == ""


def test_croiser_ctrl_c_sur_la_note_annule_aussi_le_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("Bob", "ancienne")  # Bob existe déjà (0 rencontre)

    def demander(question, defaut, genre="texte"):
        if "note" in question.casefold():
            raise KeyboardInterrupt
        return "noob"

    cli.executer(app, "Bob", demander)
    assert _trait(app, "Bob") is None
    assert app.carnet.trouver("Bob").rencontres == 0
    assert app.note_actuelle("Bob") == "ancienne"
    assert "noob" not in app.chemin_carnet.read_text(encoding="utf-8")


def test_edit_ctrl_c_annule_renommage_et_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Pizza")
    app.noter("Pizza", "noob")
    reponses = iter(["Pasta", "pro"])

    def demander(question, defaut, genre="texte"):
        try:
            return next(reponses)
        except StopIteration:
            raise KeyboardInterrupt

    cli.executer(app, "edit Pizza", demander)
    assert app.carnet.trouver("Pasta") is None
    assert _trait(app, "Pizza") == "noob"
    assert "Pasta" not in app.chemin_carnet.read_text(encoding="utf-8")


def test_erreur_inattendue_pendant_la_saisie_annule_aussi(tmp_path):
    app = nouvelle_app(tmp_path)

    def demander(question, defaut, genre="texte"):
        raise RuntimeError("boum")

    with pytest.raises(RuntimeError):
        cli.executer(app, "Bob", demander)
    assert app.carnet.trouver("Bob") is None


def test_saisie_complete_est_enregistree_une_fois_validee(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d, genre="texte": "noob")
    assert "Bob" in app.chemin_carnet.read_text(encoding="utf-8")


def test_top_commande_non_interactive(tmp_path, capsys):
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "top 2v2 unl", lambda q, d, genre="texte": "") is True
    sortie = capsys.readouterr().out
    assert "Unloukee" in sortie and "600 pts" in sortie
    assert app.carnet.trouver("top") is None  # ne compte pas de rencontre


def test_edit_champs_prerempli_entree_garde_tout(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "aggressive")
    app.memoriser("Bob", "joue le soir")
    app.maintenant = lambda: "2026-11-15T23:00"
    vus = []

    def entree(question, defaut, genre="texte"):
        vus.append(defaut)
        return defaut  # Entrée sur un champ pré-rempli

    cli.executer(app, "edit bob", entree)
    assert vus == ["Bob", "aggressive", "joue le soir"]
    bob = app.carnet.trouver("Bob")
    assert bob.rencontres == 1 and bob.derniere == "2026-11-15T20:00"
    assert _trait(app, "Bob") == "aggressive" and bob.note == "joue le soir"


def test_edit_corrige_sur_place_et_vide_efface(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "aggressive")
    app.memoriser("Bob", "joue le soir")
    reponses = iter(["Bob", "aggressive, noob", ""])  # nom gardé, trait corrigé, note vidée
    cli.executer(app, "edit Bob", lambda q, d, genre="texte": next(reponses))
    assert _trait(app, "Bob") == "aggressive, noob"
    assert app.carnet.trouver("Bob").note == ""


def test_edit_joueur_inconnu_ne_pose_aucune_question(tmp_path):
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "edit Zorglub", lambda q, d, genre="texte": pytest.fail("pas de question")) is True
    assert app.carnet.trouver("Zorglub") is None


def test_trait_hors_liste_est_refuse_et_signale(tmp_path, capsys):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d, genre="texte": "rush archers")
    sortie = capsys.readouterr().out
    assert "rush" in sortie and "Trait enregistré" not in sortie
    assert _trait(app, "Bob") is None


def test_traits_proposes_des_le_debut_sans_taper_de_lettre(tmp_path):
    from prompt_toolkit.document import Document

    _, _, completeur_trait = cli._completeurs(nouvelle_app(tmp_path))
    propositions = [c.text for c in completeur_trait.get_completions(Document(""), None)]
    assert propositions == ["aggressive", "defence", "noob", "tryhard", "pro"]
    apres_virgule = [c.text for c in completeur_trait.get_completions(Document("noob, "), None)]
    assert "pro" in apres_virgule
    assert "noob" not in apres_virgule  # déjà retenu


def test_edit_delete_et_show_ne_proposent_que_les_noms_du_carnet(tmp_path):
    from prompt_toolkit.document import Document

    app = nouvelle_app(tmp_path)
    app.croiser("Marco")
    completeur, _, _ = cli._completeurs(app)

    def propose(texte):
        return [c.text for c in completeur.get_completions(Document(texte), None)]

    assert propose("edit Un") == [] and propose("delete Un") == []
    assert propose("edit Mar") == ["Marco"]
    assert propose("show Un") == [] and propose("show Mar") == ["Marco"]
    assert "Unloukee" in propose("Un")  # saisie directe (rencontre) : tout le top 100


def test_session_principale_garde_ses_noms_apres_une_question_de_trait(tmp_path):
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.document import Document
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    app = nouvelle_app(tmp_path)
    app.croiser("Bobby")
    with create_pipe_input() as entree, create_app_session(input=entree, output=DummyOutput()):
        session, demander = cli._session(app)
        entree.send_text("noob\r")
        assert demander("  Trait > ", "", genre="trait") == "noob"
        entree.send_text("une note\r")
        assert demander("  Une note > ", "", genre="texte") == "une note"
        noms = [c.text for c in session.completer.get_completions(Document("Bob"), None)]
        assert "Bobby" in noms
        assert "noob" not in [c.text for c in session.completer.get_completions(Document("no"), None)]


def _genres(tmp_path, ligne, reponses=()):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.maintenant = lambda: "2026-11-15T23:00"
    genres = []
    suite = iter(reponses)

    def demander(question, defaut, genre="texte"):
        genres.append(genre)
        return next(suite, defaut)

    cli.executer(app, ligne, demander)
    return genres


def test_genres_des_questions(tmp_path):
    assert _genres(tmp_path, "delete Bob") == ["texte"]
    assert _genres(tmp_path, "reset") == ["texte"]
    assert _genres(tmp_path, "Bob") == ["trait", "texte"]
    assert _genres(tmp_path, "edit Bob") == ["nom", "trait", "texte"]


def test_edit_tiret_efface_le_trait(tmp_path, capsys):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")
    reponses = iter(["Bob", "-", ""])
    cli.executer(app, "edit Bob", lambda q, d, genre="texte": next(reponses))
    sortie = capsys.readouterr().out
    assert "Trait effacé." in sortie and "refusé" not in sortie
    assert _trait(app, "Bob") is None


def test_edit_tiret_efface_la_note(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.memoriser("Bob", "joue le soir")
    reponses = iter(["Bob", "", "-"])
    cli.executer(app, "edit Bob", lambda q, d, genre="texte": next(reponses))
    assert app.note_actuelle("Bob") == ""


def test_rename_renvoie_vers_edit_sans_creer_de_joueur(tmp_path, capsys):
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "rename Pizza > Pizzza", lambda q, d, genre="texte": pytest.fail("pas de question")) is True
    assert "« edit <nom> »" in capsys.readouterr().out
    assert app.carnet.joueurs == []


def test_update_echec_reste_dans_l_outil_et_pas_de_succes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "version_installee", lambda: "0.1.0")
    monkeypatch.setattr(cli, "fetch_pyproject", lambda: 'version = "9.9.9"\n')
    monkeypatch.setattr(cli, "lancer_mise_a_jour", lambda: (False, "uv introuvable."))
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "update", lambda q, d, genre="texte": "") is True
    sortie = capsys.readouterr().out
    assert "uv introuvable." in sortie and "terminée" not in sortie


def test_update_succes_quitte(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "version_installee", lambda: "0.1.0")
    monkeypatch.setattr(cli, "fetch_pyproject", lambda: 'version = "9.9.9"\n')
    monkeypatch.setattr(cli, "lancer_mise_a_jour", lambda: (True, "Mise à jour terminée."))
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "update", lambda q, d, genre="texte": "") is False
    assert "Mise à jour terminée." in capsys.readouterr().out


@pytest.mark.parametrize("ligne", ["traits", "styles"])
def test_traits_n_existe_plus_et_ne_cree_pas_de_joueur(tmp_path, capsys, ligne):
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, ligne, lambda q, d, genre="texte": pytest.fail("pas de question")) is True
    sortie = capsys.readouterr().out
    assert "n'existe plus" in sortie and "Tab" in sortie
    assert app.carnet.joueurs == []


def test_traits_absent_de_l_aide_et_de_la_completion():
    from superselection.app import AIDE, NOMS_COMMANDES
    assert "traits" not in NOMS_COMMANDES
    assert not any(l.strip().startswith("traits") for l in AIDE.splitlines())


@pytest.mark.parametrize("ligne", ["update --force", "update -f"])
def test_update_force_reinstalle_sans_verifier_la_version(tmp_path, monkeypatch, capsys, ligne):
    monkeypatch.setattr(cli, "fetch_pyproject", lambda: pytest.fail("pas de vérification"))
    monkeypatch.setattr(cli, "lancer_mise_a_jour", lambda: (True, "Mise à jour terminée."))
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, ligne, lambda q, d, genre="texte": "") is False
    sortie = capsys.readouterr().out
    assert "Réinstallation forcée" in sortie and "Mise à jour terminée." in sortie


def test_update_option_inconnue(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "lancer_mise_a_jour", lambda: pytest.fail("pas de mise à jour"))
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "update --vite", lambda q, d, genre="texte": "") is True
    assert "update --force" in capsys.readouterr().out


# --- migration et import interactif ------------------------------------------------


ANCIEN = '{"auteur": "Antho", "joueurs": [{"nom": "Bob", "rencontres": 2, "styles": {"Antho": {"texte": "noob", "maj": "2026-11-01"}}}]}'


def test_ancien_carnet_converti_au_lancement(isole, capsys):
    (isole / "carnet.json").write_text(ANCIEN, encoding="utf-8")
    cli.main(["list"])
    sortie = capsys.readouterr().out
    assert "Carnet converti au nouveau format" in sortie and "carnet.v1.bak.json" in sortie
    assert "Bob" in sortie and "noob" in sortie
    assert (isole / "notebook.json").exists() and not (isole / "carnet.json").exists()
    assert (isole / "carnet.v1.bak.json").read_text(encoding="utf-8") == ANCIEN


def test_ancien_carnet_illisible_rien_n_est_touche(isole, capsys):
    (isole / "carnet.json").write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(["list"])
    assert "carnet.json" in capsys.readouterr().out
    assert (isole / "carnet.json").read_text(encoding="utf-8") == "{"
    assert not (isole / "notebook.json").exists()


def _conflit_avec_paul(tmp_path):
    from superselection.carnet import Carnet

    app = nouvelle_app(tmp_path)
    app.memoriser("Bob", "rush")
    app.noter("Bob", "noob")
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "rush archers", maintenant="2026-11-21T20:00")
    paul.noter("Bob", "pro", maintenant="2026-11-21T20:00")
    paul.sauver(tmp_path / "paul.json")
    return app


@pytest.mark.parametrize(
    "ligne, reponses, note, trait",
    [
        ("", [""], "rush archers", "pro"),  # Entrée : la plus récente
        (" --mine", [""], "rush", "noob"),  # stratégie de départ donnée par l'option
        ("", ["c", "3", ""], "rush", "noob"),  # changer : toujours la mienne
        ("", ["c", "6", "", "f", "1"], "rush", "noob, pro"),  # un par un : trait puis note
        ("", ["x", "c", "9", "", ""], "rush archers", "pro"),  # réponses invalides redemandées
    ],
)
def test_import_confirme_et_laisse_changer_la_strategie(tmp_path, capsys, ligne, reponses, note, trait):
    app = _conflit_avec_paul(tmp_path)
    suite = iter(reponses)
    questions = []

    def demander(question, defaut, genre="texte"):
        questions.append(question)
        return next(suite)

    cli.executer(app, f"import {tmp_path / 'paul.json'}{ligne}", demander)
    sortie = capsys.readouterr().out
    assert "Import de Paul : 0 joueur(s) à ajouter, 2 version(s) nouvelle(s)" in sortie
    depart = "toujours la mienne" if ligne else "la plus récente gagne"
    assert questions[0].startswith(f"  Importer ({depart}) ? ")
    assert (app.note_actuelle("Bob"), app.trait_actuel("Bob")) == (note, trait)
    assert next(suite, None) is None  # toutes les réponses ont servi


def test_import_annule_par_n(tmp_path, capsys):
    app = _conflit_avec_paul(tmp_path)
    avant = app.chemin_carnet.read_text(encoding="utf-8")
    cli.executer(app, f"import {tmp_path / 'paul.json'}", lambda q, d, genre="texte": "n")
    assert "Import annulé" in capsys.readouterr().out
    assert app.chemin_carnet.read_text(encoding="utf-8") == avant


def test_import_sans_difference_demande_seulement_confirmation(tmp_path, capsys):
    from superselection.carnet import Carnet

    app = nouvelle_app(tmp_path)
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "rush", maintenant="2026-11-21T20:00")
    paul.sauver(tmp_path / "paul.json")
    questions = []

    def demander(question, defaut, genre="texte"):
        questions.append(question)
        return ""

    cli.executer(app, f"import {tmp_path / 'paul.json'}", demander)
    assert len(questions) == 1 and "Importer ?" in questions[0] and "changer" not in questions[0]
    assert app.note_actuelle("Bob") == "rush"


def test_import_option_inconnue(tmp_path, capsys):
    app = _conflit_avec_paul(tmp_path)
    cli.executer(app, f"import {tmp_path / 'paul.json'} --vite", lambda q, d, genre="texte": pytest.fail("pas de question"))
    assert "Option inconnue : --vite" in capsys.readouterr().out


def test_import_ctrl_c_pendant_les_questions_annule_tout(tmp_path, capsys):
    app = _conflit_avec_paul(tmp_path)
    avant = app.chemin_carnet.read_text(encoding="utf-8")
    reponses = iter(["c", "6", "1"])

    def demander(question, defaut, genre="texte"):
        try:
            return next(reponses)
        except StopIteration:
            raise KeyboardInterrupt

    cli.executer(app, f"import {tmp_path / 'paul.json'}", demander)
    assert "Annulé" in capsys.readouterr().out
    assert app.note_actuelle("Bob") == "rush"
    assert app.chemin_carnet.read_text(encoding="utf-8") == avant
