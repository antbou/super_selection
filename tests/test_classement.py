import json
from pathlib import Path

import pytest

from superselection.classement import (
    Classement,
    ErreurClassement,
    charger_classement,
    derniere_saison,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "top1001v1_s29.json").read_text(encoding="utf-8")
)["data"]


def faux_fetch(saisons: dict[int, list[dict]], appels: list | None = None):
    def fetch(mode: str, saison: int) -> list[dict]:
        if appels is not None:
            appels.append((mode, saison))
        return saisons.get(saison, []) if mode == "1v1" else saisons.get(saison, [])[:2]

    return fetch


def test_rang_ignore_la_casse():
    c = Classement(saison=29, lignes={"1v1": FIXTURE, "2v2": []}, recupere_le="2026-11-15T10:00")
    rang = c.rang("stoneageruler", "1v1")
    assert (rang.position, rang.points) == (2, 710)
    assert c.rang("stoneageruler", "2v2") is None


def test_rang_inconnu():
    c = Classement(saison=29, lignes={"1v1": FIXTURE, "2v2": []}, recupere_le="")
    assert c.rang("Personne", "1v1") is None


def test_nom_officiel_retrouve_la_casse_exacte():
    c = Classement(saison=29, lignes={"1v1": FIXTURE, "2v2": []}, recupere_le="")
    assert c.nom_officiel("MARMELAAADA") == "Marmelaaada"
    assert c.nom_officiel("inconnu") is None


def test_derniere_saison_sans_point_de_depart():
    saisons = {s: FIXTURE for s in range(1, 30)}
    assert derniere_saison(faux_fetch(saisons)) == 29


def test_derniere_saison_depuis_le_cache_avance_si_nouvelle_saison():
    saisons = {s: FIXTURE for s in range(1, 31)}
    appels = []
    assert derniere_saison(faux_fetch(saisons, appels), depuis=29) == 30
    assert len(appels) <= 3


def test_derniere_saison_aucune_saison():
    with pytest.raises(ErreurClassement):
        derniere_saison(faux_fetch({}))


def test_charger_met_en_cache(tmp_path):
    cache = tmp_path / "classement.json"
    saisons = {s: FIXTURE for s in range(1, 30)}
    c, message = charger_classement(cache, faux_fetch(saisons), maintenant="2026-11-15T10:00")
    assert c.saison == 29
    assert len(c.lignes["2v2"]) == 2
    assert message is None
    assert cache.exists()


def test_charger_hors_ligne_utilise_le_cache(tmp_path):
    cache = tmp_path / "classement.json"
    saisons = {s: FIXTURE for s in range(1, 30)}
    charger_classement(cache, faux_fetch(saisons), maintenant="2026-11-14T09:00")

    def panne(mode, saison):
        raise OSError("pas de réseau")

    c, message = charger_classement(cache, panne, maintenant="2026-11-15T10:00")
    assert c.saison == 29
    assert "hors ligne" in message


def test_charger_hors_ligne_sans_cache(tmp_path):
    def panne(mode, saison):
        raise OSError("pas de réseau")

    c, message = charger_classement(tmp_path / "absent.json", panne, maintenant="")
    assert c is None
    assert "indisponible" in message


def test_rangs_rend_tous_les_homonymes():
    lignes = [
        {"name": "Marmelaaada", "rating": 758},
        {"name": "Autre", "rating": 700},
        {"name": "marmelaaada", "rating": 403},
    ]
    c = Classement(saison=29, lignes={"1v1": lignes, "2v2": []}, recupere_le="")
    assert [(r.position, r.points) for r in c.rangs("MARMELAAADA", "1v1")] == [(1, 758), (3, 403)]
    assert c.rang("marmelaaada", "1v1").position == 1
    assert c.rangs("Personne", "1v1") == []


# --- lecture de la réponse et du cache ----------------------------------------

from superselection.classement import _lire_cache, lire_reponse


def test_lire_reponse_valide():
    corps = {"error": 0, "data": [{"name": "Pizza", "rating": 872}]}
    assert lire_reponse(corps) == [{"name": "Pizza", "rating": 872}]


@pytest.mark.parametrize(
    "corps",
    [[], "x", {"error": 1, "description": "boum", "data": []}, {"error": 0, "data": {}}, {"error": 0}],
)
def test_lire_reponse_refuse(corps):
    with pytest.raises(ErreurClassement):
        lire_reponse(corps)


def test_lire_reponse_ignore_les_lignes_mal_formees_et_nettoie():
    corps = {
        "error": 0,
        "data": [
            "x",
            {"name": "", "rating": 1},
            {"name": 3, "rating": 1},
            {"name": "Sans points"},
            {"name": "Bool", "rating": True},
            {"name": "Bon\x1b[2J", "rating": 5},
        ],
    }
    assert lire_reponse(corps) == [{"name": "Bon[2J", "rating": 5}]


def test_cache_impossible_a_ecrire_n_empeche_pas_le_classement(tmp_path):
    fichier = tmp_path / "fichier"
    fichier.write_text("x", encoding="utf-8")
    saisons = {s: FIXTURE for s in range(1, 30)}
    c, message = charger_classement(fichier / "c.json", faux_fetch(saisons), maintenant="")
    assert c.saison == 29
    assert message is None


def test_cache_de_mauvaise_forme_est_ignore(tmp_path):
    cache = tmp_path / "c.json"
    for contenu in ("[]", '{"saison": 29, "lignes": [], "recupere_le": ""}', '{"saison": "x"}',
                    '{"saison": 29, "lignes": {"1v1": [3]}, "recupere_le": ""}'):
        cache.write_text(contenu, encoding="utf-8")
        assert _lire_cache(cache) is None
