# Classement lu sur l'API top 100 de warselect.io

Le rang vient de `https://ratings.warselect.io/webapi/top100{1v1|2v2}?season=N`, l'API non documentée qu'utilise ws-stats.pl (trouvée en décodant son JavaScript). Elle ne renvoie que le top 100 et n'a pas de recherche par nom. Un joueur absent est donc « hors top 100 » et non « inconnu ». On ne cherche pas à connaître le rang au-delà de 100.

## Conséquences

- La saison en cours n'est pas fournie par l'API. Elle est détectée en cherchant la dernière saison qui a des joueurs classés en 1v1.
- L'API peut changer sans prévenir. Tout l'accès réseau est dans `classement.py` (`fetch_http`), et un cache permet de continuer à travailler hors ligne.
