from superselection.carnet import Carnet


def test_croiser_cree_puis_incremente():
    c = Carnet(auteur="Antho")
    j = c.croiser("Pizza", jour="2026-11-10")
    assert (j.rencontres, j.derniere) == (1, "2026-11-10")
    j = c.croiser("pizza", jour="2026-11-12")
    assert (j.nom, j.rencontres, j.derniere) == ("Pizza", 2, "2026-11-12")
    assert len(c.joueurs) == 1


def test_noter_et_effacer_son_style():
    c = Carnet(auteur="Antho")
    c.croiser("Pizza", jour="2026-11-10")
    c.noter("Pizza", "agressif, rush archers", maintenant="2026-11-10T20:00")
    assert c.trouver("PIZZA").styles["Antho"].texte == "agressif, rush archers"
    c.noter("Pizza", "", maintenant="2026-11-10T21:00")
    assert "Antho" not in c.trouver("Pizza").styles


def test_recents_du_plus_recent_au_plus_ancien():
    c = Carnet(auteur="Antho")
    c.croiser("A", jour="2026-11-01")
    c.croiser("B", jour="2026-11-05")
    c.croiser("C", jour="2026-11-03")
    assert [j.nom for j in c.recents()] == ["B", "C", "A"]


def test_sauver_puis_charger(tmp_path):
    chemin = tmp_path / "carnet.json"
    c = Carnet(auteur="Antho")
    c.croiser("妮蔻", jour="2026-11-10")
    c.noter("妮蔻", "défensif", maintenant="2026-11-10T20:00")
    c.sauver(chemin)
    relu = Carnet.charger(chemin)
    assert relu.auteur == "Antho"
    assert relu.trouver("妮蔻").styles["Antho"].texte == "défensif"
    assert "妮蔻" in chemin.read_text(encoding="utf-8")


def test_fusion_ajoute_les_joueurs_et_notes_du_pote():
    moi = Carnet(auteur="Antho")
    moi.croiser("Pizza", jour="2026-11-10")
    moi.noter("Pizza", "agressif", maintenant="2026-11-10T20:00")

    pote = Carnet(auteur="Kevin")
    pote.croiser("pizza", jour="2026-11-11")
    pote.croiser("pizza", jour="2026-11-12")
    pote.noter("pizza", "spam cavalerie", maintenant="2026-11-12T20:00")
    pote.croiser("Ram Pam", jour="2026-11-12")
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
    moi.croiser("Pizza", jour="2026-11-10")
    moi.noter("Pizza", "agressif", maintenant="2026-11-10T20:00")

    pote = Carnet(auteur="Kevin")
    pote.croiser("Pizza", jour="2026-11-10")
    pote.noter("Pizza", "x", maintenant="2026-11-10T20:00")
    pote.trouver("Pizza").styles["Antho"] = pote.trouver("Pizza").styles["Kevin"].__class__(
        texte="falsifié", maj="2099-01-01T00:00"
    )

    moi.fusionner(pote)
    assert moi.trouver("Pizza").styles["Antho"].texte == "agressif"


def test_reimport_met_a_jour_seulement_si_plus_recent():
    moi = Carnet(auteur="Antho")
    v1 = Carnet(auteur="Kevin")
    v1.croiser("Pizza", jour="2026-11-10")
    v1.noter("Pizza", "passif", maintenant="2026-11-10T20:00")
    moi.fusionner(v1)

    v2 = Carnet(auteur="Kevin")
    v2.croiser("Pizza", jour="2026-11-12")
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
    pote.croiser("Bob", jour="2026-11-12")
    bilan = moi.fusionner(pote)
    assert bilan.joueurs_ajoutes == 0
    assert moi.trouver("Bob") is None
