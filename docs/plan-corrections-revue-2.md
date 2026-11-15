# Plan : corriger les constats de la seconde revue (version 0.9.0, commit a2fb0d8)

Ce plan est écrit pour un agent qui n'a pas suivi la revue. Il se suffit à lui-même.
Les numéros de ligne valent pour le commit `a2fb0d8` ; ils bougent au fil des étapes,
retrouver le code par son nom.

## Objectif

Après ce travail : l'auto-complétion des noms marche pendant toute la session, les deux
parcours de saisie (rencontre et `edit`) se comportent pareil, et les messages parlent de
« trait » là où il s'agit de traits. Aucune fonctionnalité nouvelle.

## Règles à respecter

- Lire `CLAUDE.md`, `GLOSSARY.md` et `docs/adr/` avant de commencer.
- TDD : écrire le test qui échoue, puis le code. `uv run pytest` après chaque étape
  (154 tests passent au départ).
- Le réseau n'est jamais appelé en test : il est injecté.
- Code, noms et messages en français ; commandes en anglais.
- Compatible Windows : `pathlib`, `encoding="utf-8"`, aucune commande shell.
- Couleurs uniquement par `couleurs.peindre`.
- La logique va dans `app.py` (testée) ; `cli.py` reste mince.
- Un commit par étape, message `fix: …` en français. Aucune ligne d'attribution
  (`Co-Authored-By`) dans les commits.
- Ne pas pousser : le propriétaire relit avant.
- Si une correction semble demander plus que ce qui est écrit ici, s'arrêter et le signaler.

## Étape 1 — Une session par genre de question (constats 1, 2, historique partagé)

### Le problème

`cli.py`, fonction `demander` dans `_principal` :

```python
if "trait" not in question.casefold():
    return session.prompt(ANSI(question), default=defaut)
return session.prompt(ANSI(question), default=defaut, completer=completeur_trait, ...)
```

- `PromptSession.prompt()` **garde sur la session** tout argument qu'on lui passe
  (`completer`, `complete_while_typing`…). Après la première question de trait, l'invite
  `adversaire >` et toutes les autres questions utilisent `CompleteurTrait` : plus aucun
  nom ni commande proposé jusqu'au redémarrage. Vérifié sur prompt_toolkit 3.0.53.
- Le choix du compléteur lit le texte de la question. Les confirmations de `delete` et
  `reset` contiennent « trait(s) » / « traits » : elles ouvrent le menu des cinq traits.
- L'historique est commun : flèche haut à l'invite principale rappelle les notes perso et
  les « oui » tapés.

### La correction

1. Changer le contrat de `Demander` : `demander(question, defaut, genre="texte")`, avec
   `genre` parmi :
   - `"trait"` : questions de trait (`_questions`, `_editer`) ;
   - `"nom"` : champ « Nom » de `_editer` (complète les noms, utile pour retrouver le nom
     officiel) ;
   - `"texte"` (défaut) : note perso, confirmations `delete` et `reset`. Aucune complétion.

   Les appelants passent `genre=` par mot-clé. Plus aucun test sur le texte de la question.
2. Dans `_session`, créer **trois `PromptSession` distinctes**, chacune avec son compléteur
   fixé à la construction, et ne plus jamais passer `completer=` à `prompt()` :
   - principale : `Completeur()` (noms + commandes), historique normal ;
   - trait : `CompleteurTrait()`, `history=DummyHistory()` ;
   - texte : sans compléteur, `history=DummyHistory()`.

   Le genre `"nom"` peut utiliser une quatrième session ou la principale avec
   `DummyHistory` : au choix, tant que rien n'est passé à `prompt()` qui change la session
   principale. `pre_run` et `default` ne sont pas gardés par la session : ils restent des
   arguments d'appel.
3. `_session` renvoie de quoi construire `demander` ; adapter ses deux utilisateurs dans
   les tests (`test_boucle_interactive_continue_si_l_enregistrement_echoue` remplace
   `_session` par une fausse session, `test_traits_proposes_des_le_debut_sans_taper_de_lettre`
   récupère le compléteur de trait).
4. Les tests appellent `executer` avec `lambda q, d: …` : les passer en
   `lambda q, d, genre="texte": …` (ou `**_`).

### Tests à écrire d'abord

- Avec `create_pipe_input()` et `create_app_session(input=…, output=DummyOutput())` de
  prompt_toolkit : poser une question de trait via le vrai `demander`, puis vérifier que
  le compléteur de la session principale est toujours le `Completeur` de noms. C'est le
  test qui manquait ; il doit échouer avant la correction.
- `delete Bob` et `reset` appellent `demander` avec `genre="texte"` ; les questions de
  trait avec `genre="trait"` ; le champ Nom d'`edit` avec `genre="nom"` (un faux
  `demander` qui enregistre les genres reçus suffit).

## Étape 2 — « - » efface aussi dans `edit` (constat 3)

### Le problème

À la rencontre (`_questions`), « - » efface le trait ou la note. Dans `_editer`, il faut
vider le champ ; « - » y donne « Trait refusé : « - » inconnu(s) » pour le trait, et
enregistre une note perso « - » pour la note.

### La correction

Dans `_editer`, traiter une réponse « - » comme une réponse vide pour le trait et pour la
note (pas pour le nom). Vider le champ continue d'effacer. Ajouter une phrase à
l'ADR 0016 et à la ligne `edit` du README si elle décrit l'effacement.

### Tests

- `edit Bob` avec « - » au trait : trait effacé, message « Trait effacé. », pas de refus.
- `edit Bob` avec « - » à la note : note effacée, `mon_memo` vaut `""`.

## Étape 3 — `rename` et `styles` ne créent plus de joueur fantôme (constat 4)

### Le problème

Ces deux commandes ont disparu (ADR 0016, ADR 0017). Les taper par habitude crée un
joueur nommé « rename Pizza > Pizzza » ou « styles », avec une rencontre.

### La correction

Dans `app.py`, ajouter à `COMMANDES` : `"rename": "rename"` et `"styles": "traits"`.
`styles` devient un simple alias de `traits`. `rename` affiche, sans rien modifier :
« `rename` n'existe plus : utilise « edit <nom> » pour changer un nom. » Ne pas les ajouter
à `NOMS_COMMANDES` ni à `AIDE`. La règle existante reste : une ligne égale au nom d'un
joueur connu est une rencontre.

### Tests

- `analyser("rename Pizza > Pizzza")` renvoie la commande `rename` ;
  `executer` n'ajoute aucun joueur et affiche le message.
- `analyser("styles")` renvoie `traits`.

## Étape 4 — Vocabulaire « trait » dans les messages (constat 5)

« Note » désigne maintenant la note perso privée (ADR 0014). Remplacer là où il s'agit de
traits :

| Où | Avant | Après |
|---|---|---|
| `carnet.py`, `Bilan` | `notes_ajoutees`, `notes_maj` | `traits_ajoutes`, `traits_maj` |
| `app.py`, `importer` | « N note(s) ajoutée(s), N note(s) mise(s) à jour. Tes notes n'ont pas été touchées. » | « N trait(s) ajouté(s), N trait(s) mis à jour. Tes traits et tes notes perso n'ont pas été touchés. » |
| `cli.py`, question du pseudo | « il signe tes notes quand tu partages ton carnet » | « il signe tes traits quand tu partages ton carnet » |
| `carnet.py`, docstring de `fusionner` | « notes » | « traits » |
| `README.md`, section « Partager avec un pote » | « ses propres notes », « tes notes sont mises à jour » | « ses propres traits », « tes traits sont mis à jour » |
| `pyproject.toml`, `description` | « …et style de jeu. » | « …et traits des joueurs. » |
| `README.md`, exemple de mise à jour | `0.3.0` / `0.2.0` | laisser : c'est un exemple |

Chercher d'autres restes avec `grep -n -i "note" src/ README.md` et corriger ceux qui
parlent d'un trait. La classe `Note` et la clé JSON `styles` ne changent pas (glossaire,
ADR 0017). Mettre à jour les tests qui lisent ces champs ou ces textes
(`tests/test_carnet.py` lignes 56, 93, 97 ; `tests/test_app.py` pour le message d'import).

## Étape 5 — Auteurs comparés sans la casse à la fusion (reste F8)

### Le problème

`Carnet.fusionner` compare l'auteur à « moi » sans la casse, mais cherche le trait
existant avec `mien.traits.get(auteur)`, sensible à la casse : `Kevin` et `kevin` donnent
deux traits pour le même pote.

### La correction

Dans `fusionner`, chercher la clé existante sans la casse et la réutiliser telle qu'elle
est déjà écrite dans mon carnet :

```python
cle = next((a for a in mien.traits if a.casefold() == auteur.casefold()), auteur)
```

puis lire et écrire `mien.traits[cle]`.

### Test

Mon carnet a un trait de `Kevin` sur Bob ; j'importe un carnet d'auteur `kevin` avec un
trait plus récent sur Bob : un seul trait, mis à jour, sous la clé `Kevin`.

## Étape 6 — Complétion plus juste (constat 6 et compléteur de trait)

- `Completeur.get_completions` : pour `edit` et `delete`, ne proposer que les noms du
  carnet (`app.carnet.joueurs`), pas le top 100. `show` et `player` gardent tous les noms.
- `CompleteurTrait` : ne pas reproposer un trait déjà présent avant le mot en cours
  (`traits.valider` sur le texte qui précède donne les mots déjà retenus).

Tests : `Document("edit Mar")` ne propose pas un nom présent seulement dans le classement ;
`Document("noob, ")` ne propose plus `noob`. Adapter
`test_traits_proposes_des_le_debut_sans_taper_de_lettre` si besoin.

## Étape 7 — Petits effets de bord dans `app.py`

### 7a. Trait « , » ou « ; »

`App.noter` avec un texte non vide qui ne contient aucun mot (« , ») efface le trait et le
CLI affiche « Trait enregistré. ». Correction : si le texte tapé n'est pas vide mais que
`valider` ne renvoie ni mot retenu ni mot refusé, renvoyer une erreur
« Trait refusé : aucun mot-clé. » suivie de `aide_traits()`. Un texte vraiment vide
continue d'effacer.

### 7b. `export` vers son propre carnet

`export` vers le chemin de `carnet.json` réécrit le carnet sans les notes perso.
Correction dans `App.exporter` : si `cible.resolve() == self.chemin_carnet.resolve()`,
refuser avec « Choisis un autre fichier : celui-ci est ton carnet. », sans rien écrire.

### 7c. Message « Noms proches »

`App.croiser` conseille « edit sur l'autre pour le renommer », ce qui sera refusé puisque
le nom tapé vient d'être créé. Remplacer la parenthèse par :
« (si c'est le même joueur : delete {nom tapé}, puis tape le bon nom) ». Mettre à jour la
phrase correspondante de l'ADR 0011 et le test qui lit ce message.

### 7d. `show` quand le serveur ne répond pas

`App._lignes_saisons` rappelle `saison_passee` à chaque `show` : serveur muet = jusqu'à
10 s d'attente par saison, à chaque fois. Correction : `App` garde en mémoire, pour la
session, le résultat de `saison_passee` par numéro de saison (y compris `None`). Ajouter
une méthode `App.changer_classement(classement)` qui remplace `self.classement` et vide
cette mémoire ; `refresh` dans `cli.py` l'utilise au lieu d'affecter `app.classement`.

Tests : deux `voir` de suite n'appellent `saison_passee` qu'une fois par saison ; après
`changer_classement`, il est rappelé.

## Étape 8 — `update` (échec affiché en vert, PATH sous Windows)

### Le problème

- `lancer_mise_a_jour` renvoie un texte, affiché en vert même quand c'est « uv
  introuvable » ou « La mise à jour a échoué », puis l'outil quitte.
- Sous Windows, si `powershell` est introuvable, `Popen` lève `OSError` : la boucle
  affiche « Impossible d'enregistrer le carnet », ce qui est faux.
- La fenêtre de mise à jour relance `superselection` par le PATH hérité, qui peut ne pas
  encore contenir `%USERPROFILE%\.local\bin` (reste W6).

### La correction

- `version.lancer_mise_a_jour()` renvoie `(reussi: bool, message: str)`. `OSError` de
  `Popen` ou de `run` y est attrapé et donne `(False, "Impossible de lancer la mise à jour : …")`.
- `cli.py` : en cas d'échec, afficher le message avec le rôle `erreur` et **rester** dans
  l'outil (`return True`) ; en cas de succès, comme aujourd'hui (vert, puis quitter).
- Commande PowerShell : relancer par le chemin complet s'il existe, sinon par le PATH :

  ```powershell
  Start-Sleep 2; irm <INSTALL_PS1> | iex; $exe = "$env:USERPROFILE\.local\bin\superselection.exe"; if (Test-Path $exe) { & $exe } else { superselection }
  ```

  Rien ne peut être exécuté sous Windows ici : tester seulement la forme de la commande
  (en remplaçant `subprocess.Popen` et `os.name` par `monkeypatch`), et le signaler dans
  le compte rendu.

Tests : échec de `uv` (code de retour ≠ 0) et `uv` introuvable donnent `reussi == False` ;
`executer(app, "update", …)` renvoie alors `True` et n'affiche pas de message de succès.

## Étape 9 — Le 1v1 de la saison en cours n'est plus téléchargé deux fois (reste W4)

`charger_classement` appelle `derniere_saison(fetch, …)`, qui télécharge le 1v1 de la
saison trouvée, puis le retélécharge dans `{mode: fetch(mode, saison) for mode in MODES}`.
Correction : dans `charger_classement`, envelopper `fetch` dans une petite fonction qui
garde les réponses par `(mode, saison)` le temps de l'appel, et passer cette fonction aux
deux endroits.

Test : avec un faux `fetch` qui compte ses appels, `("1v1", saison en cours)` n'est
demandé qu'une fois.

## Étape 10 — Documentation

- **ADR 0005** : `install.ps1` est publié en LF (`git ls-files --eol` : `i/lf`), alors que
  l'ADR exige du CRLF, et l'installation marche. Avec `irm … | iex` le script est passé
  comme une chaîne : seule la contrainte ASCII compte. Corriger la dernière ligne de
  l'ADR : « `install.ps1` doit rester en ASCII (PowerShell 5.1 lit mal l'UTF-8 sans BOM) ;
  les fins de ligne sont indifférentes. » Ne pas toucher à `install.ps1` ni aux fins de
  ligne.
- **`docs/revue-2026-11-15.md`** et **`docs/plan-corrections-bugs.md`** décrivent la
  version 0.2.0. Ajouter en tête de chacun une ligne : « Document historique (version
  0.2.0) : les points B1 à B8, W2, W3, S2, F1, F2 sont corrigés ; suite dans
  `plan-corrections-revue-2.md`. »
- **ADR 0016** : noter que « - » efface aussi dans `edit` et que `rename` affiche un
  renvoi vers `edit`. **ADR 0017** : noter que `styles` reste un alias de `traits`.
- **`GLOSSARY.md`** : dans « Rencontre », retirer la répétition « (taper son nom, ou
  `player <nom>`) » → « (directement, ou avec `player <nom>`) ».
- **`README.md`** : vérifier que le tableau des commandes et la section `edit` collent
  aux étapes 2 et 3.

## Étape 11 — Version

Passer `version` à `0.9.1` dans `pyproject.toml`, lancer `uv lock`, vérifier
`uv run pytest`, puis lancer une fois l'outil à la main :

```text
SUPERSELECTION_DIR=<dossier temporaire> uv run superselection
```

Vérifier dans un vrai terminal : taper un nom, noter un trait, puis taper le début d'un
autre nom — Tab doit proposer des noms, pas des traits. Vérifier aussi que
`delete <nom>` n'ouvre aucun menu.

## Hors du plan

Ne pas y toucher : historique des parties (F3), nouveaux mots-clés (F4), coéquipier 2v2
(F5), écrasement silencieux d'un fichier par `export`, largeur d'affichage des noms
chinois dans `list` (W5), installation depuis un tag (S1).

## Compte rendu attendu

Pour chaque étape : fait ou non, tests ajoutés, et tout ce qui n'a pas pu être vérifié
(en particulier la partie Windows de l'étape 8).
