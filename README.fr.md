# Atelier Guitare

Application Windows de composition de tablatures et de mise en page A4 multipage. Le binaire compilé se trouve dans `dist/AtelierGuitare.exe`. Double-cliquez dessus pour ouvrir une feuille vierge.

## Sources et architecture

```text
Guitare/
├── main.py              Fenêtre principale, dialogues et cycle de vie du projet
├── canvas_a4.py         Scènes A4, sélection, poignées, règles et export PDF
├── drawing.py           Dessin vectoriel des trois types de bloc
├── tab_editor.py        Grille à six cordes et édition au clavier
├── chord_library.py     Recherche, aperçu et bibliothèque personnelle
├── chord_creator.py     Manche interactif, doigtés et barré
├── chords_data.json     132 diagrammes intégrés
├── atelier_guitare.ico  Icône de fenêtre et d’exécutable Windows
├── storage.py           Schéma du projet, validation et écritures atomiques
├── requirements.txt     Versions utilisées pour cette compilation
├── AtelierGuitare.spec  Configuration produite par PyInstaller
├── README.md
└── dist/
    └── AtelierGuitare.exe
```

## Lancer les sources

Depuis PowerShell, dans le dossier du projet, avec Python 3.14 x64 pour reproduire la compilation testée :

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

PySide6-Essentials fournit Qt Widgets et QPdfWriter. Les modules partagent la même fonction de dessin pour la page interactive et l’export.

## Compiler pour Windows

Dans une fenêtre PowerShell dédiée à la compilation, limitez le chemin de recherche aux DLL de Python et de Windows. Cela évite que PyInstaller intègre une version d’ICU fournie par un autre logiciel.

```powershell
$pythonBase = .\.venv\Scripts\python.exe -c "import sys; print(sys.base_prefix)"
$env:Path = "$pythonBase;$env:SystemRoot\System32;$env:SystemRoot"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name AtelierGuitare --icon atelier_guitare.ico --add-data "atelier_guitare.ico;." --add-data "chords_data.json;." main.py
```

Le résultat est `dist\AtelierGuitare.exe`. Le catalogue est embarqué dans le binaire. Pour changer les accords livrés par défaut, modifiez le JSON avant de recompiler.

## Composer une feuille

1. Cliquez sur **Tablature…**. Parcourez les cellules avec les flèches. Tapez une frette de 0 à 24. Pour une frette à deux chiffres, tapez les deux chiffres en moins de 1,2 seconde. Une cellule accueille une frette ou un symbole de technique. Placez par exemple `5`, `h`, `7` dans trois colonnes consécutives.
2. Tapez `|` pour ajouter ou retirer une barre avant la colonne sélectionnée. Le bord gauche de la première colonne tient lieu de barre initiale. Les colonnes sont communes aux six cordes. L’éditeur accepte de 1 à 512 colonnes par bloc. L’insertion ajoute une colonne à droite de la sélection.
3. Réglez les mesures par ligne et l’espacement. L’accordage est affiché de la corde aiguë à la corde grave. Validez pour placer le bloc.
4. Dans **Accords**, recherchez un nom et double-cliquez sur le résultat ou cliquez sur **Insérer sur la feuille**. La recherche accepte les bémols usuels, par exemple `Gb` pour `F#`.
5. Dans **Créer un accord**, choisissez le nom, la première frette et éventuellement le doigt. Cliquez sur la grille ou sur la rangée ○/×. Pour un barré, cochez l’option puis glissez horizontalement entre deux cordes. Le retrait du barré conserve les positions de frettes que vous pouvez ensuite modifier. Les boutons permettent d’insérer le diagramme ou d’en conserver une copie dans la bibliothèque.
6. Ajoutez du texte avec **Texte…**. Réglez le corps dans le dialogue. Sur la feuille, les poignées règlent la zone de retour à la ligne. Agrandissez le cadre si les paroles dépassent.
7. Déplacez les objets par glissement et redimensionnez-les par les quatre coins. Pour un diagramme d’accord, chaque poignée ajuste la largeur et la hauteur dans la même proportion, en gardant le coin opposé fixe. Double-cliquez pour modifier le contenu. Sélectionnez plusieurs objets par Ctrl+clic ou avec un rectangle de sélection depuis une zone libre. Le menu contextuel permet d’aligner les éléments dans l’enveloppe de la sélection. Avec un seul objet, l’alignement utilise les bords de la feuille.
8. Utilisez **+ Page** pour ajouter une feuille, puis la liste des pages pour naviguer. Les règles sont graduées en millimètres. Le magnétisme optionnel ajuste les déplacements à une grille de 1 mm. Ctrl+molette zoome et **Page entière** recadre.
9. Enregistrez le projet avec Ctrl+S. **Exporter en PDF…** produit un PDF vectoriel contenant toutes les pages dans leur ordre. Pour imprimer au format composé, sélectionnez A4 et une échelle de 100 %.

## Fichiers de données

Le projet `.gtab` est du JSON UTF-8 versionné. Chaque page contient ses objets dans l’ordre de superposition avec leur type, leurs coordonnées, leurs dimensions et leur contenu. Une unité vaut un tiers de millimètre. Les diagrammes insérés sont intégralement inclus dans le projet.

La bibliothèque personnelle est enregistrée dans `mes_accords.json` sous le répertoire de données utilisateur Qt, normalement `%APPDATA%\AtelierGuitare\Atelier Guitare`. Plusieurs variantes peuvent porter le même nom. Dans le catalogue JSON, les tableaux `frets` et `fingers` vont de la corde grave vers l’aiguë. Une frette de −1 indique une corde étouffée et 0 une corde à vide. Les autres frettes sont absolues. Un doigt de 0 masque son numéro. Le champ `barre` vaut `null` ou contient la frette absolue et les indices des deux cordes extrêmes, numérotées de 0 à 5.

