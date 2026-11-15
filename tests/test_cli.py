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
    carnet = isole / "carnet.json"
    carnet.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    sortie_texte = capsys.readouterr().out
    assert str(carnet) in sortie_texte
    assert "Traceback" not in sortie_texte
    assert carnet.read_text(encoding="utf-8") == "{"


def test_carnet_invalide_message_sans_traceback(isole, capsys):
    (isole / "carnet.json").write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    assert "illisible" in capsys.readouterr().out


def test_premier_lancement_sans_terminal(isole, capsys):
    with pytest.raises(SystemExit) as sortie:
        cli.main(["list"])
    assert sortie.value.code == 1
    assert "Premier lancement : lance « superselection » dans un terminal" in capsys.readouterr().out
    assert not (isole / "carnet.json").exists()


def test_premier_lancement_ctrl_c_sur_le_pseudo(isole, monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def interrompu(_invite=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrompu)
    cli.main([])  # sort proprement
    assert not (isole / "carnet.json").exists()


def test_exception_inattendue_ecrit_erreur_log(isole, monkeypatch, capsys):
    (isole / "carnet.json").write_text('{"auteur": "Antho", "joueurs": []}', encoding="utf-8")

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
    note = joueur.traits.get("Antho") if joueur else None
    return note.texte if note else None


@pytest.mark.parametrize("erreur", [KeyboardInterrupt, EOFError])
def test_ctrl_c_ou_ctrl_d_sur_le_trait_garde_tout(tmp_path, erreur):
    app = nouvelle_app(tmp_path)

    def demander(question, defaut):
        raise erreur

    assert cli.executer(app, "Bob", demander) is True
    assert app.carnet.trouver("Bob").rencontres == 1
    assert _trait(app, "Bob") is None


def test_ctrl_c_sur_le_trait_garde_le_trait_actuel(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")

    def demander(question, defaut):
        raise KeyboardInterrupt

    assert cli.executer(app, "Bob", demander) is True
    assert _trait(app, "Bob") == "noob"


def test_trait_saisi_est_enregistre(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "noob, pro")
    assert _trait(app, "Bob") == "noob, pro"


def test_tiret_efface_le_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "noob")
    cli.executer(app, "Bob", lambda q, d: "-")
    assert _trait(app, "Bob") is None


def test_reponse_vide_garde_le_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "noob")
    app.maintenant = lambda: "2026-11-15T21:00"
    cli.executer(app, "Bob", lambda q, d: "")
    assert _trait(app, "Bob") == "noob"
    assert app.carnet.trouver("Bob").rencontres == 2


def test_boucle_interactive_continue_si_l_enregistrement_echoue(isole, monkeypatch, capsys):
    (isole / "carnet.json").write_text('{"auteur": "Antho", "joueurs": []}', encoding="utf-8")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    lignes = iter(["Bob", "quit"])

    class FausseSession:
        def prompt(self, *args, **kwargs):
            return next(lignes)

    monkeypatch.setattr(cli, "_session", lambda app: (FausseSession(), None))

    def sauver_impossible(self, chemin):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(cli.Carnet, "sauver", sauver_impossible)
    cli.main([])
    sortie = capsys.readouterr().out
    assert "Impossible d'enregistrer le carnet" in sortie
    assert "À plus !" in sortie


def test_joueur_nomme_comme_une_commande_est_croise(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Show Me")
    app.maintenant = lambda: "2026-11-15T21:00"
    assert cli.executer(app, "show me", lambda q, d: "") is True
    assert app.carnet.trouver("Show Me").rencontres == 2


def test_update_sans_internet_reste_dans_l_outil(tmp_path, monkeypatch, capsys):
    def panne():
        raise OSError("pas d'internet")

    monkeypatch.setattr(cli, "fetch_pyproject", panne)
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "update", lambda q, d: "") is True
    sortie = capsys.readouterr().out
    assert "Impossible de vérifier la dernière version" in sortie
    assert "Déjà à jour" not in sortie


# --- delete / rename -----------------------------------------------------------


@pytest.mark.parametrize("reponse,reste", [("o", None), ("", "Bob"), ("n", "Bob")])
def test_delete_demande_confirmation(tmp_path, reponse, reste):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    questions = []

    def demander(question, defaut):
        questions.append(question)
        return reponse

    assert cli.executer(app, "delete bob", demander) is True
    assert len(questions) == 1
    assert (app.carnet.trouver("Bob") and "Bob") == reste


def test_delete_ctrl_c_annule(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")

    def demander(question, defaut):
        raise KeyboardInterrupt

    cli.executer(app, "delete Bob", demander)
    assert app.carnet.trouver("Bob") is not None


def test_edit_renomme_puis_note_sans_recompter(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Pizza")
    reponses = iter(["Pizza2", "noob", ""])  # nom, trait, note
    cli.executer(app, "edit Pizza", lambda q, d: next(reponses))
    assert app.carnet.trouver("Pizza") is None
    assert app.carnet.trouver("Pizza2").rencontres == 1
    assert _trait(app, "Pizza2") == "noob"


@pytest.mark.parametrize("reponse,reste", [("oui", 0), ("o", 2), ("", 2), ("non", 2)])
def test_reset_demande_confirmation(tmp_path, reponse, reste):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.croiser("Alice")
    cli.executer(app, "reset", lambda question, defaut: reponse)
    assert len(app.carnet.joueurs) == reste
    from superselection.carnet import Carnet

    assert len(Carnet.charger(app.chemin_carnet).joueurs) == reste
    assert app.carnet.auteur == "Antho"


def test_reset_ctrl_c_annule(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")

    def demander(question, defaut):
        raise KeyboardInterrupt

    cli.executer(app, "reset", demander)
    assert app.carnet.trouver("Bob") is not None


def test_reset_carnet_vide_ne_demande_rien(tmp_path, capsys):
    app = nouvelle_app(tmp_path)

    def demander(question, defaut):
        raise AssertionError("pas de question")

    cli.executer(app, "reset", demander)
    assert "déjà vide" in capsys.readouterr().out


def _repondre(**reponses):
    """demander() qui répond selon le mot-clé présent dans la question (Trait / Note)."""
    questions = []

    def demander(question, defaut):
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
    assert app.mon_memo("Bob") == "m'a insulté"
    assert len(demander.questions) == 2


def test_croiser_note_vide_ou_tiret(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", _repondre(note="x"))
    cli.executer(app, "Bob", _repondre(note=""))
    assert app.mon_memo("Bob") == "x"
    cli.executer(app, "Bob", _repondre(note="-"))
    assert app.mon_memo("Bob") == ""


def test_croiser_ctrl_c_sur_la_note_garde_tout(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("Bob", "ancienne")

    def demander(question, defaut):
        if "note" in question.casefold():
            raise KeyboardInterrupt
        return "noob"

    cli.executer(app, "Bob", demander)
    assert _trait(app, "Bob") == "noob"
    assert app.mon_memo("Bob") == "ancienne"


def test_top_commande_non_interactive(tmp_path, capsys):
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "top 2v2 unl", lambda q, d: "") is True
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

    def entree(question, defaut):
        vus.append(defaut)
        return defaut  # Entrée sur un champ pré-rempli

    cli.executer(app, "edit bob", entree)
    assert vus == ["Bob", "aggressive", "joue le soir"]
    bob = app.carnet.trouver("Bob")
    assert bob.rencontres == 1 and bob.derniere == "2026-11-15T20:00"
    assert _trait(app, "Bob") == "aggressive" and bob.memo == "joue le soir"


def test_edit_corrige_sur_place_et_vide_efface(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "aggressive")
    app.memoriser("Bob", "joue le soir")
    reponses = iter(["Bob", "aggressive, noob", ""])  # nom gardé, trait corrigé, note vidée
    cli.executer(app, "edit Bob", lambda q, d: next(reponses))
    assert _trait(app, "Bob") == "aggressive, noob"
    assert app.carnet.trouver("Bob").memo == ""


def test_edit_joueur_inconnu_ne_pose_aucune_question(tmp_path):
    app = nouvelle_app(tmp_path)
    assert cli.executer(app, "edit Zorglub", lambda q, d: pytest.fail("pas de question")) is True
    assert app.carnet.trouver("Zorglub") is None


def test_trait_hors_liste_est_refuse_et_signale(tmp_path, capsys):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "rush archers")
    sortie = capsys.readouterr().out
    assert "rush" in sortie and "Trait enregistré" not in sortie
    assert _trait(app, "Bob") is None


def test_traits_proposes_des_le_debut_sans_taper_de_lettre(tmp_path):
    from prompt_toolkit.document import Document

    _, completeur_trait = cli._session(nouvelle_app(tmp_path))
    propositions = [c.text for c in completeur_trait.get_completions(Document(""), None)]
    assert propositions == ["aggressive", "defence", "noob", "tryhard", "pro"]
    apres_virgule = [c.text for c in completeur_trait.get_completions(Document("noob, "), None)]
    assert "pro" in apres_virgule
