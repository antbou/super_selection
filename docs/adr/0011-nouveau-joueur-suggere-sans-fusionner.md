# Nom inconnu : on suggère des noms proches, on ne fusionne jamais

Taper `Pizza` alors que le carnet contient `[IMP] Pizza` crée un second joueur (ADR 0002). Pour limiter les fautes de frappe, la fiche d'un joueur inconnu partout affiche « Nouveau joueur » et les noms qui contiennent le nom tapé (ou l'inverse). Le joueur est quand même enregistré ; la correction se fait à la main avec `delete` (confirmation demandée) ou `rename <ancien> > <nouveau>` (le séparateur `>` permet les noms avec espaces). `rename` refuse un nom déjà pris : jamais de fusion automatique.
