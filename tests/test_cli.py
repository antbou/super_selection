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


# --- executer : saisie du style ------------------------------------------------

from test_app import nouvelle_app


def _style(app, nom):
    joueur = app.carnet.trouver(nom)
    note = joueur.styles.get("Antho") if joueur else None
    return note.texte if note else None


@pytest.mark.parametrize("erreur", [KeyboardInterrupt, EOFError])
def test_ctrl_c_ou_ctrl_d_sur_le_style_garde_tout(tmp_path, erreur):
    app = nouvelle_app(tmp_path)

    def demander(question, defaut):
        raise erreur

    assert cli.executer(app, "Bob", demander) is True
    assert app.carnet.trouver("Bob").rencontres == 1
    assert _style(app, "Bob") is None


def test_ctrl_c_sur_le_style_garde_le_style_actuel(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "rush")

    def demander(question, defaut):
        raise KeyboardInterrupt

    assert cli.executer(app, "Bob", demander) is True
    assert _style(app, "Bob") == "rush"


def test_style_saisi_est_enregistre(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "rush archers")
    assert _style(app, "Bob") == "rush archers"


def test_tiret_efface_le_style(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "rush")
    cli.executer(app, "Bob", lambda q, d: "-")
    assert _style(app, "Bob") is None


def test_reponse_vide_garde_le_style(tmp_path):
    app = nouvelle_app(tmp_path)
    cli.executer(app, "Bob", lambda q, d: "rush")
    cli.executer(app, "Bob", lambda q, d: "")
    assert _style(app, "Bob") == "rush"
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
