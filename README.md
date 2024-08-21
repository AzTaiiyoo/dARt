# dARt
# How to install Docker : 
 **build la version du docker** : docker build -t dart-streamlit .
 **run le docker** : docker run -p 8501:8501 --privileged dart-streamlit      
 une fois que c'est fait, se rendre manuelle sur un navigateur internet et rentrer la page : http://localhost:8501
 Si jamais vous voulez rajouter des libraries (par exemple bluepy), allez dans le fichier requirements et rentrer dans une ligne bluepy==version_de_bluepy
 Peu importe la modification que vous faites dans le requirement ou dans le docker file, il rebuild l'image du docker avec la commande de build en ligne 3.
 **Important**, le Docker fonctionne sous python 3.12.4 et sur une version de linux debian:bulls-eye slim. Si la version n'est pas compatible, demandez a Claude ou ChatGPT de recréer un docker file identique mais simplement en
 modifiant la version pour qu'elle convienne à vos besoin.
 List de commande utile si jamais : 
 docker ps -a : renvoie la liste de tous les images conteneurs utilisé ; docker rm id_du_conteneur1 id_du_conteneur2 ...  :  supprimer les images conteneurs ; docker image prune -a : supprimer toutes les images non utilisés.