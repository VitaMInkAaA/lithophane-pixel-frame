# Matryca 7 x 9 - jeden wspolny bufor i jedno mapowanie pikseli.
#
# W calym projekcie jest DOKLADNIE JEDEN obiekt NeoPixel. Animacje rysuja do
# bufora logicznego we wspolrzednych (x, y), gdzie:
#   x = 0 to lewa krawedz, y = 0 to GORNA krawedz (patrzac na ramke z przodu)
# Dopiero show() przelicza to na fizyczne indeksy diod i nanosi jasnosc.
import machine
import neopixel
from config import LED_PIN, WIDTH, HEIGHT, LED_COUNT


class Matrix:
    def __init__(self, settings):
        self.w = WIDTH
        self.h = HEIGHT
        self.n = LED_COUNT
        self.s = settings
        self.np = neopixel.NeoPixel(machine.Pin(LED_PIN), self.n)
        self.buf = bytearray(self.n * 3)   # obraz logiczny, zawsze pelna jasnosc
        self.map = [0] * self.n            # logiczny indeks -> fizyczna dioda
        self.remap()

    # ---------------------------------------------------------------- mapowanie
    def remap(self):
        """Przelicza tablice mapowania z ustawien geometrii.
        Domyslnie: origin=BR, rzedami, wezykiem - czyli dioda 0 jest w prawym
        dolnym rogu, pasek idzie w lewo, potem wraca w prawo rzedem wyzej."""
        s = self.s
        origin = s.get("origin", "BR")
        by_rows = s.get("rows", True)
        snake = s.get("serpentine", True)
        from_top = origin[0] == "T"
        from_left = origin[1] == "L"

        for y in range(self.h):
            for x in range(self.w):
                # px, py = wspolrzedne liczone od rogu startowego paska
                px = x if from_left else self.w - 1 - x
                py = y if from_top else self.h - 1 - y
                if by_rows:
                    col = px
                    if snake and (py & 1):
                        col = self.w - 1 - col
                    idx = py * self.w + col
                else:
                    row = py
                    if snake and (px & 1):
                        row = self.h - 1 - row
                    idx = px * self.h + row
                self.map[y * self.w + x] = idx

    # ---------------------------------------------------------------- rysowanie
    def clear(self):
        buf = self.buf
        for i in range(len(buf)):
            buf[i] = 0

    def fill(self, r, g, b):
        buf = self.buf
        for i in range(0, len(buf), 3):
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b

    def set(self, x, y, r, g, b):
        if 0 <= x < self.w and 0 <= y < self.h:
            j = (y * self.w + x) * 3
            buf = self.buf
            buf[j] = r if r < 256 else 255
            buf[j + 1] = g if g < 256 else 255
            buf[j + 2] = b if b < 256 else 255

    def setc(self, x, y, c):
        self.set(x, y, c[0], c[1], c[2])

    def blit(self, data):
        """Wrzuca gotowa klatke RGB prosto do bufora - uzywane przez wlasne
        animacje z galerii, zeby nie przeliczac pikseli po jednym."""
        n = len(self.buf)
        if len(data) == n:
            self.buf[:] = data
        else:
            self.clear()
            k = n if len(data) > n else len(data)
            self.buf[0:k] = data[0:k]

    def get(self, x, y):
        j = (y * self.w + x) * 3
        buf = self.buf
        return (buf[j], buf[j + 1], buf[j + 2])

    def add(self, x, y, r, g, b):
        """Dodaje kolor z ograniczeniem do 255 - do nakladajacych sie efektow."""
        if 0 <= x < self.w and 0 <= y < self.h:
            j = (y * self.w + x) * 3
            buf = self.buf
            v = buf[j] + r
            buf[j] = 255 if v > 255 else v
            v = buf[j + 1] + g
            buf[j + 1] = 255 if v > 255 else v
            v = buf[j + 2] + b
            buf[j + 2] = 255 if v > 255 else v

    def fade(self, amount):
        """Odejmuje stala wartosc od kazdego kanalu - liniowe gasniecie."""
        buf = self.buf
        for i in range(len(buf)):
            v = buf[i] - amount
            buf[i] = v if v > 0 else 0

    def scale(self, num, den=256):
        """Mnozy caly obraz przez num/den - wykladnicze gasniecie smug."""
        buf = self.buf
        for i in range(len(buf)):
            buf[i] = buf[i] * num // den

    # ------------------------------------------------------------------- wyjscie
    def show(self):
        b = self.s.get("brightness", 40)
        if b > 100:
            b = 100
        elif b < 0:
            b = 0
        npx = self.np
        buf = self.buf
        m = self.map
        if b >= 100:
            for i in range(self.n):
                j = i * 3
                npx[m[i]] = (buf[j], buf[j + 1], buf[j + 2])
        else:
            for i in range(self.n):
                j = i * 3
                npx[m[i]] = (buf[j] * b // 100, buf[j + 1] * b // 100, buf[j + 2] * b // 100)
        npx.write()

    def blackout(self):
        """Gasi diody nie ruszajac bufora - lampka pamieta co wyswietlala."""
        self.np.fill((0, 0, 0))
        self.np.write()
