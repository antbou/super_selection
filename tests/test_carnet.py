from superselection.carnet import Carnet


def test_croiser_cree_puis_incremente():
    c = Carnet(auteur="Antho")
    j = c.croiser("Pizza", quand="2026-11-10")
    assert (j.rencontres, j.derniere) == (1, "2026-11-10")
    j = c.croiser("pizza", quand="2026-11-12")
    assert (j.nom, j.rencontres, j.derniere) == ("Pizza", 2, "2026-11-12")
    assert len(c.joueurs) == 1


def test_noter_et_effacer_son_style():
    c = Carnet(auteur="Antho")
    c.croiser("Pizza", quand="2026-11-10")
    c.noter("Pizza", "agressif, rush archers", maintenant="2026-11-10T20:00")
    assert c.trouver("PIZZA").styles["Antho"].texte == "agressif, rush archers"
    c.noter("Pizza", "", maintenant="2026-11-10T21:00")
    assert "Antho" not in c.trouver("Pizza").styles


def test_recents_du_plus_recent_au_plus_ancien():
    c = Carnet(auteur="Antho")
    c.croiser("A", quand="2026-11-01")
    c.croiser("B", quand="2026-11-05")
    c.croiser("C", quand="2026-11-03")
    assert [j.nom for j in c.recents()] == ["B", "C", "A"]


def test_sauver_puis_charger(tmp_path):
    chemin = tmp_path / "carnet.json"
    c = Carnet(auteur="Antho")
    c.croiser("妮蔻", quand="2026-11-10")
    c.noter("妮蔻", "défensif", maintenant="2026-11-10T20:00")
    c.sauver(chemin)
    relu = Carnet.charger(chemin)
    assert relu.auteur == "Antho"
    assert relu.trouver("妮蔻").styles["Antho"].texte == "défensif"
    assert "妮蔻" in chemin.read_text(encoding="utf-8")


def test_fusion_ajoute_les_joueurs_et_notes_du_pote():
    moi = Carnet(auteur="Antho")
    moi.croiser("Pizza", quand="2026-11-10")
    moi.noter("Pizza", "agressif", maintenant="2026-11-10T20:00")

    pote = Carnet(auteur="Kevin")
    pote.croiser("pizza", quand="2026-11-11")
    pote.croiser("pizza", quand="2026-11-12")
    pote.noter("pizza", "spam cavalerie", maintenant="2026-11-12T20:00")
    pote.croiser("Ram Pam", quand="2026-11-12")
    pote.noter("Ram Pam", "passif", maintenant="2026-11-12T21:00")

    bilan = moi.fusionner(pote)

    assert (bilan.joueurs_ajoutes, bilan.notes_ajoutees, bilan.notes_maj) == (1, 2, 0)
    pizza = moi.trouver("Pizza")
    assert pizza.rencontres == 1  # seules mes rencontres comptent
    assert pizza.styles["Antho"].texte == "agressif"
    assert pizza.styles["Kevin"].texte == "spam cavalerie"
    ram = moi.trouver("ram pam")
    assert ram.rencontres == 0
    assert ram.styles["Kevin"].texte == "passif"


def test_fusion_ne_touche_jamais_mes_notes():
    moi = Carnet(auteur="Antho")
    moi.croiser("Pizza", quand="2026-11-10")
    moi.noter("Pizza", "agressif", maintenant="2026-11-10T20:00")

    pote = Carnet(auteur="Kevin")
    pote.croiser("Pizza", quand="2026-11-10")
    pote.noter("Pizza", "x", maintenant="2026-11-10T20:00")
    pote.trouver("Pizza").styles["Antho"] = pote.trouver("Pizza").styles["Kevin"].__class__(
        texte="falsifié", maj="2099-01-01T00:00"
    )

    moi.fusionner(pote)
    assert moi.trouver("Pizza").styles["Antho"].texte == "agressif"


def test_reimport_met_a_jour_seulement_si_plus_recent():
    moi = Carnet(auteur="Antho")
    v1 = Carnet(auteur="Kevin")
    v1.croiser("Pizza", quand="2026-11-10")
    v1.noter("Pizza", "passif", maintenant="2026-11-10T20:00")
    moi.fusionner(v1)

    v2 = Carnet(auteur="Kevin")
    v2.croiser("Pizza", quand="2026-11-12")
    v2.noter("Pizza", "en fait agressif", maintenant="2026-11-12T20:00")
    bilan = moi.fusionner(v2)
    assert bilan.notes_maj == 1
    assert moi.trouver("Pizza").styles["Kevin"].texte == "en fait agressif"

    bilan = moi.fusionner(v1)  # ancienne version : ignorée
    assert (bilan.notes_ajoutees, bilan.notes_maj) == (0, 0)
    assert moi.trouver("Pizza").styles["Kevin"].texte == "en fait agressif"


def test_fusion_ignore_les_joueurs_sans_note():
    moi = Carnet(auteur="Antho")
    pote = Carnet(auteur="Kevin")
    pote.croiser("Bob", quand="2026-11-12")
    bilan = moi.fusionner(pote)
    assert bilan.joueurs_ajoutes == 0
    assert moi.trouver("Bob") is None


# --- validation à la lecture ---------------------------------------------------

import pytest

from superselection.carnet import CarnetInvalide


def _joueur(**champs):
    return {"nom": "Bob", **champs}


def _carnet(**joueur):
    return {"auteur": "Kevin", "joueurs": [_joueur(**joueur)]}


@pytest.mark.parametrize(
    "brut",
    [
        [],
        "texte",
        {"joueurs": {}},
        {"auteur": 3, "joueurs": []},
        {"joueurs": ["Bob"]},
        {"joueurs": [{"nom": 3}]},
        {"joueurs": [{"nom": ""}]},
        {"joueurs": [{"nom": "\x1b\x07"}]},
        _carnet(rencontres="a"),
        _carnet(rencontres=-1),
        _carnet(rencontres=True),
        _carnet(rencontres=1.5),
        _carnet(derniere=3),
        _carnet(derniere="hier"),
        _carnet(styles=[]),
        _carnet(styles={"Kevin": "rush"}),
        _carnet(styles={"Kevin": {"texte": 3}}),
        _carnet(styles={"Kevin": {"texte": "rush", "maj": 3}}),
    ],
)
def test_depuis_dict_refuse_les_carnets_invalides(brut):
    with pytest.raises(CarnetInvalide):
        Carnet.depuis_dict(brut)


def test_message_d_erreur_situe_le_joueur():
    brut = {"joueurs": [{"nom": "Al"}, {"nom": "Bob"}, {"nom": "Bob2", "rencontres": "a"}]}
    with pytest.raises(CarnetInvalide, match=r"joueur n°3 \(« Bob2 »\).*rencontres"):
        Carnet.depuis_dict(brut)


def test_depuis_dict_valeurs_par_defaut():
    c = Carnet.depuis_dict({"joueurs": [{"nom": "Bob", "styles": {"K": {"texte": "rush"}}}]})
    assert c.auteur == "?"
    assert c.trouver("Bob").styles["K"].maj == ""
    assert c.trouver("Bob").derniere is None


def test_depuis_dict_nettoie_les_textes():
    brut = {
        "auteur": " Ke\x1b[2Jvin ",
        "joueurs": [
            {"nom": " Bob\x07 ", "derniere": "2026-11-15T10:00", "styles": {"K\x1bx": {"texte": "ru\nsh ", "maj": ""}}}
        ],
    }
    c = Carnet.depuis_dict(brut)
    assert c.auteur == "Ke[2Jvin"
    assert c.trouver("Bob").styles["Kx"].texte == "rush"


def test_charger_json_casse(tmp_path):
    chemin = tmp_path / "c.json"
    chemin.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        Carnet.charger(chemin)


def test_charger_fichier_binaire(tmp_path):
    chemin = tmp_path / "c.json"
    chemin.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(CarnetInvalide):
        Carnet.charger(chemin)


# --- enregistrement impossible -------------------------------------------------

from superselection import carnet as module_carnet


def test_sauver_reessaie_apres_un_permission_error(tmp_path, monkeypatch):
    vrai_replace = module_carnet.os.replace
    appels = []

    def replace(src, dst):
        appels.append(1)
        if len(appels) <= 2:
            raise PermissionError("verrouillé")
        vrai_replace(src, dst)

    monkeypatch.setattr(module_carnet.os, "replace", replace)
    monkeypatch.setattr(module_carnet.time, "sleep", lambda s: None)
    chemin = tmp_path / "c.json"
    Carnet(auteur="Antho").sauver(chemin)
    assert len(appels) == 3
    assert Carnet.charger(chemin).auteur == "Antho"


def test_sauver_abandonne_et_nettoie_le_tmp(tmp_path, monkeypatch):
    def replace(src, dst):
        raise PermissionError("verrouillé")

    monkeypatch.setattr(module_carnet.os, "replace", replace)
    monkeypatch.setattr(module_carnet.time, "sleep", lambda s: None)
    chemin = tmp_path / "c.json"
    with pytest.raises(PermissionError):
        Carnet(auteur="Antho").sauver(chemin)
    assert not (tmp_path / "c.json.tmp").exists()


def test_memo_enregistre_efface_et_survit_au_fichier(tmp_path):
    c = Carnet(auteur="Antho")
    c.memoriser("Pizza", "  m'a insulté, rush à 3 min  ")
    assert c.trouver("pizza").memo == "m'a insulté, rush à 3 min"
    c.sauver(tmp_path / "c.json")
    assert Carnet.charger(tmp_path / "c.json").trouver("Pizza").memo == "m'a insulté, rush à 3 min"
    c.memoriser("Pizza", "")
    assert c.trouver("Pizza").memo == ""
    assert "memo" not in c.vers_dict()["joueurs"][0]


def test_memo_jamais_exporte_ni_fusionne(tmp_path):
    c = Carnet(auteur="Antho")
    c.memoriser("Pizza", "privé")
    c.sauver(tmp_path / "export.json", avec_memos=False)
    assert "privé" not in (tmp_path / "export.json").read_text(encoding="utf-8")

    pote = Carnet(auteur="Kevin")
    pote.noter("Pizza", "rush", maintenant="2026-11-15T20:00")
    pote.trouver("Pizza").memo = "memo du pote"
    c.fusionner(pote)
    assert c.trouver("Pizza").memo == "privé"
