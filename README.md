# Atelier Guitare

Atelier Guitare is a Windows desktop editor for guitarists who want to print their own song sheets. Arrange six-string tablature, chord diagrams, lyrics and titles on A4 pages, then export the layout as a vector PDF. The application interface is in French.

**[Download Atelier Guitare for Windows x64](https://github.com/Bruxellesflorian/atelier-guitare/releases/latest/download/AtelierGuitare.exe)** · [Guide en français](README.fr.md)

Download and double-click `AtelierGuitare.exe` to start. The executable includes Python, Qt and the chord library.

## Make your first sheet

1. Choose **Tablature…** and use the arrow keys to select a string and column. Type a fret from 0 to 24. For a hammer-on, for example, enter `5`, `h` and `7` in consecutive columns. Press `|` to toggle a bar line before the current column. You can change the tuning, note spacing and measures per line.
2. In **Accords**, search for a chord such as **Am7** and double-click it to place it on the page. The built-in library contains 132 diagrams across 12 keys. In **Créer un accord**, you can design a voicing with finger numbers, open or muted strings and a barre.
3. Choose **Texte…** for a title or lyrics. Drag blocks into position and resize them using their corner handles. Chord diagrams keep their proportions. Ctrl-click several blocks and right-click to align them.
4. Use **+ Page** to add another sheet. Press **Ctrl+S** to save an editable `.gtab` project. Choose **Exporter en PDF…** to export every page. For a printout at the size shown on the sheet, select A4 paper and 100% scale.

## Run from source

The Windows x64 build was tested with Python 3.14. Run these commands in PowerShell from the repository directory.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Build the Windows executable

In a dedicated PowerShell window, use the following commands after installing the dependencies above. Limiting the DLL search path prevents PyInstaller from picking up incompatible libraries from other applications.

```powershell
$pythonBase = .\.venv\Scripts\python.exe -c "import sys; print(sys.base_prefix)"
$env:Path = "$pythonBase;$env:SystemRoot\System32;$env:SystemRoot"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean AtelierGuitare.spec
```

The build writes a standalone executable to `dist\AtelierGuitare.exe`. The spec bundles the chord catalogue and the application icon.

## Project files and personal chords

A `.gtab` project stores page order, positions, sizes and the contents of every block in UTF-8 JSON. Each inserted chord includes its own fingering, so you can share the project with another player. The personal library is stored separately in `mes_accords.json` in the Qt user data directory. To extend the bundled catalogue, edit `chords_data.json` and rebuild.
