# CAD — model obudowy / enclosure model

Pliki do druku 3D. **3D-printable parts.**

| Plik / File | Co to / What it is |
|---|---|
| `stl/case-main.stl` | Obudowa główna — mieści matrycę i elektronikę. *Main enclosure, holds the matrix and electronics.* |
| `stl/cover.stl` | Pokrywa tylna. *Back cover.* |
| `stl/cover-pico.stl` | Pokrywa nad Pico. *Cover over the Pico.* |

Folder nazywa się `cad`, a nie `fusion`, bo pliki STL otworzy i wydrukuje każdy,
niezależnie od tego, w czym projektuje.

*The folder is called `cad`, not `fusion`: STL files are usable by anyone, whatever
CAD package they run.*

## Druk / Printing

Części nie wymagają podpór drukowane płasko. Materiał i kolor dowolne — światło idzie
przez litofanię, nie przez obudowę.

*No supports needed when printed flat. Material and colour are up to you — light
passes through the lithophane, not through the enclosure.*

## Panel z litofanią / The lithophane panel

**Nie ma go tutaj i nie powinno być** — generujesz go ze swojego zdjęcia. Ustawienia
narzędzia [itslitho](https://tool.itslitho.com/CreateModel) są w
[README](../README.md#the-lithophane-panel).
