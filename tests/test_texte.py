from superselection.texte import sans_controle


def test_retire_les_caracteres_de_controle():
    assert sans_controle("a\x1b[2Jb\x07") == "a[2Jb"
    assert sans_controle("a\nb\tc\x85d") == "abcd"


def test_garde_les_noms_et_emojis():
    assert sans_controle("妮蔻") == "妮蔻"
    assert sans_controle("👨‍👩‍👧 [IMP] Pizza") == "👨‍👩‍👧 [IMP] Pizza"
