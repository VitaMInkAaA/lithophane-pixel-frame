# LED Lampka — ramka 7 × 9 na Raspberry Pi Pico W

Drukowana w 3D ramka z matrycą WS2812 **7 szeroko × 9 wysoko (63 diody)**, przyciskiem
dotykowym TTP223 i panelem WWW. Sterowanie dotykiem albo z telefonu — bez chmury,
wszystko lokalnie na Pico.

## Podłączenie

| Sygnał | Pico | Uwagi |
|---|---|---|
| DIN matrycy | **GP0** (pin 1) | opcjonalnie rezystor 330 Ω w szereg przy pierwszej diodzie |
| OUT z TTP223 | **GP2** (pin 4) | |
| VCC TTP223 | **3V3(OUT)** (pin 36) | **nie 5 V** — GPIO Pico nie jest 5 V tolerant |
| GND wszystkiego | GND (pin 38) | masa wspólna z zasilaczem |
| zasilanie Pico | **VSYS** (pin 39) | opcjonalnie przez diodę Schottky |
| zasilanie matrycy | osobna para przewodów wprost od zasilacza | |

### Elementy opcjonalne

Referencyjny egzemplarz działa bez nich. To dobra praktyka, warta dołożenia,
jeśli natkniesz się na odpowiadający jej problem:

| Element | Po co |
|---|---|
| **dioda Schottky** 1N5817 / SS14, ≥ 1 A | na `VSYS`, żeby dało się mieć podłączony zasilacz i USB jednocześnie |
| **rezystor 330 Ω** | w szereg z linią danych przy pierwszej diodzie — tłumi odbicia przy dłuższym przewodzie |
| **kondensator 470–1000 µF**, ≥ 6,3 V | między 5 V i GND na wejściu matrycy — przyjmuje skoki prądu przy przełączaniu wielu diod naraz |
| **konwerter poziomów 74AHCT125** | tylko jeśli diody wariują przy danych 3,3 V |

Taśma naklejona wężykiem: **pierwsza dioda w prawym dolnym rogu** (patrząc na ramkę
z przodu), pasek idzie **w górę**, zawraca i schodzi w dół — czyli kolumnami po 9.
Tak jest ustawione fabrycznie w `config.py`. Kod przelicza to na współrzędne (x, y)
z zerem w lewym górnym rogu, więc animacje pisze się normalnie, bez myślenia o wężyku.
Jeśli Twoja ramka jest polutowana inaczej, nie zgaduj — uruchom **Kreator** w panelu
(Ustawienia → Geometria), odpowiedz na dwa pytania o to, co widzisz, i ustawi się sam.

63 diody na pełnej bieli to ~3,8 A. Domyślna jasność 40 % daje ~1,5 A, a panel pokazuje
szacowany pobór przy każdej zmianie suwaka.

## Model do druku

Wszystko do obudowy leży w folderze **`cad/`**:

| Plik | Co to |
|---|---|
| `stl/case-main.stl` | obudowa główna — mieści matrycę i elektronikę |
| `stl/cover.stl` | pokrywa tylna |
| `stl/cover-pico.stl` | pokrywa nad Pico |

Drukowane płasko części nie wymagają podpór. Materiał i kolor dowolne — światło idzie
przez litofanię, nie przez obudowę.

Folder nazywa się `cad`, a nie `fusion`, bo pliki mają służyć też komuś bez
Fusion 360. Nazwa związana z jednym programem sugerowałaby, że bez niego nie ma tu
czego szukać.

**Samego panelu z litofanią w repozytorium nie ma** — generujesz go ze swojego
zdjęcia, patrz niżej.

## Litofania (panel ze zdjęciem)

Ramka jest zrobiona pod **zdjęcie pionowe w proporcji 3:4** — prosto z iPhone'a albo
dowolne o tej samej proporcji. Zdjęcie poziome ani kwadratowe **nie zmieści się**
w ramce; najpierw przytnij je do pionu 3:4.

Model generujesz na **<https://tool.itslitho.com/CreateModel>** z takimi ustawieniami:

| Sekcja | Ustawienie | Wartość |
|---|---|---|
| **Shape** | Shape | `Arc` |
| | Height | `150 mm` |
| | Width | *automatycznie* (~109,5 mm — wynika z proporcji zdjęcia) |
| | Angle | `50°` |
| | Min Thick | `0,8 mm` |
| | Max Thick | `3,2 mm` |
| | Crop / Inside | wyłączone |
| **Frame** | Frame | `Frame` |
| | Thickness | `3 mm` |
| | Depth | `4 mm` |
| | Angle | `45°` |
| | Advanced | wyłączone |
| **Quality** | mm per pixel | `0,1 mm` |
| | Preview Model | `Low` |
| **Attributes** | Enable lamp / Close bottom / Nightlight | wszystko wyłączone |
| **Model** | Lighting | `Back lighted` |
| | Light intensity | `5 – 95 %` |
| | Auto update / Cura fix | włączone |
| **Image** | Positive image | włączone |
| | Flip / Mirror image | wyłączone |
| | Placement horizontal / vertical | `50 % / 50 %` |
| | Zoom factor | `100 %` |

Dlaczego akurat tak:

- **0,8–3,2 mm grubości** to jest cały mechanizm litofanii — cienkie miejsca
  przepuszczają światło, grube blokują. Poniżej 0,8 mm panel robi się kruchy i źle
  się drukuje.
- `Back lighted` jest istotne: narzędzie odwraca wtedy mapę grubości pod panel
  podświetlany od tyłu, czyli dokładnie tak, jak siedzi matryca.
- Przy `0,1 mm na piksel` plik STL ma około **165 MB**. To normalne dla litofanii,
  ale krojenie chwilę trwa.
- Drukuj w **białym albo naturalnym PLA**, łuk nie wymaga podpór. Wygięcie panelu
  jest celowe: odsuwa go od diod, dzięki czemu pojedyncze piksele rozmywają się
  w równą poświatę zamiast świecić jako kropki.

## Wgranie na Pico

Potrzebny MicroPython dla **Pico W** (biblioteki `neopixel` i `network` są w firmware,
nic nie doinstalowujesz).

Na Pico trafia **cała zawartość folderu `firmware/`**, z zachowaniem układu — pliki
`.py` do katalogu głównego, panel do katalogu `www`:

```bash
cd firmware
mpremote connect auto fs mkdir :www
mpremote connect auto fs cp *.py :
mpremote connect auto fs cp www/index.html www/style.css www/app.js :www/
mpremote connect auto reset
```

W Thonnym: skopiuj zawartość `firmware/` na urządzenie, zachowując podkatalog `www`.

Nic spoza `firmware/` na Pico nie idzie — `cad/` to modele do druku.

## Pierwsze uruchomienie

Bez zapisanego hasła lampka stawia własną sieć:

- SSID **LED-Lampka**, hasło **ledlampka**
- panel: **http://192.168.4.1/**

Podłącz się telefonem, wejdź w zakładkę **WiFi**, wybierz swoją sieć, podaj hasło →
lampka próbuje się połączyć **od razu, bez restartu**, a wynik widać w polu „Stan".
Jeśli się nie uda, pokazuje **dlaczego** („złe hasło", „nie widzę tej sieci"…),
nie traci własnej sieci i panel zostaje dostępny, więc możesz od razu poprawić hasło.

### Gdy lampka nie chce się połączyć

| Komunikat | Co z tym zrobić |
|---|---|
| złe hasło | literówka; hasła WiFi rozróżniają wielkość liter |
| nie widzę tej sieci | **Pico W obsługuje wyłącznie 2,4 GHz** — sieć 5 GHz jest dla niego niewidzialna, nawet jeśli telefon ją widzi. Sprawdź też kod kraju niżej |
| router odrzucił połączenie | filtr adresów MAC albo pełna lista klientów na routerze |
| nie zdążyłem w wyznaczonym czasie | słaby sygnał — spróbuj bliżej routera |
| sieć nie przydzieliła adresu | problem z DHCP na routerze |

**Kod kraju** (zakładka WiFi, domyślnie `PL`) decyduje o dozwolonych kanałach.
Bez niego Pico trzyma się kanałów 1–11, a routery w Polsce potrafią stać na 12 lub 13
— takiej sieci lampka **w ogóle nie zobaczy**, i to wygląda dokładnie jak „nie widzę
tej sieci". Jeśli sieć jest widoczna na telefonie, a lampka jej nie znajduje,
to jest pierwszy podejrzany.

## Jak wejść do panelu nie znając adresu IP

Trzy niezależne drogi — jeśli jedna zawiedzie, zostają dwie:

**1. Nazwa lampki (mDNS): http://lampka.local/**
Nazwę zmienisz w Ustawieniach. Działa bez zaglądania do rutera. iPhone i Mac
obsługują to od zawsze (Bonjour), Windows 10/11 i Android 12+ też. Zastrzeżenie:
wymaga firmware'u z odpowiedzią mDNS — buildy MicroPythona dla Pico W zwykle ją mają,
ale nie sprawdzę tego bez Twojego sprzętu. Po starcie lampka wypisuje na porcie
szeregowym dokładny adres, pod którym się ogłasza.

**2. Własna sieć lampki: http://192.168.4.1/**
Gdy lampka nie ma z czym się połączyć, sama stawia AP `LED-Lampka` — podłączasz
telefon i wchodzisz na `192.168.4.1`. Działa bez rutera i bez nazwy .local.

Opcja *„Trzymaj własną sieć lampki cały czas"* (domyślnie włączona) utrzymuje ten AP
**równolegle** z domowym WiFi — drugie, niezależne wejście do panelu, przydatne tam,
gdzie nie masz dostępu do rutera. Zastrzeżenie: Pico W dzieli jedno radio między oba
interfejsy, więc na niektórych routerach potrafi to rozchwiać połączenie. Jeśli lampka
ma poprawny adres, a panel nie odpowiada — to jeden z podejrzanych, spróbuj wyłączyć.

**3. Panel otwiera się sam po podłączeniu do sieci lampki**
Domyślnie włączone (Ustawienia → *„Otwieraj panel sam po podłączeniu"*). Telefon po
połączeniu z siecią `LED-Lampka` sprawdza dostęp do internetu, a lampka odpowiada na
każde pytanie DNS swoim adresem i odbija zapytanie na panel — system pokazuje go od
razu, jak w hotelowym WiFi.

Działa **wyłącznie w czystym trybie AP**, czyli gdy lampka nie jest w żadnej sieci.
Po wejściu do domowego WiFi serwer DNS się nie uruchamia — odpowiadanie „każda nazwa
= 192.168.4.1" na cudzej sieci zepsułoby internet pozostałym urządzeniom.

**4. Lampka sama pokazuje swój adres**
Po połączeniu z WiFi matryca wyświetla **dwa ostatnie człony** adresu, rozdzielone
poziomą kreską — np. `1`,`7`,`8`, kreska, `1`,`4`,`4` znaczy `192.168.178.144`.
Dwa człony, a nie jeden, bo router potrafi wpuścić lampkę do innej podsieci niż ta,
w której jest Twój telefon — wtedy samo `144` prowadziłoby pod zły adres.

Awaryjnie: **4 kliknięcia** pokazują końcówkę IP na matrycy w dowolnym momencie,
a **3 kliknięcia + przytrzymanie 5 s** czyszczą zapisane WiFi i lampka wraca do
czystego trybu AP pod `192.168.4.1`.

Sygnały po starcie:

| Błysk | Znaczenie |
|---|---|
| słaby niebieski | kod wystartował |
| żółty | łączę się z zapisaną siecią |
| zielony | jest WiFi, potem matryca pokazuje **dwa ostatnie człony IP** |
| dwa niebieskie | tryb AP |
| trzy czerwone | wyjątek w kodzie (szczegóły na porcie szeregowym) |

## Sterowanie dotykiem

| Gest | Efekt |
|---|---|
| **1 klik** | włącz / wyłącz |
| **2 kliki** | następny tryb (gdy zgaszona — zapala) |
| **3 kliki** | poprzedni tryb |
| **4 kliki** | pokaż końcówkę IP na matrycy |
| **przytrzymanie** | jasność — rampa w górę; puszczasz i trzymasz znowu, żeby zejść w dół |
| **2 kliki + przytrzymanie** | szybkość animacji, tak samo naprzemiennie |
| **3 kliki + przytrzymanie 5 s** | zapomnij WiFi i wróć do trybu AP |

Jak to działa w praktyce: pojedynczy klik reaguje po ~0,35 s, bo tyle trwa okno na
dołożenie drugiego kliknięcia — inaczej nie da się odróżnić jednego od dwóch.
Rampa jasności rusza po 0,5 s trzymania i idzie ~4 % na 0,1 s, czyli pełen przejazd
od 1 % do 100 % trwa około 2,5 s. Kierunek przełącza się po każdym puszczeniu, a po
dojściu do końca zakresu następne trzymanie zawsze zawraca. Jasność nie schodzi
poniżej 1 %, żeby lampka nie „zgasła" bez wyłączenia.

Gest kasowania WiFi celowo wymaga trzech kliknięć i dopiero potem 5 s trzymania —
samo długie trzymanie steruje jasnością i nie ma szans przypadkiem wyczyścić sieci.

Jeśli Twój moduł TTP223 ma odwróconą logikę (zworka), przełącz to w panelu w
**Ustawienia → Przycisk i start** — nic nie trzeba przelutowywać.

## Panel WWW

**Animacje** — jasność, szybkość, kolor (paleta + własny picker), siatka trybów.

**Edytor** — pełne narzędzie do pixel artu i animacji klatka po klatce.

*Rysowanie:* siatka 7 × 9 1:1 z ramką, pędzel z paletą, **wypełnianie obszaru**,
**pipeta** (pobiera kolor z siatki), gumka, cofnij/ponów (40 kroków wstecz).
**Duch poprzedniej klatki** pokazuje pod spodem przygaszony poprzedni kadr — bez
tego rysowanie ruchu to zgadywanka. Klik w piksel z kolorem pędzla gasi go; kolor
pociągnięcia ustala się przy pierwszym dotkniętym pikselu, więc przeciągnięcie po
pomalowanym fragmencie go nie zjada, a zaczęte na świecącym pikselu działa jak gumka.

*Klatki:* pasek miniatur, dodaj / duplikuj / przesuń / usuń, **usuń wszystkie**
(z pytaniem o potwierdzenie, cofalne), własny czas każdej klatki w ms,
„ten czas wszystkim".

Pod siatką, w zasięgu kciuka, jest wszystko, czego używa się przy rysowaniu animacji:
strzałki **◀ ▶** do przewijania klatka po klatce ze wskaźnikiem pozycji (`3 / 12`),
przyciski **▶ Podgląd**, **+ klatka**, **duplikuj**, **Cofnij**, **Ponów** oraz
osobny rządek **← ↑ ↓ →** do przesuwania rysunku. Pełne trójkąty przewijają klatki,
cienkie strzałki przesuwają obraz — to celowo różne kształty. Przewijanie klatek
zawija się, bo animacja i tak jest pętlą.

**▶ Podgląd** odtwarza animację na siatce w telefonie, a przy zaznaczonym
*„Podgląd puszczaj też na lampce"* równocześnie na ramce — widzisz wtedy dokładnie
to samo w obu miejscach. Po odznaczeniu podgląd zostaje tylko w telefonie, a lampka
gra dalej swoje. **Stop** wraca do klatki, którą edytowałeś, a lampka do tego, co
pokazywała przed podglądem (o ile w ogóle brała udział). Podgląd niczego nie zmienia
w animacji. Przerwanie go rysowaniem, przewinięciem albo kliknięciem w inną klatkę
zatrzymuje odtwarzanie tam, gdzie jesteś, bez skakania.

*Efekty* — z wyborem zakresu **tej klatki / od tej do końca / wszystkich klatek**:
jasność suwakiem 0–200 % plus szybkie −20 % / +25 %, negatyw, odbarwienie,
nasycenie, kontrast, zabarwienie kolorem pędzla.

*Przekształcenia:* przesuwanie w czterech kierunkach (z zawijaniem), odbicie
poziome i pionowe, obrót 180°.

*Generowanie klatek:* ściemnianie, rozjaśnianie, **przenikanie do następnej klatki**,
miganie, przesuwanie (auto-animacja ruchu w zadanym kierunku), „tam i z powrotem",
odwrócenie kolejności, przyspieszenie i zwolnienie całości ×2.

**Galeria** — zapisane animacje z miniaturami: pokaż na lampce, wczytaj do edytora,
usuń. Niżej **sekwencja przycisku**: lista wszystkich trybów z checkboxami. Zaznaczone
krążą pod dwoma kliknięciami przycisku, odznaczone zostają dostępne z panelu, ale
przycisk je pomija. Domyślnie poza sekwencją jest tylko Kalibracja.

**Ustawienia** — auto-wyłączanie (włącznik + liczba minut; licznik zeruje każde
dotknięcie przycisku i każda zmiana w panelu), nazwa lampki, stały AP i automatyczne
otwieranie panelu, geometria matrycy z kreatorem, logika przycisku, restart.

Kafelek koloru **wyszarza się i blokuje** w trybach, które mają własne kolory —
działa tylko przy „Kolor stały" i „Oddech", żeby nie kręcić suwakiem bez efektu.

**WiFi** — stan, wszystkie adresy pod którymi lampka odpowiada (klikalne), skan sieci,
zapis, „zapomnij sieć".

Ustawienia lądują w `settings.json`, ale zapis na flash jest zbierany i wykonywany
najwyżej raz na 5 s — klikanie przyciskiem nie zajeżdża pamięci.

## Animacje

Stare (przepisane na 7 × 9 z poprawnym mapowaniem): **Tęcza**, **Tęcza z rogu**,
**Śnieg**, **Matrix**, **Kostka**, **Świetliki**, **Kulki z ogonami**.

Nowe, dobrane pod pionową ramkę 7 × 9:

| Tryb | Dlaczego pasuje |
|---|---|
| **Ogień** | algorytm Fire2012 per kolumna — na pionowej ramce wygląda najlepiej z całej listy |
| **Płomień świecy** | ciepłe migotanie, jaśniej u dołu i na środku; tryb „lampka do pokoju" |
| **Zorza polarna** | wolne zielono-błękitne fale, spokojne światło |
| **Plazma** | gładkie przejścia kolorów, klasyk demoscenowy |
| **Iskry** | losowe błyski gasnące wykładniczo |
| **Fajerwerki** | rakieta leci w górę i wybucha — 9 rzędów wysokości robi tu robotę |
| **Bijące serce** | bitmapa 7 × 9 z podwójnym uderzeniem, dobre na prezent |
| **Oddech** | pulsowanie wybranym kolorem |
| **Kolor stały** | zwykła lampka w wybranym kolorze |
| **Kalibracja** | biała kropka wędrująca rzędami + znaczniki rogów |

Czego nie ma i dlaczego: **przewijany tekst** (7 diod szerokości to pół litery — dałoby
się tylko pionowo, mało czytelne), **reakcja na muzykę** (potrzebny moduł mikrofonu,
np. MAX9814 na ADC), **kolory z pogody** (wymaga odpytywania API w tle). Wszystkie trzy
da się dorobić na tej architekturze — animacja to jedna klasa z metodą `step()`.

## Jak dopisać własną animację

W `animations.py` dodaj klasę i wpisz ją do `ANIMS` — panel podchwyci ją sam:

```python
class MojaAnimacja(Anim):
    name = "moja"           # ASCII, identyfikator w API
    label = "Moja animacja" # to widać w panelu
    interval = 60           # ms między krokami przy szybkości 100 %

    def step(self):
        m = self.m
        m.clear()
        m.set(3, 4, 255, 0, 0)   # x, y, r, g, b — (0,0) to lewy górny róg
```

Nie wołaj `m.show()` ani `time.sleep()` — robi to pętla w `lamp.py`. Do dyspozycji
masz `m.clear()`, `fill()`, `set()`, `setc()`, `get()`, `add()`, `fade()`, `scale()`
oraz `m.w`, `m.h`.

## Co było nie tak w starej wersji

1. **Każdy plik animacji tworzył własny obiekt `NeoPixel` na GP0** — było 7 niezależnych
   buforów walczących o ten sam pasek. To dlatego jasność nie działała (komentarz
   „janosc nie dziala" na końcu starego `main.py`): `set_color()` skalowało swój bufor,
   a animacje zaraz nadpisywały diody pełnymi wartościami. Teraz jest **jeden**
   `NeoPixel` i jasność nakładana w jednym miejscu, w `Matrix.show()`.
2. Rozmiar 8 × 8 (64 diody) wpisany na sztywno w 9 plikach — teraz raz w `config.py`.
3. Niespójne mapowanie: część plików liczyła wężykiem, część liniowo. Teraz jedna
   tablica mapowania, konfigurowalna z panelu.
4. `while True` w każdym pliku — nie dało się tego użyć jako biblioteki.
5. Blokujące `time.sleep()` w pętli głównej — przy serwerze WWW to nie do przyjęcia,
   więc całość siedzi na `uasyncio`: animacje, przycisk i panel działają równolegle.
6. Stary `main.py` zapisywał tryb, przepisując `conf.py` jako kod Pythona przy każdej
   zmianie — teraz JSON, zapisywany najwyżej raz na 5 s.
7. `kub rampka.py` uznawał pozycję `[0, 0]` za „pierwsze uruchomienie", więc resetował
   animację przy każdym trafieniu w róg.

## Gdy coś nie działa

**Animacje „szatkują się", lecą w złą stronę, piksele w edytorze zapalają się nie
tam gdzie klikasz** → Ustawienia → Geometria → **Kreator**. Zapala pojedyncze diody po
numerach na taśmie (z pominięciem całego mapowania), pyta w którym rogu się zapaliły
i w którą stronę biegną, i sam wylicza wszystkie trzy ustawienia. Trzy pytania,
bez zgadywania.

Przycisk **Wzór** to sprawdzenie: poprawne mapowanie wygląda jako **biały piksel
w lewym górnym rogu**, **czerwona linia od niego w prawo** wzdłuż górnej krawędzi
i **zielona w dół** wzdłuż lewej. Nic się nie rusza — jeśli widzisz to w innych
miejscach albo poszatkowane, mapowanie jest złe.

**Diody migają losowo, złe kolory** → zasilanie. Sprawdź kondensator, wspólną masę
i przekrój przewodów. Przy 3,3 V na linii danych i 5 V na diodach czasem trzeba
konwertera poziomów albo zasilenia matrycy z 4,5 V.

**Pico się resetuje przy jaśniejszych animacjach** → zasilacz nie wyrabia albo Pico
jest podłączone za matrycą. Prowadź zasilanie gwiazdą od zasilacza.

**Przycisk reaguje odwrotnie / sam się klika** → przełącz logikę w Ustawieniach.
TTP223 potrzebuje płytki masy pod padem i nie lubi luźnego, długiego przewodu do
elektrody.

**Lampka ma adres z WiFi, ale panel nie odpowiada, a przez jej własne AP działa**
→ najpierw porównaj podsieci. Sprawdź w telefonie, jaki adres IP dostał on sam
(Android: Ustawienia → WiFi → szczegóły sieci; iPhone: WiFi → „i" przy nazwie sieci).
Jeśli telefon ma np. `192.168.1.x`, a lampka `192.168.178.x`, to **są w dwóch różnych
sieciach** i nie mają jak się widzieć — pakiety nie mają tamtędy drogi. `lampka.local`
też nie zadziała, bo mDNS jest rozgłoszeniem lokalnym i nie przechodzi między
podsieciami. Najczęstsza przyczyna: wzmacniacz zasięgu albo drugi router, który
tworzy własną sieć za NAT-em. Wtedy albo podłącz oba urządzenia do tej samej sieci,
albo po prostu korzystaj z AP lampki — po to jest.

Druga możliwość przy tych samych objawach to **izolacja klientów** na routerze
(często włączona domyślnie w sieci dla gości): urządzenia mają internet, ale nie
widzą się nawzajem. Szukaj w ustawieniach routera pozycji „izolacja klientów",
„AP isolation" albo „blokuj komunikację między urządzeniami".

**Lampka jest w WiFi, ma adres, ale panel się nie otwiera** → najpewniej masz
włączone *„Trzymaj własną sieć lampki cały czas"*. Jedno radio obsługuje wtedy dwie
sieci naraz i połączenie się rozjeżdża. Wyłącz tę opcję (Ustawienia → Dostęp bez
znania adresu IP) i zrestartuj lampkę.

**Przy rysowaniu telefon przybliża stronę** → nie powinien: dwuklik jest wyłączony
przez `touch-action: manipulation`. Jeśli mimo to przybliża, masz starą wersję
`style.css` — wgraj ją ponownie. Celowe powiększenie dwoma palcami dalej działa.

**Panel wygląda inaczej niż powinien / siatka edytora jest płaska** → stara wersja
plików w pamięci przeglądarki. Pliki panelu są serwowane z `no-cache`, więc wystarczy
odświeżyć stronę; jeśli to nie pomaga, sprawdź, czy wgrałeś **wszystkie trzy** pliki
z `www/`.

**Rano/po kilku godzinach panel przestaje odpowiadać** → dwie najczęstsze
przyczyny, obie zaadresowane w kodzie:

1. **Oszczędzanie energii radia.** Układ CYW43 usypia odbiornik między ramkami
   i gubi pakiety przychodzące — lampka formalnie jest w sieci, wychodzące
   połączenia działają, ale wejść na panel się nie da. Domyślnie **wyłączone**
   (`wifi_powersave: False`, ustawiane przy każdym łączeniu). Kosztuje ~30 mA.
2. **Brak wznawiania połączenia.** Po restarcie routera, wygaśnięciu adresu albo
   zmianie kanału lampka zostawała offline do końca życia. Teraz `netmgr.watchdog`
   sprawdza stan co 20 s i sam się łączy ponownie, zapisując to w logu.

3. **Padnięcie samego nasłuchu HTTP.** W uasyncio zadanie przyjmujące połączenia
   jest zwykłym zadaniem — jeśli rzuci wyjątkiem, ginie po cichu. Animacje chodzą
   dalej, przycisk działa, a serwer po prostu przestaje odbierać. Objaw jest wtedy
   nie do odróżnienia od problemu z WiFi.

   Trzy zabezpieczenia: **dozór nasłuchu** (`Server.supervisor`) co 2 minuty puka
   do własnego portu i po dwóch nieudanych próbach restartuje nasłuch — bez
   restartu lampki i bez gubienia animacji; **limit 6 jednoczesnych połączeń**,
   żeby nie wyczerpać skończonej puli gniazd lwIP; oraz **handler wyjątków pętli
   zdarzeń**, który zapisuje do logu traceback każdego zadania, jakie padło.

   Dozór sam się kalibruje: sprawdza najpierw, czy sonda w ogóle działa na danym
   firmware (pętla zwrotna w lwIP), i jeśli nie — wyłącza się, zamiast restartować
   serwer bez powodu.

Jeśli mimo tego problem wróci, zajrzyj do logu — powie, co się stało i po ilu
godzinach.

### Co czytać w logu

Linia stanu co 5 minut wygląda tak:

```
02:35:11  RAM 138912 B | polaczenia otwarte 0 | obsluzonych 214
```

Trzy liczby rozstrzygają, która hipoteza jest prawdziwa:

| Objaw w logu | Znaczenie |
|---|---|
| RAM systematycznie spada | wyciek pamięci — log pokaże, po ilu godzinach się zaczyna |
| „połączenia otwarte" rośnie i nie wraca do zera | gniazda nie są zwalniane, pula lwIP się kończy |
| „obsłużonych" zamarza, choć wchodzisz na panel | zapytania nie dochodzą — czyli WiFi, nie serwer |
| wpis `ZADANIE PADLO` | coś rzuciło wyjątkiem; traceback mówi dokładnie co |
| wpis `nasluch nie przyjmuje polaczen` | to był serwer, i dozór go podniósł |

### Log

Ustawienia → **Diagnostyka**. Domyślnie włączony zapis do `log.txt` na Pico.
Do pliku idą tylko istotne zdarzenia (start, stan sieci, wznawianie, wolna pamięć
co 5 minut, błędy); pojedyncze wejścia na panel lecą wyłącznie na port szeregowy,
żeby nie zajeżdżać pamięci flash. Plik nie rośnie ponad ~12 kB — po przekroczeniu
starsze wpisy są obcinane.

Każdy wpis ma stempel **czasu od startu** (`gg:mm:ss`), bo Pico nie ma zegara
z baterią. To i tak najważniejsza informacja: po ilu godzinach pracy coś się stało.

Trzy sposoby odczytu:

```bash
mpremote connect auto fs cat :log.txt      # przez USB
```

- w panelu: Ustawienia → Diagnostyka → **Pokaż log**
- na porcie szeregowym na żywo (tam widać też każde zapytanie HTTP)

**Jak wyłączyć:** odznacz *„Zapisuj zdarzenia do pliku log.txt"* w Diagnostyce
i kliknij Zapisz. Port szeregowy dalej będzie pisał — to nic nie kosztuje.
Żeby wyciszyć również log zapytań HTTP na porcie szeregowym, ustaw `LOG = False`
na początku `webserver.py`. Plik usuniesz przez `mpremote connect auto fs rm :log.txt`.

**Nie wiem, jaki ma adres** → patrz „Jak wejść do panelu nie znając adresu IP" wyżej.
Najpewniejsza droga: podłącz telefon do sieci `LED-Lampka` i wejdź na `192.168.4.1`.

**`lampka.local` nie działa** → Twój firmware nie ma odpowiedzi mDNS, albo klient jej
nie obsługuje (część Androidów, przeglądarki w trybie oszczędzania danych). Wpisuj
adres z `http://` na początku, bo bez tego telefon potraktuje to jako zapytanie do
wyszukiwarki. Jeśli i tak nie idzie — zostaje AP `192.168.4.1`, który działa zawsze.

**W nowym miejscu lampka nie widzi WiFi** → sama wróci do trybu AP po ~15 s prób,
więc po prostu podłącz się do `LED-Lampka` i wpisz dane nowej sieci.

## Struktura

```
firmware/        wszystko, co ląduje na Pico
main.py          start: WiFi, sygnały, uruchomienie zadań
config.py        piny, rozmiar matrycy, ustawienia + zapis do settings.json
led_matrix.py    klasa Matrix: jeden NeoPixel, mapowanie wężyka, jasność
animations.py    wszystkie animacje (klasa Anim + rejestr ANIMS)
lamp.py          stan lampki, pętla rysowania, auto-wyłączanie, obsługa gestów
touch.py         TTP223: krótko / przytrzymanie / długie przytrzymanie
netmgr.py        łączenie z WiFi, tryb AP, skanowanie
dns.py           serwer DNS dla captive portalu (panel otwiera się sam)
logger.py        log zdarzeń: port szeregowy + opcjonalnie log.txt
webserver.py     serwer HTTP + API (uasyncio, bez bibliotek zewnętrznych)
frames.py        galeria własnych animacji (katalog anims/)
glyphs.py        czcionka 3×5 do pokazania IP na matrycy
www/             panel: index.html, style.css, app.js
                 (powyższe leżą w firmware/)
cad/             obudowa: pliki STL do druku
```

`settings.json` i katalog `anims/` tworzą się same przy pierwszym zapisie.
Sam program to ~95 kB z ~1,4 MB flasha Pico.

### Dlaczego efekty nie obciążają Pico

Cała obróbka dzieje się **w przeglądarce** i zapieka się w piksele. Na lampkę
trafiają gotowe klatki, a ona robi dokładnie to samo co przy zwykłym obrazku:
jeden `blit()` bufora 189 bajtów na klatkę. Możesz nakładać dowolnie dużo efektów
— koszt po stronie Pico jest zawsze taki sam. Cena tego rozwiązania: efekty są
nieodwracalne (po zejściu do 0 % koloru nie ma skąd go wziąć), dlatego jest
cofanie na 40 kroków.

Trzy zabezpieczenia przed zamuleniem lampki:

1. **Limit 40 klatek** — generatory nie przekraczają go po cichu, tylko dokładają
   tyle, ile się mieści, i mówią o tym wprost.
2. **Limit 64 kB na zapytanie HTTP** — większe ciało dostaje `413` bez próby
   wczytania do RAM-u. Pełna 40-klatkowa animacja waży ~16 kB, więc jest z zapasem.
3. **Do RAM-u wchodzi tylko grająca animacja** — 40 klatek to 7,5 kB buforów.

### Jak trzymane są własne animacje

Każda animacja to osobny plik `anims/<nazwa>.json`, a `anims/index.json` to spis nazw
z miniaturami. Do RAM-u ładowana jest wyłącznie ta animacja, która akurat gra —
przy 24 animacjach po 40 klatek cała galeria w pamięci by się nie zmieściła.
Piksele siedzą jako ciąg hex (`rrggbb` × 63), bo lista liczb w JSON-ie zajmuje
trzy razy więcej. Klatka na urządzeniu to gotowy bufor 189 bajtów wrzucany do matrycy
jednym `blit()`, bez przeliczania piksel po pikselu.

Limity: **40 klatek** na animację, **24 animacje** w galerii, czas klatki **40–10000 ms**.
Panel dostaje te wartości z `/api/state`, więc zmiana ich w `frames.py` od razu
przestawia też podpowiedzi w interfejsie.

## Licencja

**[CC BY-NC 4.0](LICENSE)** — uznanie autorstwa, użycie niekomercyjne.

Możesz zbudować dla siebie, przerobić, opublikować swoją wersję z podaniem źródła,
używać na warsztatach i w edukacji. **Sprzedaż gotowych lampek, zestawów albo
wydrukowanych paneli wymaga pisemnej zgody** autora.

Pamiętaj, że CC BY-NC celowo **nie jest** licencją open source w rozumieniu OSI —
ograniczenie komercyjne jest tu zamierzone. Składniki obce (MicroPython, SDK Pico W,
narzędzia zewnętrzne) mają własne licencje.
