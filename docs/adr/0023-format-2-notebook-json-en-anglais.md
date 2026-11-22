# Format 2 : `notebook.json`, champs en anglais, un seul objet par joueur

Le fichier du carnet s'appelle maintenant `notebook.json` et ses champs sont en anglais. Chaque joueur n'apparaît qu'une fois, dans `players`, et chaque information porte son auteur (`by`) au lieu d'être rangée sous un objet par auteur :

```json
{
  "version": 2,
  "owner": "antho",
  "players": [
    {
      "name": "[IMP] Pizza",
      "encountered_by": {"antho": {"count": 3, "last": "2026-11-20T21:00:00"}},
      "trait_history": [{"text": "aggressive, pro", "by": "Paul", "at": "2026-11-20T21:05:00"}],
      "note_history": [{"text": "rush à 3 min", "by": "antho", "at": "2026-11-21T20:00:00"}]
    }
  ]
}
```

`owner` est seulement le pseudo du propriétaire, qui signe ses prochaines modifications. Il n'y a pas de champs `created_by` ni `updated_by` : ils se déduisent de l'historique, et les écrire deux fois risquerait qu'ils ne correspondent plus. Les historiques et les rencontres vides ne sont pas écrits. Le code Python reste en français, comme le veut la règle du projet. Seuls les noms du fichier sont en anglais.

Au premier lancement, un ancien `carnet.json` (format 1) est converti en `notebook.json`, puis renommé `carnet.v1.bak.json`, jamais supprimé. Chaque trait et chaque note par auteur de l'ancien format devient une version de l'historique commun. Le plus récent devient donc la version actuelle, même s'il vient d'un autre auteur. Un ancien fichier illisible n'est pas touché. L'import lit encore le format 1, pour les potes qui n'ont pas encore mis à jour.

## Options écartées

Une liste de propriétaires et une liste de joueurs reliées par des identifiants : le nom du joueur sert déjà d'identifiant (ADR 0002), et des identifiants ne servent à rien dans un fichier qu'on s'envoie à la main.

## Conséquences

Remplace le compromis de l'ADR 0017 (garder la clé `styles`). Une version antérieure à 0.15.0 ne lit pas le format 2 : elle importe un tel fichier sans erreur mais sans rien ajouter. Chacun doit donc faire `update`.
