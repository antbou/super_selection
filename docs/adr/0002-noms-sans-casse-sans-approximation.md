# Noms comparés sans la casse, mais jamais de façon approchée

`pizza` et `Pizza` désignent le même joueur (comparaison en `casefold`). Par contre, `[IMP] Pizza` et `Pizza` restent deux joueurs différents : les tags de clan, les espaces et les caractères spéciaux comptent. Une comparaison approchée fusionnerait à tort des joueurs différents et mélangerait leurs notes. C'est l'auto-complétion par sous-chaîne (Tab) qui retrouve le bon nom, y compris pour un nom collé depuis une capture d'écran.
