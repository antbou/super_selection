from superselection.app import App, analyser
from superselection.carnet import Carnet
from superselection.classement import Classement

TOP_1V1 = [{"name": "[IMP] Pizza", "rating": 872}, {"name": "Unloukee", "rating": 800}]
TOP_2V2 = [{"name": "Unloukee", "rating": 600}]


def nouvelle_app(tmp_path, classement=True):
    c = (
        Classement(saison=29, lignes={"1v1": TOP_1V1, "2v2": TOP_2V2}, recupere_le="")
        if classement
        else None
    )
    return App(
        carnet=Carnet(auteur="Antho"),
        chemin_carnet=tmp_path / "carnet.json",
        classement=c,
        aujourd_hui=lambda: "2026-11-15",
        maintenant=lambda: "2026-11-15T20:00",
    )


def test_analyser_commandes():
    assert analyser("list") == ("list", "")
    assert analyser("  show  [IMP] Pizza ") == ("show", "[IMP] Pizza")
    assert analyser('import "C:\\Users\\moi\\kevin.json"') == ("import", "C:\\Users\\moi\\kevin.json")
    assert analyser("Q") == ("quit", "")
    assert analyser("HELP") == ("help", "")
    assert analyser("refresh") == ("refresh", "")
    assert analyser("update") == ("update", "")
    assert analyser("version") == ("version", "")
    assert analyser("[imp] pizza") == ("croiser", "[imp] pizza")
    assert analyser("player list") == ("croiser", "list")
    assert analyser("") == ("rien", "")


def test_croiser_un_joueur_du_top(tmp_path):
    app = nouvelle_app(tmp_path)
    texte = app.croiser("[imp] pizza")
    assert "[IMP] Pizza" in texte
    assert "1v1 : #1 (872 pts)" in texte
    assert "2v2 : hors top 100" in texte
    assert "Première rencontre" in texte
    assert app.carnet.trouver("[IMP] Pizza").rencontres == 1
    assert (tmp_path / "carnet.json").exists()


def test_croiser_deux_fois_affiche_le_compteur_et_le_style(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "rush")
    texte = app.croiser("bob")
    assert "1v1 : hors top 100" in texte
    assert "Croisé 2 fois" in texte
    assert "Style (toi) : rush" in texte


def test_voir_ne_compte_pas_de_rencontre(tmp_path):
    app = nouvelle_app(tmp_path)
    texte = app.voir("Unloukee")
    assert "jamais croisé" in texte.lower()
    assert app.carnet.trouver("Unloukee") is None


def test_sans_classement(tmp_path):
    app = nouvelle_app(tmp_path, classement=False)
    assert "classement indisponible" in app.croiser("Bob")


def test_liste(tmp_path):
    app = nouvelle_app(tmp_path)
    assert "Aucun joueur" in app.liste()
    app.croiser("Bob")
    app.noter("Bob", "rush")
    assert "Bob" in app.liste() and "rush" in app.liste()


def test_export_puis_import_chez_le_pote(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "rush")
    fichier = tmp_path / "antho.json"
    assert "exporté" in app.exporter(str(fichier))

    pote = App(
        carnet=Carnet(auteur="Kevin"),
        chemin_carnet=tmp_path / "kevin_carnet.json",
        classement=None,
        aujourd_hui=lambda: "2026-11-15",
        maintenant=lambda: "2026-11-15T21:00",
    )
    texte = pote.importer(str(fichier))
    assert "1 joueur(s) ajouté(s)" in texte
    assert pote.carnet.trouver("Bob").styles["Antho"].texte == "rush"


def test_import_fichier_absent(tmp_path):
    app = nouvelle_app(tmp_path)
    assert "introuvable" in app.importer(str(tmp_path / "nope.json"))


def test_noms_pour_autocompletion(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    assert set(app.noms()) == {"[IMP] Pizza", "Unloukee", "Bob"}


def test_voir_apres_une_rencontre(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    assert "Croisé 1 fois — dernière fois le 15/11/2026" in app.voir("bob")


def test_fiche_et_liste_affichent_les_emojis(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "aggressive, noob")
    assert "Style (toi) : 🔥 aggressive, 🐣 noob" in app.voir("Bob")
    assert "🔥 aggressive" in app.liste()
    assert app.carnet.trouver("Bob").styles["Antho"].texte == "aggressive, noob"  # stocké sans emoji


def test_analyser_styles():
    assert analyser("styles") == ("styles", "")


def test_import_fichier_qui_n_est_pas_un_carnet(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    avant = (tmp_path / "carnet.json").read_text(encoding="utf-8")
    for contenu in ("[]", "{", '{"joueurs": [{"nom": "X", "rencontres": "a"}]}'):
        fichier = tmp_path / "x.json"
        fichier.write_text(contenu, encoding="utf-8")
        texte = app.importer(str(fichier))
        assert "n'est pas un carnet superselection" in texte
        assert str(fichier) in texte
    assert (tmp_path / "carnet.json").read_text(encoding="utf-8") == avant
    assert [j.nom for j in app.carnet.joueurs] == ["Bob"]


def test_export_impossible_donne_un_message(tmp_path):
    app = nouvelle_app(tmp_path)
    fichier = tmp_path / "fichier"
    fichier.write_text("x", encoding="utf-8")
    texte = app.exporter(str(fichier / "sous" / "antho.json"))
    assert "Impossible d'écrire" in texte


def test_analyser_nom_connu_qui_ressemble_a_une_commande():
    connus = ["Show Me", "Q"]
    assert analyser("show me", connus) == ("croiser", "show me")
    assert analyser("q", connus) == ("croiser", "q")
    assert analyser("show Bob", connus) == ("show", "Bob")
    assert analyser("player list", connus) == ("croiser", "list")
    assert analyser("Q") == ("quit", "")


def test_fiche_d_un_homonyme_montre_les_deux_rangs(tmp_path):
    app = nouvelle_app(tmp_path)
    app.classement.lignes["1v1"] = [
        {"name": "Marmelaaada", "rating": 758},
        {"name": "Autre", "rating": 700},
        {"name": "Marmelaaada", "rating": 403},
    ]
    texte = app.voir("Marmelaaada")
    assert "1v1 : #1 (758 pts) ou #3 (403 pts) — 2 joueurs portent ce nom" in texte
