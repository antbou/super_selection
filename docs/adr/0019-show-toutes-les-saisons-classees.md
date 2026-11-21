# `show` parcourt toutes les saisons et n'affiche que celles où le joueur est classé

Remplace l'ADR 0012. `show <nom>` affiche toujours la ligne de la saison en cours, puis une ligne par saison passée où le joueur est dans le top 100 (1v1 ou 2v2), de la plus récente à la plus ancienne. Les saisons où il est absent ne sont pas listées ; s'il n'a jamais été classé, une ligne le dit. Les saisons injoignables (hors ligne sans cache) sont regroupées sur une seule ligne « Saisons indisponibles ».

Compromis : le premier `show` de la session télécharge toutes les saisons passées (2 requêtes par saison, une cinquantaine fin 2026). Elles partent en parallèle (8 à la fois) et chaque saison finie reste en cache définitif (`saison-N.json`), donc l'attente n'a lieu qu'une fois par installation. Choisi plutôt que de se limiter aux 2 saisons précédentes, qui cachait les anciens joueurs du top.
