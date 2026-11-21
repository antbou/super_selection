from superselection.texte import sans_controle


def test_retire_les_caracteres_de_controle():
    assert sans_controle("a\x1b[2Jb\x07") == "a[2Jb"
    assert sans_controle("a\nb\tc\x85d") == "abcd"


def test_garde_les_noms_et_emojis():
    assert sans_controle("妮蔻") == "妮蔻"
    assert sans_controle("👨‍👩‍👧 [IMP] Pizza") == "👨‍👩‍👧 [IMP] Pizza"


from superselection.texte import cle_alphabetique, largeur, ajuster, tronquer


def test_tri_alphabetique_ecritures_non_latines_en_bas():
    noms = ["妮蔻", "bob", "Émile", "[IMP] Pizza", "Alice", "Дима", "zed", "42"]
    assert sorted(noms, key=cle_alphabetique) == ["42", "Alice", "bob", "Émile", "[IMP] Pizza", "zed", "Дима", "妮蔻"]


def test_largeur_compte_double_les_caracteres_larges():
    assert largeur("abc") == 3
    assert largeur("妮蔻") == 4
    assert ajuster("妮蔻", 6) == "妮蔻  "
    assert largeur("🛡️ defence") == largeur("🐣 defence") == 10


def test_tronquer():
    assert tronquer("court", 50) == "court"
    assert tronquer("a" * 60, 50) == "a" * 49 + "…"
    assert len(tronquer("a" * 60, 50)) == 50
