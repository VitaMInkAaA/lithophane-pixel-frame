# Minimalna czcionka 3x5 - lampka pokazuje na matrycy ostatni czlon swojego IP,
# zeby nie trzeba bylo szukac adresu w routerze ani podlaczac USB.
from time import sleep_ms

FONT = {
    "0": (0b111, 0b101, 0b101, 0b101, 0b111),
    "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b111, 0b001, 0b111, 0b100, 0b111),
    "3": (0b111, 0b001, 0b111, 0b001, 0b111),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001),
    "5": (0b111, 0b100, 0b111, 0b001, 0b111),
    "6": (0b111, 0b100, 0b111, 0b101, 0b111),
    "7": (0b111, 0b001, 0b001, 0b010, 0b010),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111),
    "9": (0b111, 0b101, 0b111, 0b001, 0b001),
}


def draw_char(m, ch, x0, y0, color):
    rows = FONT.get(ch)
    if not rows:
        return
    for dy in range(5):
        row = rows[dy]
        for dx in range(3):
            if row & (1 << (2 - dx)):
                m.setc(x0 + dx, y0 + dy, color)


def flash(m, color, times=1, on_ms=140, off_ms=110):
    for _ in range(times):
        m.fill(*color)
        m.show()
        sleep_ms(on_ms)
        m.clear()
        m.show()
        sleep_ms(off_ms)


def ip_sequence(ip):
    """Znaki do pokazania na matrycy: DWA ostatnie czlony adresu.

    Sam ostatni czlon nie wystarcza - router potrafi dac lampce siec inna niz
    ta, w ktorej siedzi telefon (np. 192.168.178.x zamiast 192.168.1.x).
    Wtedy pojedyncze "144" prowadzi prosto pod zly adres."""
    if not ip:
        return ""
    parts = str(ip).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def draw_sep(m, color=(70, 70, 70)):
    """Kreska rozdzielajaca czlony adresu."""
    m.clear()
    for x in range(1, m.w - 1):
        m.setc(x, m.h // 2, color)


def show_ip(m, ip, color=(0, 90, 255), per=600):
    """Wyswietla cyfry dwoch ostatnich czlonow adresu, rozdzielone kreska."""
    x0 = (m.w - 3) // 2
    y0 = (m.h - 5) // 2
    for ch in ip_sequence(ip):
        if ch == ".":
            draw_sep(m)
            m.show()
            sleep_ms(280)
        else:
            m.clear()
            draw_char(m, ch, x0, y0, color)
            m.show()
            sleep_ms(per)
        m.clear()
        m.show()
        sleep_ms(150)
