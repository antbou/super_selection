# Une rencontre ou un `edit` est une transaction : Ctrl+C annule tout

Taper un nom puis répondre aux questions (trait, note), ou lancer `edit`, forme un tout : si on interrompt (Ctrl+C, Ctrl+D, ou une erreur), le carnet revient exactement à son état d'avant, rencontre et renommage compris, et rien n'est écrit sur disque. À la fin normale, le carnet est écrit une seule fois.

Avant, chaque étape s'enregistrait aussitôt : un Ctrl+C laissait un joueur à moitié saisi, avec une rencontre comptée pour rien.

Compromis : interrompre à la dernière question perd aussi le trait déjà tapé ; il faut le retaper. Une saisie sans rien changer n'écrit pas le fichier.
