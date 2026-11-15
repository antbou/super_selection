from superselection import version
from superselection.version import est_plus_recente, etat_version, lire_version_publiee, nouvelle_version

PYPROJECT = '[project]\nname = "superselection"\nversion = "0.3.0"\n'


def test_comparer_les_versions():
    assert est_plus_recente("0.2.0", "0.1.0")
    assert est_plus_recente("0.10.0", "0.9.0")  # numérique, pas alphabétique
    assert not est_plus_recente("0.1.0", "0.1.0")
    assert not est_plus_recente("0.1.0", "0.2.0")


def test_lire_version_publiee():
    assert lire_version_publiee(lambda: PYPROJECT) == "0.3.0"


def test_lire_version_publiee_sans_reseau_renvoie_none():
    def panne():
        raise OSError("pas d'internet")

    assert lire_version_publiee(panne) is None
    assert lire_version_publiee(lambda: "rien d'utile") is None


def test_nouvelle_version():
    assert nouvelle_version("0.2.0", lambda: PYPROJECT) == "0.3.0"
    assert nouvelle_version("0.3.0", lambda: PYPROJECT) is None
    assert nouvelle_version("0.4.0", lambda: PYPROJECT) is None


def test_etat_version_les_trois_cas():
    def panne():
        raise OSError("pas d'internet")

    assert etat_version("0.2.0", panne) == ("injoignable", None)
    assert etat_version("0.3.0", lambda: PYPROJECT) == ("a_jour", "0.3.0")
    assert etat_version("0.2.0", lambda: PYPROJECT) == ("nouvelle", "0.3.0")


def test_mise_a_jour_uv_introuvable(monkeypatch):
    monkeypatch.setattr(version.os, "name", "posix")
    monkeypatch.setattr(version.shutil, "which", lambda _: None)
    reussi, message = version.lancer_mise_a_jour()
    assert reussi is False and "uv introuvable" in message


def test_mise_a_jour_uv_echoue(monkeypatch):
    class Resultat:
        returncode = 1

    monkeypatch.setattr(version.os, "name", "posix")
    monkeypatch.setattr(version.shutil, "which", lambda _: "/usr/bin/uv")
    monkeypatch.setattr(version.subprocess, "run", lambda *a, **k: Resultat())
    reussi, message = version.lancer_mise_a_jour()
    assert reussi is False and "a échoué" in message


def test_mise_a_jour_uv_reussit(monkeypatch):
    class Resultat:
        returncode = 0

    monkeypatch.setattr(version.os, "name", "posix")
    monkeypatch.setattr(version.shutil, "which", lambda _: "/usr/bin/uv")
    monkeypatch.setattr(version.subprocess, "run", lambda *a, **k: Resultat())
    assert version.lancer_mise_a_jour()[0] is True


def test_mise_a_jour_oserror_donne_un_echec_lisible(monkeypatch):
    def casse(*a, **k):
        raise OSError("introuvable")

    monkeypatch.setattr(version.os, "name", "posix")
    monkeypatch.setattr(version.shutil, "which", lambda _: "/usr/bin/uv")
    monkeypatch.setattr(version.subprocess, "run", casse)
    reussi, message = version.lancer_mise_a_jour()
    assert reussi is False and message.startswith("Impossible de lancer la mise à jour")


def test_mise_a_jour_windows_forme_de_la_commande(monkeypatch):
    lances = []
    monkeypatch.setattr(version.os, "name", "nt")
    monkeypatch.setattr(version.subprocess, "CREATE_NEW_CONSOLE", 16, raising=False)
    monkeypatch.setattr(version.subprocess, "Popen", lambda args, **k: lances.append(args))
    assert version.lancer_mise_a_jour()[0] is True
    commande = lances[0][-1]
    assert version.INSTALL_PS1 in commande
    assert "USERPROFILE" in commande and "Test-Path" in commande and commande.rstrip().endswith("superselection }")


def test_mise_a_jour_windows_powershell_introuvable(monkeypatch):
    def casse(*a, **k):
        raise FileNotFoundError("powershell")

    monkeypatch.setattr(version.os, "name", "nt")
    monkeypatch.setattr(version.subprocess, "CREATE_NEW_CONSOLE", 16, raising=False)
    monkeypatch.setattr(version.subprocess, "Popen", casse)
    reussi, message = version.lancer_mise_a_jour()
    assert reussi is False and "Impossible de lancer la mise à jour" in message
