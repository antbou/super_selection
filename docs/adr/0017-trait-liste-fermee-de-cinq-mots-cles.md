# Le style devient « trait » : liste fermée de cinq mots-clés

Remplace l'ADR 0008. Le texte libre servait peu : le détail utile (« rush archers ») a sa place dans la note perso (ADR 0014). Le trait se limite donc à `aggressive` 🔥, `defence` 🛡️, `noob` 🐣, `tryhard` 😤 et `pro` 👑, plusieurs possibles. Une saisie hors liste est refusée avec la liste des mots permis ; les variantes (`agressif`, `défense`…) sont enregistrées sous le mot conseillé. Les cinq mots s'affichent dès l'ouverture de la question, sans taper de lettre.

« Style » devient « trait » partout (commande `traits`, supprimée depuis par l'ADR 0020, messages, code, glossaire), car la liste décrit un trait de joueur, pas un texte de style.

Compromis : la clé JSON reste `styles`, pour ne casser aucun carnet existant ni partagé. Les anciens textes libres restent lisibles et affichés tels quels ; ils ne sont validés que s'ils sont modifiés. Ajouter un sixième mot demande de changer le code, mais jamais les carnets (l'emoji reste à l'affichage). `styles` reste accepté comme alias de `traits` (non annoncé), pour ne pas créer un joueur « styles » par habitude.
