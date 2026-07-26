# Animacje dla ramki 7 x 9 (63 diody).
#
# Kazda animacja tylko RYSUJE do bufora matrycy. Wywolanie show() i odmierzanie
# czasu robi petla w lamp.py - dzieki temu jasnosc i szybkosc dzialaja globalnie
# dla wszystkich efektow.
import math
import random

import config

# --------------------------------------------------------------------- narzedzia

# Tablica sinusa 0..255 - w MicroPythonie taniej niz math.sin w petli po pikselach
_SIN = bytes(int(127.5 + 127.4 * math.sin(6.283185 * i / 256)) for i in range(256))


def isin(i):
    return _SIN[i & 255]


def wheel(pos):
    """Pozycja 0..255 -> kolor teczy."""
    pos &= 255
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def heat_color(t):
    """Temperatura 0..255 -> kolor ognia (czarny -> czerwony -> zolty -> bialy)."""
    t192 = (t * 191) >> 8
    ramp = (t192 & 0x3F) << 2
    if t192 & 0x80:
        return (255, 255, ramp)
    if t192 & 0x40:
        return (255, ramp, 0)
    return (ramp, 0, 0)


class Anim:
    name = "anim"
    label = "Animacja"
    interval = 60         # ms miedzy krokami przy szybkosci 100%
    uses_color = False    # czy tryb korzysta z koloru wybranego w panelu

    def __init__(self, m, s):
        self.m = m
        self.s = s

    def step(self):
        pass


# ------------------------------------------------------------- tryby spokojne

class Kolor(Anim):
    name = "kolor"
    label = "Kolor stały"
    interval = 300
    uses_color = True

    def step(self):
        self.m.fill(*config.color_rgb())


class Oddech(Anim):
    name = "oddech"
    label = "Oddech"
    interval = 35
    uses_color = True

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.p = 0

    def step(self):
        r, g, b = config.color_rgb()
        v = 25 + isin(self.p) * 230 // 255
        self.m.fill(r * v >> 8, g * v >> 8, b * v >> 8)
        self.p = (self.p + 2) & 255


class Swieca(Anim):
    name = "swieca"
    label = "Płomień świecy"
    interval = 70

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.lvl = 200

    def step(self):
        m = self.m
        self.lvl += random.randint(-45, 45)
        if self.lvl > 255:
            self.lvl = 255
        elif self.lvl < 100:
            self.lvl = 100
        cx = m.w // 2
        for y in range(m.h):
            for x in range(m.w):
                # jasniej u dolu i na srodku, plus drobne migotanie
                v = self.lvl - y * 9 - abs(x - cx) * 7 + random.randint(-12, 12)
                if v < 0:
                    v = 0
                m.set(x, y, v, v * 45 // 100, v * 7 // 100)


class Ogien(Anim):
    name = "ogien"
    label = "Ogień"
    interval = 55
    COOLING = 30
    SPARKING = 130

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.heat = [[0] * m.h for _ in range(m.w)]

    def step(self):
        m = self.m
        h = m.h
        cool_max = (self.COOLING * 10) // h + 2
        for x in range(m.w):
            col = self.heat[x]
            for i in range(h):                       # 1. chlodzenie
                v = col[i] - random.randint(0, cool_max)
                col[i] = v if v > 0 else 0
            for i in range(h - 1, 1, -1):            # 2. cieplo unosi sie w gore
                col[i] = (col[i - 1] + col[i - 2] + col[i - 2]) // 3
            if random.getrandbits(8) < self.SPARKING:  # 3. iskra u podstawy
                i = random.randint(0, 2)
                v = col[i] + random.randint(160, 255)
                col[i] = 255 if v > 255 else v
            for i in range(h):                       # 4. rysowanie (i=0 to dol)
                m.setc(x, h - 1 - i, heat_color(col[i]))


class Zorza(Anim):
    name = "zorza"
    label = "Zorza polarna"
    interval = 70

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.t = 0

    def step(self):
        m = self.m
        t = self.t
        for x in range(m.w):
            ph = isin(x * 18 + t) >> 2
            hue = 100 + ((isin(x * 12 + t) - 128) >> 3)
            c = wheel(hue)
            for y in range(m.h):
                v = isin(y * 26 + t * 2 + ph * 4)
                v = v * v >> 8                       # kontrast, ciemne jeszcze ciemniej
                m.set(x, y, c[0] * v >> 8, c[1] * v >> 8, c[2] * v >> 8)
        self.t = (t + 3) & 0x3FFF


class Plazma(Anim):
    name = "plazma"
    label = "Plazma"
    interval = 55

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.t = 0

    def step(self):
        m = self.m
        t = self.t
        for y in range(m.h):
            for x in range(m.w):
                v = isin(x * 26 + t) + isin(y * 22 - t) + isin((x + y) * 18 + (t >> 1))
                m.setc(x, y, wheel(v // 3 + (t >> 1)))
        self.t = (t + 4) & 0x3FFF


# ---------------------------------------------------------------------- tecze

class Tecza(Anim):
    name = "tecza"
    label = "Tęcza"
    interval = 50

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.p = 0

    def step(self):
        m = self.m
        for y in range(m.h):
            c = wheel(self.p + y * 24)
            for x in range(m.w):
                m.setc(x, y, c)
        self.p = (self.p + 3) & 255


class TeczaSkos(Anim):
    name = "tecza_skos"
    label = "Tęcza z rogu"
    interval = 50

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.p = 0

    def step(self):
        m = self.m
        for y in range(m.h):
            for x in range(m.w):
                m.setc(x, y, wheel(self.p + (x + (m.h - 1 - y)) * 16))
        self.p = (self.p + 3) & 255


# ------------------------------------------------------------ efekty opadajace

class Snieg(Anim):
    name = "snieg"
    label = "Śnieg"
    interval = 110

    def step(self):
        m = self.m
        for y in range(m.h - 1, 0, -1):          # przesuniecie calego obrazu w dol
            for x in range(m.w):
                m.setc(x, y, m.get(x, y - 1))
        for x in range(m.w):                     # nowe platki w gornym rzedzie
            if random.getrandbits(7) < 15:
                m.set(x, 0, 210, 225, 255)
            else:
                m.set(x, 0, 0, 0, 0)


class MatrixRain(Anim):
    name = "matrix"
    label = "Matrix"
    interval = 85

    def step(self):
        m = self.m
        for y in range(m.h - 1, 0, -1):          # ogon gasnie podczas opadania
            for x in range(m.w):
                g = m.get(x, y - 1)[1]
                m.set(x, y, 0, g * 62 // 100, 0)
        for x in range(m.w):
            m.set(x, 0, 0, 255 if random.getrandbits(4) < 3 else 0, 0)


# ------------------------------------------------------------- ruchome obiekty

class Iskry(Anim):
    name = "iskry"
    label = "Iskry"
    interval = 45

    def step(self):
        m = self.m
        m.scale(225)
        for _ in range(2):
            if random.getrandbits(3) < 5:
                m.setc(random.randint(0, m.w - 1), random.randint(0, m.h - 1),
                       wheel(random.getrandbits(8)))


class Swietliki(Anim):
    name = "swietliki"
    label = "Świetliki"
    interval = 60
    COUNT = 12

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.px = []
        self.py = []
        self.vx = []
        self.vy = []
        self.col = []
        self.target = []
        for _ in range(self.COUNT):
            self.px.append(random.randint(0, (m.w - 1) * 10))
            self.py.append(random.randint(0, (m.h - 1) * 10))
            self.vx.append(random.randint(-8, 8))
            self.vy.append(random.randint(-8, 8))
            self.col.append([255, 255, 255])
            self.target.append(wheel(random.getrandbits(8)))
        self.tick = 0

    def step(self):
        m = self.m
        m.clear()
        self.tick = (self.tick + 1) % 20
        for i in range(self.COUNT):
            if self.tick == 0:                   # co 20 krokow lekka zmiana kursu
                self.vx[i] = max(-16, min(16, self.vx[i] + random.randint(-4, 4)))
                self.vy[i] = max(-16, min(16, self.vy[i] + random.randint(-4, 4)))
            self.px[i] += self.vx[i]
            self.py[i] += self.vy[i]
            if self.px[i] < 0:                   # w poziomie zawijanie
                self.px[i] += m.w * 10
            elif self.px[i] >= m.w * 10:
                self.px[i] -= m.w * 10
            if self.py[i] < 0:                   # w pionie odbicie
                self.py[i] = 0
                self.vy[i] = -self.vy[i]
            elif self.py[i] > (m.h - 1) * 10:
                self.py[i] = (m.h - 1) * 10
                self.vy[i] = -self.vy[i]

            c = self.col[i]                      # plynne przejscie do koloru docelowego
            t = self.target[i]
            near = True
            for k in range(3):
                d = t[k] - c[k]
                if d > 4 or d < -4:
                    near = False
                c[k] += d // 6
            if near:
                self.target[i] = wheel(random.getrandbits(8))
            m.add(self.px[i] // 10, self.py[i] // 10, c[0], c[1], c[2])


class Kulki(Anim):
    name = "kulki"
    label = "Kulki z ogonami"
    interval = 60
    COUNT = 4

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.b = []
        for _ in range(self.COUNT):
            self.b.append([
                random.randint(0, (m.w - 1) * 10),
                random.randint(0, (m.h - 1) * 10),
                random.choice((-12, -8, 8, 12)),
                random.choice((-12, -8, 8, 12)),
                wheel(random.getrandbits(8)),
            ])

    def step(self):
        m = self.m
        m.scale(150)                              # smugi
        for b in self.b:
            b[0] += b[2]
            b[1] += b[3]
            if b[0] < 0:
                b[0] = 0
                b[2] = -b[2]
            elif b[0] > (m.w - 1) * 10:
                b[0] = (m.w - 1) * 10
                b[2] = -b[2]
            if b[1] < 0:
                b[1] = 0
                b[3] = -b[3]
            elif b[1] > (m.h - 1) * 10:
                b[1] = (m.h - 1) * 10
                b[3] = -b[3]
            m.setc(b[0] // 10, b[1] // 10, b[4])


class Kostka(Anim):
    name = "kostka"
    label = "Kostka"
    interval = 110

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.size = 2
        self.x = (m.w - self.size) * 10 // 2
        self.y = (m.h - self.size) * 10 // 2
        self.vx = random.choice((-9, -6, 6, 9))
        self.vy = random.choice((-9, -6, 6, 9))
        self.col = wheel(random.getrandbits(8))

    def step(self):
        m = self.m
        maxx = (m.w - self.size) * 10
        maxy = (m.h - self.size) * 10
        bounced = False
        self.x += self.vx
        self.y += self.vy
        if self.x < 0:
            self.x = 0
            self.vx = -self.vx
            bounced = True
        elif self.x > maxx:
            self.x = maxx
            self.vx = -self.vx
            bounced = True
        if self.y < 0:
            self.y = 0
            self.vy = -self.vy
            bounced = True
        elif self.y > maxy:
            self.y = maxy
            self.vy = -self.vy
            bounced = True
        if bounced:
            self.col = wheel(random.getrandbits(8))
        m.clear()
        x0 = self.x // 10
        y0 = self.y // 10
        for dy in range(self.size):
            for dx in range(self.size):
                m.setc(x0 + dx, y0 + dy, self.col)


class Fajerwerki(Anim):
    name = "fajerwerki"
    label = "Fajerwerki"
    interval = 75

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.reset()

    def reset(self):
        m = self.m
        self.x = random.randint(1, m.w - 2)
        self.y = m.h - 1
        self.top = random.randint(1, 3)
        self.col = wheel(random.getrandbits(8))
        self.boom = False
        self.r = 0

    def step(self):
        m = self.m
        m.scale(150)
        if not self.boom:
            m.set(self.x, self.y, 255, 220, 130)
            self.y -= 1
            if self.y <= self.top:
                self.boom = True
        else:
            r = self.r
            c = self.col
            for dy in range(-r, r + 1):           # romb - tanie "kolo" na 7x9
                dx = r - abs(dy)
                m.add(self.x + dx, self.y + dy, c[0], c[1], c[2])
                if dx:
                    m.add(self.x - dx, self.y + dy, c[0], c[1], c[2])
            self.r += 1
            if self.r > 5:
                self.reset()


class Serce(Anim):
    name = "serce"
    label = "Bijące serce"
    interval = 60
    # 7 bitow na rzad, bit 6 = lewa krawedz
    SHAPE = (0b0000000,
             0b0110110,
             0b1111111,
             0b1111111,
             0b1111111,
             0b0111110,
             0b0011100,
             0b0001000,
             0b0000000)
    BEAT = (255, 205, 160, 120, 100, 255, 215, 170, 135, 110,
            95, 85, 78, 72, 68, 65, 63, 62, 61, 60, 60, 60)

    def __init__(self, m, s):
        Anim.__init__(self, m, s)
        self.i = 0

    def step(self):
        m = self.m
        v = self.BEAT[self.i]
        self.i = (self.i + 1) % len(self.BEAT)
        r = v
        g = v * 12 // 100
        b = v * 18 // 100
        for y in range(m.h):
            row = self.SHAPE[y] if y < len(self.SHAPE) else 0
            for x in range(m.w):
                if row & (1 << (m.w - 1 - x)):
                    m.set(x, y, r, g, b)
                else:
                    m.set(x, y, 0, 0, 0)


# ------------------------------------------------------- kalibracja i wlasne

class Kalibracja(Anim):
    """Nieruchomy wzor do sprawdzenia mapowania. Poprawnie wyglada tak:
         - BIALY pojedynczy piksel w lewym GORNYM rogu
         - CZERWONA linia od niego w PRAWO, wzdluz gornej krawedzi
         - ZIELONA linia od niego w DOL, wzdluz lewej krawedzi
    Cokolwiek innego (linie w innych miejscach, poszatkowane co drugi rzad)
    znaczy, ze ustawienia geometrii sa zle - patrz kreator w panelu."""
    name = "kalibracja"
    label = "Kalibracja"
    interval = 500

    def step(self):
        m = self.m
        m.clear()
        for x in range(1, m.w):
            m.set(x, 0, 120, 0, 0)
        for y in range(1, m.h):
            m.set(0, y, 0, 120, 0)
        m.set(0, 0, 255, 255, 255)


class WlasnaAnimacja(Anim):
    """Animacja z galerii: klatki rysowane w panelu, kazda z wlasnym czasem.
    Leci w kolko. Pojedynczy obrazek to po prostu animacja o jednej klatce."""
    name = "wlasna"
    label = "Własna"
    interval = 300

    def __init__(self, m, s, frames):
        Anim.__init__(self, m, s)
        self.frames = frames or [{"px": bytearray(m.n * 3), "ms": 500}]
        self.i = 0
        self.interval = self.frames[0]["ms"]

    def step(self):
        fr = self.frames[self.i]
        self.m.blit(fr["px"])
        # petla rysowania czyta interval po kazdym kroku, wiec kazda klatka
        # moze wisiec inaczej dlugo
        self.interval = fr["ms"]
        self.i = (self.i + 1) % len(self.frames)


ANIMS = (Kolor, Oddech, Swieca, Ogien, Zorza, Plazma, Tecza, TeczaSkos,
         Snieg, MatrixRain, Iskry, Swietliki, Kulki, Kostka, Fajerwerki,
         Serce, Kalibracja)


def by_name(name):
    for cls in ANIMS:
        if cls.name == name:
            return cls
    return None
