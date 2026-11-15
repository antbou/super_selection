# Retaper un nom dans les 30 minutes ne compte pas une nouvelle rencontre

En partie, on retape le nom pour relire la note : sans règle, le compteur monte à chaque fois. Une rencontre n'est donc recomptée que 30 minutes après la précédente ; `derniere` stocke la date et l'heure. Un ancien carnet qui n'a qu'une date ne bloque jamais le comptage. Compromis : deux vraies parties d'affilée contre le même adversaire, en moins de 30 minutes, ne comptent que pour une.
