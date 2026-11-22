import json

import pytest

from superselection import carnet as module_carnet
from superselection.carnet import Carnet, CarnetInvalide, Revision, migrer_ancien_fichier


def test_croiser_cree_puis_incremente():
    c = Carnet(auteur="Antho")
    j = c.croiser("Pizza", quand="2026-11-10")
    assert (j.rencontres, j.derniere) == (1, "2026-11-10")
    j = c.croiser("pizza", quand="2026-11-12")
    assert (j.nom, j.rencontres, j.derniere) == ("Pizza", 2, "2026-11-12")
    assert len(c.joueurs) == 1


def test_recents_du_plus_recent_au_plus_ancien():
    c = Carnet(auteur="Antho")
    c.croiser("A", quand="2026-11-01")
    c.croiser("B", quand="2026-11-05")
    c.croiser("C", quand="2026-11-03")
    assert [j.nom for j in c.recents()] == ["B", "C", "A"]


# --- trait et note communs, avec historique (ADR 0022) ---------------------------


def test_noter_ajoute_une_version_au_trait_commun():
    c = Carnet(auteur="Antho")
    c.noter("Pizza", "aggressive", maintenant="2026-11-10T20:00")
    c.noter("pizza", "aggressive, pro", maintenant="2026-11-11T20:00")
    pizza = c.trouver("Pizza")
    assert pizza.trait == "aggressive, pro"
    assert pizza.historique_trait == [
        Revision("aggressive", "Antho", "2026-11-10T20:00"),
        Revision("aggressive, pro", "Antho", "2026-11-11T20:00"),
    ]


def test_effacer_le_trait_garde_l_historique():
    c = Carnet(auteur="Antho")
    c.noter("Pizza", "noob", maintenant="2026-11-10T20:00")
    c.noter("Pizza", "", maintenant="2026-11-10T21:00")
    pizza = c.trouver("Pizza")
    assert pizza.trait == ""
    assert [r.texte for r in pizza.historique_trait] == ["noob", ""]


def test_meme_valeur_n_ajoute_pas_de_version():
    c = Carnet(auteur="Antho")
    c.noter("Pizza", "pro", maintenant="2026-11-10T20:00")
    c.noter("Pizza", "pro", maintenant="2026-11-11T20:00")
    c.memoriser("Pizza", "", maintenant="2026-11-11T20:00")  # rien à effacer
    assert len(c.trouver("Pizza").historique_trait) == 1
    assert c.trouver("Pizza").historique_note == []


def test_memoriser_nettoie_et_n_ajoute_pas_de_joueur_pour_rien():
    c = Carnet(auteur="Antho")
    c.memoriser("Pizza", "  m'a insulté\x07, rush à 3 min  ", maintenant="2026-11-10T20:00")
    assert c.trouver("pizza").note == "m'a insulté, rush à 3 min"
    c.memoriser("Bob", "", maintenant="2026-11-10T20:00")
    assert c.trouver("Bob") is None


def test_modification_locale_passe_devant_une_version_datee_du_futur():
    # horloge du pote en avance : ma modification doit quand même devenir la version actuelle
    c = Carnet(auteur="Antho")
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "de Paul", maintenant="2026-11-10T22:00")
    c.fusionner(paul)
    c.memoriser("Bob", "de moi", maintenant="2026-11-10T21:00")
    assert c.trouver("Bob").note == "de moi"


# --- fichier JSON (format 2, en anglais) -----------------------------------------


def test_sauver_puis_charger(tmp_path):
    chemin = tmp_path / "notebook.json"
    c = Carnet(auteur="Antho")
    c.croiser("妮蔻", quand="2026-11-10T19:00")
    c.noter("妮蔻", "defence", maintenant="2026-11-10T20:00")
    c.memoriser("妮蔻", "joue le soir", maintenant="2026-11-10T20:00")
    c.sauver(chemin)
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    assert brut == {
        "version": 2,
        "owner": "Antho",
        "players": [
            {
                "name": "妮蔻",
                "encountered_by": {"Antho": {"count": 1, "last": "2026-11-10T19:00"}},
                "trait_history": [{"text": "defence", "by": "Antho", "at": "2026-11-10T20:00"}],
                "note_history": [{"text": "joue le soir", "by": "Antho", "at": "2026-11-10T20:00"}],
            }
        ],
    }
    assert "妮蔻" in chemin.read_text(encoding="utf-8")
    relu = Carnet.charger(chemin)
    assert relu.auteur == "Antho"
    assert relu.trouver("妮蔻").trait == "defence"
    assert relu.trouver("妮蔻").note == "joue le soir"


def test_historiques_vides_absents_du_fichier():
    c = Carnet(auteur="Antho")
    c.croiser("Bob", quand="2026-11-10")
    assert c.vers_dict()["players"][0] == {"name": "Bob", "encountered_by": {"Antho": {"count": 1, "last": "2026-11-10"}}}


# --- migration depuis le format 1 (carnet.json, en français) ----------------------


ANCIEN = {
    "version": 1,
    "auteur": "Antho",
    "joueurs": [
        {
            "nom": "Pizza",
            "rencontres": 3,
            "derniere": "2026-11-10T19:00",
            "styles": {
                "Antho": {"texte": "aggressive", "maj": "2026-11-09T20:00"},
                "Kevin": {"texte": "pro", "maj": "2026-11-10T20:00"},
            },
            "memo": "rush à 3 min",
            "memo_maj": "2026-11-08T20:00",
            "notes": {"Léa": {"texte": "joue le soir", "maj": "2026-11-07T20:00"}},
        }
    ],
}


def test_format_1_converti_en_historiques_communs():
    c = Carnet.depuis_dict(ANCIEN)
    assert c.auteur == "Antho"
    pizza = c.trouver("Pizza")
    assert (pizza.rencontres, pizza.derniere) == (3, "2026-11-10T19:00")
    assert pizza.trait == "pro"  # la plus récente l'emporte
    assert pizza.historique_trait == [
        Revision("aggressive", "Antho", "2026-11-09T20:00"),
        Revision("pro", "Kevin", "2026-11-10T20:00"),
    ]
    assert pizza.note == "rush à 3 min"
    assert pizza.historique_note == [
        Revision("joue le soir", "Léa", "2026-11-07T20:00"),
        Revision("rush à 3 min", "Antho", "2026-11-08T20:00"),
    ]


def test_migrer_ancien_fichier(tmp_path):
    (tmp_path / "carnet.json").write_text(json.dumps(ANCIEN), encoding="utf-8")
    sauvegarde = migrer_ancien_fichier(tmp_path)
    assert sauvegarde == tmp_path / "carnet.v1.bak.json"
    assert not (tmp_path / "carnet.json").exists()
    assert json.loads(sauvegarde.read_text(encoding="utf-8")) == ANCIEN
    nouveau = Carnet.charger(tmp_path / "notebook.json")
    assert nouveau.trouver("Pizza").trait == "pro"


def test_migrer_ne_fait_rien_sans_ancien_fichier_ou_si_le_nouveau_existe(tmp_path):
    assert migrer_ancien_fichier(tmp_path) is None
    Carnet(auteur="Antho").sauver(tmp_path / "notebook.json")
    (tmp_path / "carnet.json").write_text(json.dumps(ANCIEN), encoding="utf-8")
    assert migrer_ancien_fichier(tmp_path) is None
    assert Carnet.charger(tmp_path / "notebook.json").joueurs == []


def test_migrer_ancien_fichier_illisible_ne_touche_a_rien(tmp_path):
    (tmp_path / "carnet.json").write_text("{", encoding="utf-8")
    with pytest.raises(CarnetInvalide):
        migrer_ancien_fichier(tmp_path)
    assert (tmp_path / "carnet.json").exists()
    assert not (tmp_path / "notebook.json").exists()


# --- fusion : la version la plus récente l'emporte, l'historique garde tout -------


def test_fusion_ajoute_les_joueurs_et_les_versions_du_pote():
    moi = Carnet(auteur="Antho")
    moi.croiser("Pizza", quand="2026-11-10")
    moi.noter("Pizza", "aggressive", maintenant="2026-11-10T20:00")

    pote = Carnet(auteur="Kevin")
    pote.croiser("pizza", quand="2026-11-11")
    pote.croiser("pizza", quand="2026-11-12")
    pote.noter("pizza", "pro", maintenant="2026-11-12T20:00")
    pote.croiser("Ram Pam", quand="2026-11-12")
    pote.memoriser("Ram Pam", "passif", maintenant="2026-11-12T21:00")
    pote.croiser("Bob", quand="2026-11-12")  # ni trait ni note : pas importé

    bilan = moi.fusionner(pote)

    assert (bilan.joueurs_ajoutes, bilan.versions_ajoutees, bilan.traits_maj, bilan.notes_maj) == (1, 2, 1, 1)
    pizza = moi.trouver("Pizza")
    assert pizza.rencontres == 1  # seules mes rencontres comptent
    assert pizza.trait == "pro"  # celle de Kevin est plus récente
    assert [r.auteur for r in pizza.historique_trait] == ["Antho", "Kevin"]
    ram = moi.trouver("ram pam")
    assert (ram.rencontres, ram.note) == (0, "passif")
    assert moi.trouver("Bob") is None


def test_version_importee_plus_ancienne_va_dans_l_historique_sans_gagner():
    moi = Carnet(auteur="Antho")
    moi.noter("Pizza", "aggressive", maintenant="2026-11-12T20:00")
    pote = Carnet(auteur="Kevin")
    pote.noter("Pizza", "noob", maintenant="2026-11-10T20:00")
    bilan = moi.fusionner(pote)
    assert (bilan.versions_ajoutees, bilan.traits_maj) == (1, 0)
    pizza = moi.trouver("Pizza")
    assert pizza.trait == "aggressive"
    assert [r.texte for r in pizza.historique_trait] == ["noob", "aggressive"]


def test_le_pote_modifie_ma_note_et_je_recupere_sa_version():
    moi = Carnet(auteur="Antho")
    moi.memoriser("Bob", "rush", maintenant="2026-11-10T20:00")
    paul = Carnet(auteur="Paul")
    paul.fusionner(moi)
    assert paul.trouver("Bob").note == "rush"  # Paul voit ma note comme la sienne
    paul.memoriser("Bob", "rush à 3 min", maintenant="2026-11-11T20:00")
    assert moi.fusionner(paul).notes_maj == 1
    bob = moi.trouver("Bob")
    assert bob.note == "rush à 3 min"
    assert [(r.texte, r.auteur) for r in bob.historique_note] == [("rush", "Antho"), ("rush à 3 min", "Paul")]


def test_un_effacement_plus_recent_se_propage():
    moi = Carnet(auteur="Antho")
    moi.noter("Bob", "noob", maintenant="2026-11-10T20:00")
    paul = Carnet(auteur="Paul")
    paul.fusionner(moi)
    paul.noter("Bob", "", maintenant="2026-11-11T20:00")
    moi.fusionner(paul)
    assert moi.trouver("Bob").trait == ""


def test_fusion_idempotente():
    moi = Carnet(auteur="Antho")
    moi.noter("Bob", "noob", maintenant="2026-11-10T20:00")
    paul = Carnet(auteur="Paul")
    paul.noter("Bob", "pro", maintenant="2026-11-11T20:00")
    moi.fusionner(paul)
    paul.fusionner(moi)
    bilan = moi.fusionner(paul)
    assert (bilan.joueurs_ajoutes, bilan.versions_ajoutees, bilan.traits_maj, bilan.notes_maj) == (0, 0, 0, 0)
    assert len(moi.trouver("Bob").historique_trait) == 2
    assert moi.trouver("Bob").historique_trait == paul.trouver("Bob").historique_trait


def test_fusion_d_un_ancien_carnet_format_1():
    moi = Carnet(auteur="Antho")
    moi.noter("Pizza", "noob", maintenant="2026-11-01T20:00")
    bilan = moi.fusionner(Carnet.depuis_dict(ANCIEN))
    assert moi.trouver("Pizza").trait == "pro"
    assert moi.trouver("Pizza").note == "rush à 3 min"
    assert bilan.versions_ajoutees == 4


# --- validation à la lecture ---------------------------------------------------


def _ancien(**joueur):
    return {"auteur": "Kevin", "joueurs": [{"nom": "Bob", **joueur}]}


def _nouveau(**joueur):
    return {"version": 2, "owner": "Kevin", "players": [{"name": "Bob", **joueur}]}


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
        _ancien(rencontres="a"),
        _ancien(rencontres=-1),
        _ancien(rencontres=True),
        _ancien(rencontres=1.5),
        _ancien(derniere=3),
        _ancien(derniere="hier"),
        _ancien(styles=[]),
        _ancien(styles={"Kevin": "rush"}),
        _ancien(styles={"Kevin": {"texte": 3}}),
        _ancien(styles={"Kevin": {"texte": "rush", "maj": 3}}),
        _ancien(memo=3),
        {"owner": 3, "players": []},
        {"owner": "Kevin", "players": {}},
        {"owner": "Kevin", "players": [{"name": ""}]},
        _nouveau(encountered_by=[]),
        _nouveau(encountered_by={"K": 3}),
        _nouveau(encountered_by={"K": {"count": -1}}),
        _nouveau(encountered_by={"K": {"count": True}}),
        _nouveau(encountered_by={"K": {"count": 1, "last": "hier"}}),
        _nouveau(trait_history={}),
        _nouveau(trait_history=["pro"]),
        _nouveau(note_history=[{"text": 3, "by": "K", "at": ""}]),
        _nouveau(note_history=[{"text": "x", "by": 3, "at": ""}]),
        _nouveau(note_history=[{"text": "x", "by": "K", "at": 3}]),
    ],
)
def test_depuis_dict_refuse_les_carnets_invalides(brut):
    with pytest.raises(CarnetInvalide):
        Carnet.depuis_dict(brut)


def test_message_d_erreur_situe_le_joueur():
    brut = {"owner": "K", "players": [{"name": "Al"}, {"name": "Bob"}, {"name": "Bob2", "trait_history": "a"}]}
    with pytest.raises(CarnetInvalide, match=r"joueur n°3 \(« Bob2 »\).*trait_history"):
        Carnet.depuis_dict(brut)


def test_depuis_dict_valeurs_par_defaut():
    c = Carnet.depuis_dict({"players": [{"name": "Bob", "trait_history": [{"text": "pro"}]}]})
    assert c.auteur == "?"
    assert c.trouver("Bob").historique_trait == [Revision("pro", "?", "")]
    assert c.trouver("Bob").derniere is None


def test_depuis_dict_nettoie_les_textes():
    brut = {
        "owner": " Ke\x1b[2Jvin ",
        "players": [
            {
                "name": " Bob\x07 ",
                "trait_history": [{"text": "ru\nsh ", "by": "K\x1bx", "at": ""}],
            }
        ],
    }
    c = Carnet.depuis_dict(brut)
    assert c.auteur == "Ke[2Jvin"
    assert c.trouver("Bob").historique_trait == [Revision("rush", "Kx", "")]


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


# --- rencontres des autres (encountered_by) ------------------------------------


def test_rencontres_du_pote_importees_a_son_nom_jamais_les_miennes():
    moi = Carnet(auteur="Antho")
    moi.croiser("Bob", quand="2026-11-10T20:00")
    paul = Carnet(auteur="Paul")
    paul.croiser("Bob", quand="2026-11-12T20:00")
    paul.noter("Bob", "pro", maintenant="2026-11-12T20:00")
    paul.trouver("Bob").autres_rencontres["antho"] = module_carnet.Rencontres(99, "2099-01-01")
    moi.fusionner(paul)
    bob = moi.trouver("Bob")
    assert (bob.rencontres, bob.derniere) == (1, "2026-11-10T20:00")
    assert bob.autres_rencontres == {"Paul": module_carnet.Rencontres(1, "2026-11-12T20:00")}


def test_rencontres_des_autres_gardent_la_plus_recente_et_survivent_au_fichier(tmp_path):
    moi = Carnet(auteur="Antho")
    moi.noter("Bob", "pro", maintenant="2026-11-10T20:00")
    for quand in ("2026-11-12T20:00", "2026-11-12T21:00"):
        paul = Carnet(auteur="Paul")
        paul.croiser("Bob", quand=quand)
        moi.fusionner(paul)
    moi.sauver(tmp_path / "n.json")
    bob = Carnet.charger(tmp_path / "n.json").trouver("Bob")
    assert bob.autres_rencontres["Paul"].derniere == "2026-11-12T21:00"
    assert bob.rencontres == 0


# --- conflits et choix à l'import ----------------------------------------------


def _deux_notes():
    moi = Carnet(auteur="Antho")
    moi.memoriser("Bob", "rush", maintenant="2026-11-07T20:00")
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "rush archers", maintenant="2026-11-21T20:00")
    return moi, paul


def test_conflit_quand_chacun_a_modifie_de_son_cote():
    moi, paul = _deux_notes()
    [conflit] = moi.conflits(paul)
    assert (conflit.nom, conflit.champ, conflit.mienne.texte, conflit.sienne.texte) == ("Bob", "note", "rush", "rush archers")


def test_pas_de_conflit_si_sa_version_est_deja_dans_mon_historique():
    moi = Carnet(auteur="Antho")
    moi.memoriser("Bob", "ancienne", maintenant="2026-11-07T20:00")
    paul = Carnet(auteur="Paul")
    paul.fusionner(moi)
    moi.memoriser("Bob", "nouvelle", maintenant="2026-11-08T20:00")
    assert moi.conflits(paul) == []


def test_pas_de_conflit_sans_version_chez_moi_ou_meme_valeur():
    moi = Carnet(auteur="Antho")
    moi.croiser("Bob", quand="2026-11-07")
    moi.noter("Bob", "pro", maintenant="2026-11-07T20:00")
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "x", maintenant="2026-11-08T20:00")
    paul.noter("Bob", "pro", maintenant="2026-11-08T20:00")
    assert moi.conflits(paul) == []


@pytest.mark.parametrize(
    "choix, attendu, ajoutee",
    [
        ("recente", "rush archers", False),
        ("mienne", "rush", True),
        ("sienne", "rush archers", False),
        ("fusion", "rush / rush archers", True),
    ],
)
def test_resoudre_un_conflit(choix, attendu, ajoutee):
    moi, paul = _deux_notes()
    [conflit] = moi.conflits(paul)
    moi.fusionner(paul)
    assert moi.resoudre(conflit, choix, maintenant="2026-11-22T10:00") is ajoutee
    assert moi.trouver("Bob").note == attendu


def test_choix_enregistre_gagne_aussi_chez_le_pote():
    moi, paul = _deux_notes()
    [conflit] = moi.conflits(paul)
    moi.fusionner(paul)
    moi.resoudre(conflit, "mienne", maintenant="2026-11-22T10:00")
    assert moi.trouver("Bob").version("note") == Revision("rush", "Antho", "2026-11-22T10:00")
    assert paul.conflits(moi) == []  # sa version est dans mon historique : pas de question chez lui
    paul.fusionner(moi)
    assert paul.trouver("Bob").note == "rush"


def test_sans_suppression_garde_ma_note_si_le_pote_l_a_effacee():
    moi = Carnet(auteur="Antho")
    moi.memoriser("Bob", "rush", maintenant="2026-11-07T20:00")
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "autre", maintenant="2026-11-08T20:00")
    paul.memoriser("Bob", "", maintenant="2026-11-21T20:00")
    [conflit] = moi.conflits(paul)
    moi.fusionner(paul)
    assert moi.trouver("Bob").note == ""
    assert moi.resoudre(conflit, "sans_suppression", maintenant="2026-11-22T10:00")
    assert moi.trouver("Bob").note == "rush"


def test_sans_suppression_ne_change_rien_si_ce_n_est_pas_une_suppression():
    moi, paul = _deux_notes()
    [conflit] = moi.conflits(paul)
    moi.fusionner(paul)
    assert not moi.resoudre(conflit, "sans_suppression", maintenant="2026-11-22T10:00")
    assert moi.trouver("Bob").note == "rush archers"


def test_fusion_de_deux_traits_reunit_les_mots_cles():
    assert module_carnet.reunir("trait", "aggressive, pro", "pro, noob") == "aggressive, pro, noob"
    assert module_carnet.reunir("note", "", "x") == "x"
    assert module_carnet.reunir("note", "x", "x") == "x"


def test_pas_de_conflit_si_le_pote_a_remplace_ma_version():
    moi = Carnet(auteur="Antho")
    moi.memoriser("Bob", "rush", maintenant="2026-11-07T20:00")
    paul = Carnet(auteur="Paul")
    paul.fusionner(moi)
    paul.memoriser("Bob", "rush à 3 min", maintenant="2026-11-08T20:00")
    assert moi.conflits(paul) == []
