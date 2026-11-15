from superselection.couleurs import peindre, sans_couleur

from test_app import nouvelle_app


def test_peindre_entoure_de_codes_ansi_et_se_retire():
    texte = peindre("Pizza", "nom")
    assert texte.startswith("\x1b[") and texte.endswith("\x1b[0m")
    assert sans_couleur(texte) == "Pizza"


def test_peindre_inactif_ne_change_rien():
    assert peindre("Pizza", "nom", actif=False) == "Pizza"


def test_fiche_en_couleur_meme_texte_que_sans_couleur(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Unloukee")
    app.noter("Unloukee", "aggressive")
    sans = app.voir("Unloukee")
    app.couleur = True
    avec = app.voir("Unloukee")
    assert "\x1b[" not in sans
    assert "\x1b[" in avec
    assert sans_couleur(avec) == sans
    app.couleur = True
    liste_couleur = app.liste()
    app.couleur = False
    assert sans_couleur(liste_couleur) == app.liste()


def test_homonymes_meme_texte_avec_et_sans_couleur(tmp_path):
    app = nouvelle_app(tmp_path)
    app.classement.lignes["1v1"] = [
        {"name": "Marmelaaada", "rating": 758},
        {"name": "Marmelaaada", "rating": 403},
    ]
    sans = app.voir("Marmelaaada")
    app.couleur = True
    avec = app.voir("Marmelaaada")
    assert "\x1b[" in avec
    assert sans_couleur(avec) == sans
    assert "2 joueurs portent ce nom" in sans
