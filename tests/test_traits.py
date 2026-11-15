from superselection.traits import TAGS, decorer, tags_commencant_par, valider


def test_decorer_ajoute_l_emoji_devant_chaque_mot_connu():
    assert decorer("aggressive, tryhard, rush archers") == "🔥 aggressive, 😤 tryhard, rush archers"
    assert decorer("pro, defence") == "👑 pro, 🛡️ defence"


def test_decorer_accepte_les_fautes_et_variantes():
    assert decorer("aggresive") == "🔥 aggresive"
    assert decorer("Defense") == "🛡️ Defense"
    assert decorer("defence") == "🛡️ defence"
    assert decorer("NOOB") == "🐣 NOOB"
    assert decorer("défense") == "🛡️ défense"


def test_decorer_laisse_le_reste_intact():
    assert decorer("joue bizarre") == "joue bizarre"
    assert decorer("") == ""


def test_decorer_ne_coupe_pas_les_mots():
    assert decorer("prochain") == "prochain"  # contient « pro » mais n'est pas « pro »


def test_tags_commencant_par():
    assert [t.nom for t in tags_commencant_par("ag")] == ["aggressive"]
    assert [t.nom for t in TAGS] == ["aggressive", "defence", "noob", "tryhard", "pro"]
    assert [t.nom for t in tags_commencant_par("")] == [t.nom for t in TAGS]


def test_valider_normalise_les_variantes_et_dedoublonne():
    assert valider("Agressif, defense, NOOB, aggro") == ("aggressive, defence, noob", [])
    assert valider("pro tryhard") == ("pro, tryhard", [])
    assert valider("") == ("", [])


def test_valider_signale_les_mots_hors_liste():
    assert valider("aggressive, rush archers") == ("aggressive", ["rush", "archers"])
    assert valider("rush") == ("", ["rush"])
