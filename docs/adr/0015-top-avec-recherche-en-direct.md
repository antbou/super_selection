# `top` : le top 100 complet, filtré pendant la frappe

`top [1v1|2v2]` ouvre un écran plein terminal : la liste du top 100 du mode choisi, une ligne de recherche en bas. Chaque frappe relance le filtre après 120 ms sans nouvelle frappe (debounce), sur un fragment du nom, sans casse ; le rang d'origine reste affiché. Tab bascule 1v1/2v2, Échap sort. `top 2v2 unl` (avec filtre) ou hors terminal interactif imprime simplement la liste filtrée, ce qui reste testable.

Ce n'est pas un « mode 2v2 spécial » (ADR 0009) : c'est une vue du classement, sans notion d'équipe ni effet sur le carnet (pas de rencontre comptée). Compromis : un écran plein terminal (prompt_toolkit `Application`) plutôt qu'une liste en dessous du prompt, pour pouvoir afficher 100 lignes qui changent ; le rendu interactif n'est pas testé automatiquement, la logique (`App.top`, `App.lire_top`) l'est.
