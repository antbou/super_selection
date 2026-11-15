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
    app.maintenant = lambda: "2026-11-15T21:00"  # plus de 30 minutes après
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


# --- F2 : pas de rencontre en double -------------------------------------------


def test_retaper_un_nom_peu_apres_ne_recompte_pas(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.maintenant = lambda: "2026-11-15T20:29:59"
    texte = app.croiser("Bob")
    assert app.carnet.trouver("Bob").rencontres == 1
    assert app.carnet.trouver("Bob").derniere == "2026-11-15T20:00"
    assert "déjà comptée" in texte
    assert "Première rencontre" not in texte


def test_apres_30_minutes_on_recompte(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.maintenant = lambda: "2026-11-15T20:30:00"
    texte = app.croiser("Bob")
    assert app.carnet.trouver("Bob").rencontres == 2
    assert "déjà comptée" not in texte


def test_ancien_carnet_avec_date_seule_recompte(tmp_path):
    app = nouvelle_app(tmp_path)
    app.carnet.croiser("Bob", quand="2026-11-15")
    app.croiser("Bob")
    assert app.carnet.trouver("Bob").rencontres == 2


# --- F1 : suppression, renommage, nouveau joueur -------------------------------


def test_nouveau_joueur_propose_des_noms_proches(tmp_path):
    app = nouvelle_app(tmp_path)
    texte = app.croiser("Pizza")
    assert "Nouveau joueur." in texte
    assert "Noms proches : [IMP] Pizza" in texte
    assert app.carnet.trouver("Pizza") is not None  # on suggère, on ne fusionne pas


def test_pas_de_signal_pour_un_joueur_connu(tmp_path):
    app = nouvelle_app(tmp_path)
    assert "Nouveau joueur" not in app.croiser("unloukee")  # dans le top 100
    app.croiser("Bob")
    app.maintenant = lambda: "2026-11-15T22:00"
    assert "Nouveau joueur" not in app.croiser("bob")  # déjà dans le carnet


def test_nouveau_joueur_sans_nom_proche(tmp_path):
    texte = nouvelle_app(tmp_path).croiser("Zzz")
    assert "Nouveau joueur." in texte and "Noms proches" not in texte


def test_supprimer(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    assert "retiré" in app.supprimer("BOB")
    assert app.carnet.trouver("Bob") is None
    assert "Bob" not in (tmp_path / "carnet.json").read_text(encoding="utf-8")
    assert "n'est pas dans ton carnet" in app.supprimer("Bob")


def test_renommer_garde_rencontres_et_styles(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Pizza")
    app.noter("Pizza", "rush")
    assert "renommé" in app.renommer("pizza > [IMP] Pizza")
    assert app.carnet.trouver("Pizza") is None
    joueur = app.carnet.trouver("[IMP] Pizza")
    assert (joueur.nom, joueur.rencontres, joueur.styles["Antho"].texte) == ("[IMP] Pizza", 1, "rush")
    assert "[IMP] Pizza" in (tmp_path / "carnet.json").read_text(encoding="utf-8")


def test_renommer_refuse_les_cas_invalides(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.croiser("Alice")
    assert "existe déjà" in app.renommer("Bob > alice")
    assert "n'est pas dans ton carnet" in app.renommer("Zed > Zoe")
    assert "ex : rename" in app.renommer("Bob")
    assert "ex : rename" in app.renommer("Bob > ")
    assert app.carnet.trouver("Bob") is not None


def test_renommer_juste_la_casse(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("bob")
    assert "renommé" in app.renommer("bob > Bob")
    assert app.carnet.trouver("bob").nom == "Bob"


def test_analyser_delete_rename():
    assert analyser("delete Bob") == ("delete", "Bob")
    assert analyser("rename a > b") == ("rename", "a > b")
