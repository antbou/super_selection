# Carnet local en JSON, partagé par fichier

Chaque joueur a son propre `carnet.json`, rangé dans le dossier de données de l'utilisateur (platformdirs). On le partage avec `export` et `import` en envoyant le fichier (Discord, mail). Il n'y a ni serveur, ni compte, ni base partagée : rien à héberger, et l'outil marche hors ligne.

## Options écartées

Un carnet partagé en ligne aurait synchronisé tout le monde, mais il fallait un serveur, de l'authentification et une gestion des conflits en direct. C'est trop lourd pour l'usage visé.
