import pytest

from superselection.couleurs import sans_couleur
from superselection.app import App, analyser
from superselection.carnet import Carnet
from superselection.classement import Classement

TOP_1V1 = [{"name": "[IMP] Pizza", "rating": 872}, {"name": "Unloukee", "rating": 800}]
TOP_2V2 = [{"name": "Unloukee", "rating": 600}]


def nouvelle_app(tmp_path, classement=True, anciennes=None):
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
        saison_passee=(lambda n: anciennes.get(n)) if anciennes is not None else None,
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


def test_croiser_deux_fois_affiche_le_compteur_et_le_trait(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")
    app.maintenant = lambda: "2026-11-15T21:00"  # plus de 30 minutes après
    texte = app.croiser("bob")
    assert "1v1 : hors top 100" in texte
    assert "Croisé 2 fois" in texte
    assert "Trait : 🐣 noob  (Antho, 15/11/2026)" in texte


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
    app.noter("Bob", "noob")
    assert "Bob" in app.liste() and "noob" in app.liste()


def test_liste_en_tete_tri_alphabetique_et_note_tronquee(tmp_path):
    app = nouvelle_app(tmp_path)
    for nom in ("妮蔻", "zed", "Alice"):
        app.croiser(nom)
    app.memoriser("zed", "x" * 80)
    lignes = sans_couleur(app.liste()).splitlines()
    assert lignes[0] == "3 joueur(s) :"
    assert lignes[1].split() == ["Nom", "Traits", "Note", "Vu"]
    assert lignes[2].endswith("1x, 15/11/2026")
    assert [l.split()[0] for l in lignes[2:]] == ["Alice", "zed", "妮蔻"]
    assert "x" * 49 + "…" in lignes[3] and "x" * 50 not in lignes[3]
    assert "1x, 15/11/2026" in lignes[2] and "Antho" not in lignes[2]


def test_liste_sans_auteurs_mais_show_les_garde(tmp_path):
    app = nouvelle_app(tmp_path)
    autre = Carnet(auteur="Kevin")
    autre.croiser("Bob", quand="2026-11-10T10:00")
    autre.noter("Bob", "noob", maintenant="2026-11-10T10:00")
    autre.sauver(tmp_path / "kevin.json")
    app.importer(str(tmp_path / "kevin.json"))
    app.croiser("Bob")
    app.noter("Bob", "pro")
    liste = sans_couleur(app.liste())
    assert "jamais croisé" not in liste.lower()
    assert "Kevin" not in liste and "Antho" not in liste and "Croisé par" not in liste
    assert "👑 pro" in liste.splitlines()[2] and "noob" not in liste  # version actuelle seulement
    fiche = sans_couleur(app.voir("Bob"))
    assert "Trait : 👑 pro  (Antho, 15/11/2026)" in fiche
    assert "10/11/2026  Kevin  trait : 🐣 noob" in fiche  # l'ancienne version, dans l'historique


def test_show_joueur_importe_donne_l_auteur(tmp_path):
    app = nouvelle_app(tmp_path)
    autre = Carnet(auteur="Kevin")
    autre.croiser("Bob", quand="2026-11-10T10:00")
    autre.noter("Bob", "noob", maintenant="2026-11-10T10:00")
    autre.sauver(tmp_path / "kevin.json")
    app.importer(str(tmp_path / "kevin.json"))
    fiche = sans_couleur(app.voir("Bob"))
    assert "Jamais croisé" not in fiche and "Croisé par Kevin" in fiche


def test_liste_vu_aligne_a_droite_malgre_les_emojis(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "defence, pro")
    app.croiser("Al")
    lignes = sans_couleur(app.liste()).splitlines()
    from superselection.texte import largeur
    assert len({largeur(l) for l in lignes[2:]}) == 1  # même rencontre : même largeur totale


def test_export_puis_import_chez_le_pote(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")
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
    assert "1 version(s) ajoutée(s) à l'historique, 1 trait(s) et 0 note(s) changé(s)" in texte
    assert "la version la plus récente l'emporte" in texte and "conflit" not in texte
    assert pote.trait_actuel("Bob") == "noob"  # trait commun : Kevin peut le modifier


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
    assert "Trait : 🔥 aggressive, 🐣 noob" in app.voir("Bob")
    assert "🔥 aggressive" in app.liste()
    assert app.carnet.trouver("Bob").trait == "aggressive, noob"  # stocké sans emoji


def test_analyser_traits():
    assert analyser("traits") == ("traits", "")


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
    assert "(même joueur ? delete Pizza, puis saisir le bon nom)" in texte
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
    assert "n'est pas dans le carnet" in app.supprimer("Bob")


def test_renommer_garde_rencontres_et_traits(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Pizza")
    app.noter("Pizza", "noob")
    assert "renommé" in app.renommer("pizza", "[IMP] Pizza")
    assert app.carnet.trouver("Pizza") is None
    joueur = app.carnet.trouver("[IMP] Pizza")
    assert (joueur.nom, joueur.rencontres, joueur.trait) == ("[IMP] Pizza", 1, "noob")
    assert "[IMP] Pizza" in (tmp_path / "carnet.json").read_text(encoding="utf-8")


def test_renommer_refuse_les_cas_invalides(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.croiser("Alice")
    assert "existe déjà" in app.renommer("Bob", "alice")
    assert "n'est pas dans le carnet" in app.renommer("Zed", "Zoe")
    assert "Nouveau nom manquant" in app.renommer("Bob", " ")
    assert app.carnet.trouver("Bob") is not None


def test_renommer_juste_la_casse(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("bob")
    assert "renommé" in app.renommer("bob", "Bob")
    assert app.carnet.trouver("bob").nom == "Bob"


def test_analyser_delete_edit():
    assert analyser("delete Bob") == ("delete", "Bob")
    assert analyser("edit [IMP] Pizza") == ("edit", "[IMP] Pizza")


def _saison(n, top_1v1, top_2v2):
    return Classement(saison=n, lignes={"1v1": top_1v1, "2v2": top_2v2}, recupere_le="")


def test_show_liste_les_saisons_ou_le_joueur_est_dans_le_top(tmp_path):
    anciennes = {n: _saison(n, [{"name": "x", "rating": 1}], []) for n in range(1, 29)}
    anciennes[28] = _saison(28, [{"name": "x", "rating": 1}, {"name": "Unloukee", "rating": 900}], [])
    anciennes[12] = _saison(12, [], [{"name": "unloukee", "rating": 500}])
    texte = nouvelle_app(tmp_path, anciennes=anciennes).voir("Unloukee")
    lignes = texte.splitlines()
    assert [l.split(" :")[0].strip() for l in lignes[1:4]] == ["Saison actuelle", "Saison 28", "Saison 12"]
    assert "#2 (800 pts)" in lignes[1] and "2v2 : #1 (600 pts)" in lignes[1]
    assert "1v1 : #2 (900 pts)" in lignes[2] and "2v2 : hors top 100" in lignes[2]
    assert "1v1 : hors top 100" in lignes[3] and "2v2 : #1 (500 pts)" in lignes[3]
    assert "Saison 27" not in texte and "indisponible" not in texte


def test_show_jamais_dans_le_top_les_saisons_passees(tmp_path):
    anciennes = {n: _saison(n, [{"name": "x", "rating": 1}], []) for n in range(1, 29)}
    texte = nouvelle_app(tmp_path, anciennes=anciennes).voir("Bob")
    assert "Saison actuelle : 1v1 : hors top 100" in texte and "Saison 29" not in texte
    assert "Saisons passées : jamais dans le top 100" in texte


def test_show_saison_passee_indisponible(tmp_path):
    anciennes = {n: _saison(n, [{"name": "x", "rating": 1}], []) for n in range(1, 27)}
    texte = nouvelle_app(tmp_path, anciennes=anciennes).voir("Unloukee")
    assert "Saisons indisponibles : 28, 27" in texte


def test_croiser_ne_montre_pas_l_historique(tmp_path):
    anciennes = {28: _saison(28, [], []), 27: _saison(27, [], [])}
    texte = nouvelle_app(tmp_path, anciennes=anciennes).croiser("Unloukee")
    assert "Saison 28" not in texte and "Saison 29" not in texte


def test_note_enregistre_et_apparait_dans_show(tmp_path):
    app = nouvelle_app(tmp_path)
    assert "Note" not in app.voir("Bob")
    assert "enregistrée" in app.memoriser("bob", "rush archers, mauvais perdant")
    assert app.note_actuelle("Bob") == "rush archers, mauvais perdant"
    assert "Note : rush archers, mauvais perdant" in app.voir("Bob")
    assert "Note : rush archers" in app.croiser("Bob")
    assert Carnet.charger(tmp_path / "carnet.json").trouver("Bob").note == "rush archers, mauvais perdant"


def test_note_sans_compter_de_rencontre_et_effacement(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("Bob", "x")
    assert app.carnet.trouver("Bob").rencontres == 0
    assert "effacée" in app.memoriser("Bob", "")
    assert app.note_actuelle("Bob") == ""


def test_note_vide_sur_joueur_inconnu_ne_cree_rien(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("Fantome", "  ")
    assert app.carnet.trouver("Fantome") is None


def test_note_donne_le_nom_officiel_et_apparait_dans_list(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("pizza", "gentil")
    assert app.carnet.trouver("[IMP] Pizza") is None  # nom_canonique ne devine pas le préfixe
    app.memoriser("unloukee", "fort")
    assert app.carnet.trouver("Unloukee").note == "fort"
    assert "Unloukee" in app.liste()


def test_export_import_avec_les_notes(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.memoriser("Bob", "joue le soir")
    message = app.exporter(str(tmp_path / "e.json"))
    assert "notes et historique inclus" in message.lower()
    assert "joue le soir" in (tmp_path / "e.json").read_text(encoding="utf-8")

    pote = App(
        carnet=Carnet(auteur="Kevin"),
        chemin_carnet=tmp_path / "kevin_carnet.json",
        classement=None,
        maintenant=lambda: "2026-11-15T21:00",
    )
    pote.memoriser("Bob", "rush")  # 21:00, après celle d'Antho : conflit, la plus récente gagne
    texte = pote.importer(str(tmp_path / "e.json"))
    assert "1 conflit(s), 0 choix enregistré(s)" in texte
    fiche = sans_couleur(pote.voir("Bob"))
    assert "Note : rush  (Kevin, 15/11/2026)" in fiche
    assert "15/11/2026  Antho  note  : joue le soir" in fiche
    assert "Croisé par Kevin, Antho." in fiche
    assert "rush" in sans_couleur(pote.liste()) and "joue le soir" not in sans_couleur(pote.liste())
    assert pote.note_actuelle("Bob") == "rush"


# --- top : classement complet avec recherche -------------------------------------

def test_analyser_top():
    assert analyser("top") == ("top", "")
    assert analyser("top 2v2 unl") == ("top", "2v2 unl")
    assert analyser("player top") == ("croiser", "top")


def test_top_liste_le_classement_du_mode(tmp_path):
    texte = sans_couleur(nouvelle_app(tmp_path).top("1v1"))
    assert "Top 100 1v1 (saison 29)" in texte
    assert "#1" in texte and "[IMP] Pizza" in texte and "872 pts" in texte
    assert "#2" in texte and "Unloukee" in texte


def test_top_a_un_en_tete(tmp_path):
    lignes = sans_couleur(nouvelle_app(tmp_path).top("1v1")).splitlines()
    assert lignes[1].split() == ["Rang", "Nom", "Points"]


def test_top_2v2(tmp_path):
    texte = sans_couleur(nouvelle_app(tmp_path).top("2v2"))
    assert "Unloukee" in texte and "600 pts" in texte
    assert "Pizza" not in texte


def test_top_filtre_par_fragment_sans_casse_et_garde_le_vrai_rang(tmp_path):
    texte = sans_couleur(nouvelle_app(tmp_path).top("1v1", "LOUK"))
    assert "#2" in texte and "Unloukee" in texte
    assert "Pizza" not in texte


def test_top_filtre_sans_resultat(tmp_path):
    assert "Aucun joueur" in sans_couleur(nouvelle_app(tmp_path).top("1v1", "zzz"))


def test_top_sans_classement(tmp_path):
    assert "indisponible" in nouvelle_app(tmp_path, classement=False).top("1v1")


def test_lire_top_argument(tmp_path):
    app = nouvelle_app(tmp_path)
    assert app.lire_top("") == ("1v1", "")
    assert app.lire_top("2V2") == ("2v2", "")
    assert app.lire_top("2v2 unl") == ("2v2", "unl")
    assert app.lire_top("pizza") == ("1v1", "pizza")


def test_modifier_ne_compte_pas_de_rencontre(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.maintenant = lambda: "2026-11-15T23:00"  # une partie plus tard
    assert app.modifier("bob").startswith("Bob")
    joueur = app.carnet.trouver("Bob")
    assert joueur.rencontres == 1 and joueur.derniere == "2026-11-15T20:00"


def test_modifier_joueur_inconnu(tmp_path):
    app = nouvelle_app(tmp_path)
    assert "pas dans le carnet" in app.modifier("Zorglub")
    assert app.carnet.trouver("Zorglub") is None


def test_noter_refuse_un_trait_hors_liste_sans_rien_enregistrer(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    erreur = app.noter("Bob", "rush archers")
    assert "rush" in erreur and "aggressive" in erreur and "pro" in erreur
    assert app.trait_actuel("Bob") == ""


def test_noter_enregistre_les_mots_cles_normalises(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    assert app.noter("Bob", "agressif, Defense") == ""
    assert app.trait_actuel("Bob") == "aggressive, defence"


def test_analyser_commandes_disparues():
    assert analyser("rename Pizza > Pizzza") == ("rename", "Pizza > Pizzza")
    assert analyser("styles") == ("traits", "")


# --- effets de bord ----------------------------------------------------------------


@pytest.mark.parametrize("texte", [",", " ; ", ", ,"])
def test_trait_sans_aucun_mot_est_refuse_et_n_efface_pas(tmp_path, texte):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")
    message = app.noter("Bob", texte)
    assert "Trait refusé : aucun mot-clé." in message and "Traits possibles" in message
    assert app.trait_actuel("Bob") == "noob"


def test_trait_vide_efface_toujours(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.noter("Bob", "noob")
    assert app.noter("Bob", "  ") == ""
    assert app.trait_actuel("Bob") == ""


def test_export_vers_son_propre_carnet_est_refuse(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.memoriser("Bob", "secret")
    avant = app.chemin_carnet.read_text(encoding="utf-8")
    message = app.exporter(str(app.chemin_carnet))
    assert "Export impossible : ce fichier est le carnet lui-même." in message
    assert app.chemin_carnet.read_text(encoding="utf-8") == avant


def test_show_ne_redemande_pas_la_saison_passee_deux_fois(tmp_path):
    appels = []

    def passee(n):
        appels.append(n)
        return None  # serveur muet

    app = nouvelle_app(tmp_path)
    app.saison_passee = passee
    app.voir("Bob")
    app.voir("Bob")
    assert sorted(appels) == list(range(1, 29))
    app.changer_classement(app.classement)
    app.voir("Bob")
    assert len(appels) == 2 * 28


def test_en_tetes_de_list_et_top_en_couleur(tmp_path):
    from superselection.couleurs import ROLES
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.couleur = True
    code = f"\x1b[{ROLES['entete']}m"
    assert code + "Nom" in app.liste().splitlines()[1]
    assert code + "Rang" in app.top("1v1").splitlines()[1]


def test_show_dit_qui_a_croise_le_joueur(tmp_path):
    app = nouvelle_app(tmp_path)
    autre = Carnet(auteur="Kevin")
    autre.croiser("Bob", quand="2026-11-10T10:00")
    autre.noter("Bob", "noob", maintenant="2026-11-10T10:00")
    autre.sauver(tmp_path / "kevin.json")
    app.importer(str(tmp_path / "kevin.json"))
    assert "Croisé par Kevin." in sans_couleur(app.voir("Bob"))
    app.croiser("Bob")
    fiche = sans_couleur(app.voir("Bob"))
    assert "Croisé par Antho, Kevin." in fiche and "Croisé 1 fois" in fiche
    assert "Croisé par" not in sans_couleur(app.croiser("Bob"))  # en partie : fiche courte


def test_show_seul_moi(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    assert "Croisé par Antho." in sans_couleur(app.voir("Bob"))


def test_export_sur_le_bureau_par_defaut(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    app.bureau = tmp_path / "Bureau"
    app.bureau.mkdir()
    assert str(app.bureau / "Antho.json") in app.exporter("")
    assert (app.bureau / "Antho.json").exists()
    app.exporter("kevin")
    assert (app.bureau / "kevin.json").exists()
    ailleurs = tmp_path / "ailleurs.json"
    app.exporter(str(ailleurs))  # chemin complet : tel quel
    assert ailleurs.exists()


def test_import_ne_cherche_pas_sur_le_bureau(tmp_path, monkeypatch):
    app = nouvelle_app(tmp_path)
    app.bureau = tmp_path / "Bureau"
    app.bureau.mkdir()
    Carnet(auteur="Kevin").sauver(app.bureau / "kevin.json")
    monkeypatch.chdir(tmp_path)
    assert "introuvable" in app.importer("kevin.json")


# --- historique et conflits (ADR 0022) -------------------------------------------


def _pote(tmp_path, auteur="Paul", quand="2026-11-16T20:00"):
    return App(
        carnet=Carnet(auteur=auteur),
        chemin_carnet=tmp_path / f"{auteur}_notebook.json",
        classement=None,
        maintenant=lambda: quand,
    )


def test_show_et_edit_affichent_l_historique_du_plus_recent_au_plus_ancien(tmp_path):
    app = nouvelle_app(tmp_path)
    app.croiser("Bob")
    for heure, trait in (("20:01", "noob"), ("20:02", "pro"), ("20:03", "")):
        app.maintenant = lambda h=heure: f"2026-11-15T{h}"
        app.noter("Bob", trait)
    app.memoriser("Bob", "rush")
    fiche = sans_couleur(app.voir("Bob"))
    assert "Trait : pas encore noté" in fiche and "Note : rush" in fiche
    lignes = fiche.split("Historique (2 version(s) remplacée(s)) :")[1].strip().splitlines()
    assert [l.split(" : ")[1] for l in lignes] == ["👑 pro", "🐣 noob"]
    assert "Historique (2" in sans_couleur(app.modifier("Bob"))
    assert "Historique" not in sans_couleur(app.croiser("Bob"))  # en partie : fiche courte


def test_historique_limite_aux_dix_dernieres_versions(tmp_path):
    app = nouvelle_app(tmp_path)
    for n in range(15):
        app.maintenant = lambda n=n: f"2026-11-15T20:{n:02d}"
        app.memoriser("Bob", f"note {n}")
    fiche = sans_couleur(app.voir("Bob"))
    assert "Historique (14 version(s) remplacée(s))" in fiche
    assert "note 13" in fiche and "note 4" in fiche and "note 3" not in fiche


def test_show_affiche_les_rencontres_des_autres(tmp_path):
    app = nouvelle_app(tmp_path)
    paul = Carnet(auteur="Paul")
    paul.croiser("Bob", quand="2026-11-12T20:00")
    paul.noter("Bob", "pro", maintenant="2026-11-12T20:00")
    paul.sauver(tmp_path / "paul.json")
    app.importer(str(tmp_path / "paul.json"))
    fiche = sans_couleur(app.voir("Bob"))
    assert "Rencontres des autres : Paul 1 fois (12/11/2026)" in fiche
    assert "Croisé par Paul." in fiche
    assert "vu" not in sans_couleur(app.top("1v1"))  # top : mes rencontres seulement


def test_import_demande_un_choix_par_conflit(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("Bob", "rush")
    app.noter("Bob", "noob")
    paul = _pote(tmp_path)
    paul.memoriser("Bob", "rush archers")
    paul.noter("Bob", "pro")
    paul.exporter(str(tmp_path / "paul.json"))
    vus = []

    def decider(conflits, auteur):
        assert auteur == "Paul"
        vus.extend(conflits)
        return ["mienne" if c.champ == "note" else "fusion" for c in conflits]

    app.maintenant = lambda: "2026-11-17T10:00"
    texte = app.importer(str(tmp_path / "paul.json"), decider)
    assert sorted(c.champ for c in vus) == ["note", "trait"]
    assert "2 conflit(s), 2 choix enregistré(s)" in texte
    assert app.note_actuelle("Bob") == "rush"
    assert app.trait_actuel("Bob") == "noob, pro"
    assert Carnet.charger(app.chemin_carnet).trouver("Bob").note == "rush"


def test_import_sans_conflit_ne_demande_rien(tmp_path):
    app = nouvelle_app(tmp_path)
    paul = _pote(tmp_path)
    paul.memoriser("Bob", "rush")
    paul.exporter(str(tmp_path / "paul.json"))

    def decider(conflits, auteur):
        raise AssertionError("pas de question sans conflit")

    app.importer(str(tmp_path / "paul.json"), decider)
    assert app.note_actuelle("Bob") == "rush"


def test_resume_et_description_d_un_conflit(tmp_path):
    app = nouvelle_app(tmp_path)
    app.memoriser("Bob", "rush")
    app.noter("Bob", "noob")
    paul = Carnet(auteur="Paul")
    paul.memoriser("Bob", "autre", maintenant="2026-11-20T20:00")
    paul.memoriser("Bob", "", maintenant="2026-11-21T20:00")  # Paul l'a supprimée
    paul.noter("Bob", "pro", maintenant="2026-11-21T20:00")
    conflits = app.carnet.conflits(paul)
    assert app.resume_conflits(conflits, "Paul") == "2 conflit(s) avec Paul (1 note(s), 1 trait(s)), dont 1 suppression(s)."
    note = next(c for c in conflits if c.champ == "note")
    assert sans_couleur(app.decrire_conflit(note)).splitlines() == [
        "Bob — note",
        "  1. Antho (15/11/2026) : rush",
        "  2. Paul  (21/11/2026) : (supprimée)",
    ]
