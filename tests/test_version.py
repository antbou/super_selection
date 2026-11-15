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
