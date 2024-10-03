# Données de test ConnectedBluetoothDevice

 # Fonction utilitaire pour vérifier l'existence des fichiers
    # def check_file_exists(directory, filename):
    #     full_path = os.path.join(directory, filename)
    #     exists = os.path.exists(full_path)
    #     print(f"Fichier {filename}: {'Existe' if exists else 'N''existe pas'}")
    #     return exists

    # Créer trois instances de ConnectedBluetoothDevice
    # device1 = ConnectedBluetoothDevice()
    # device2 = ConnectedBluetoothDevice()
    # device3 = ConnectedBluetoothDevice()

    # # Simuler l'ajout de données pour chaque device
    # test_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    # # Device 1
    # device1.CWP_data_to_array([*test_data, 55])  # Données de configuration
    # device1.CWP_data_to_array([*test_data, 15])  # Données SG
    # device1.CWP_data_to_array([*test_data, 25])  # Données Piezos
    # device1.CWP_data_to_array([*test_data, 35])  # Données Capa

    # # Device 2
    # device2.CWP_data_to_array([*test_data, 55])
    # device2.CWP_data_to_array([*test_data, 15])
    # device2.CWP_data_to_array([*test_data, 25])
    # device2.CWP_data_to_array([*test_data, 35])

    # # Device 3
    # device3.CWP_data_to_array([*test_data, 55])
    # device3.CWP_data_to_array([*test_data, 15])
    # device3.CWP_data_to_array([*test_data, 25])
    # device3.CWP_data_to_array([*test_data, 35])

    # # Écrire les données dans les fichiers CSV
    # device1.CWP_data_to_csv()
    # device2.CWP_data_to_csv()
    # device3.CWP_data_to_csv()

    # # Vérifier l'existence des fichiers créés
    # directory = device1.DIRECTORY  # Supposons que tous les devices utilisent le même répertoire

    # expected_files = [
    #     "CWP_Capa_data_0.csv", "CWP_Piezos_data_0.csv", "CWP_SG_data_0.csv",
    #     "CWP_Capa_data_1.csv", "CWP_Piezos_data_1.csv", "CWP_SG_data_1.csv",
    #     "CWP_Capa_data_2.csv", "CWP_Piezos_data_2.csv", "CWP_SG_data_2.csv"
    # ]

    # print("\nVérification des fichiers créés:")
    # all_files_exist = all(check_file_exists(directory, filename) for filename in expected_files)

    # if all_files_exist:
    #     print("\nTous les fichiers attendus ont été créés avec succès!")
    # else:
    #     print("\nCertains fichiers attendus n'ont pas été créés.")

    # print("\nTest terminé.")
