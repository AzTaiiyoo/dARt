import os

# Vérifier si nous sommes dans un environnement graphique
#if 'DISPLAY' in os.environ:
from Evalkit_GUI import GridEYE_Viewer

def main():
    GridEYE_Viewer()

if __name__ == "__main__":
    main()
else:
    print("Exécution dans un environnement sans interface graphique.")
    # Ici, vous pouvez ajouter du code pour exécuter des tests non graphiques
    # Par exemple :
    # from Evalkit_CLI import run_tests
    # run_tests()