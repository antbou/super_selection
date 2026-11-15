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
