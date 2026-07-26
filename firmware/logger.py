# Log zdarzen: na port szeregowy zawsze, do pliku log.txt opcjonalnie.
#
# Pico nie ma zegara z bateria, wiec zamiast daty stemplujemy czasem od startu -
# i tak najwazniejsze jest "po ilu godzinach pracy cos sie stalo".
#
# Do pliku ida TYLKO istotne zdarzenia (siec, pamiec, bledy). Pojedyncze
# zapytania HTTP leca wylacznie na port szeregowy, zeby nie zajezdzac flasha.
import sys
import time

try:
    import uos as os
except ImportError:
    import os

import config

FILE = "log.txt"
MAX_BYTES = 12000        # po przekroczeniu zostawiamy druga polowe

_t0 = time.ticks_ms()


def uptime():
    """Czas od startu jako gg:mm:ss."""
    s = time.ticks_diff(time.ticks_ms(), _t0) // 1000
    if s < 0:
        s = 0
    return "%02d:%02d:%02d" % (s // 3600, (s // 60) % 60, s % 60)


def _trim():
    """Nie pozwalamy plikowi rosnac bez konca."""
    try:
        if os.stat(FILE)[6] < MAX_BYTES:
            return
    except OSError:
        return
    try:
        with open(FILE) as f:
            data = f.read()
        with open(FILE, "w") as f:
            f.write("--- starsze wpisy obciete ---\n")
            f.write(data[-(MAX_BYTES // 2):])
    except (OSError, MemoryError) as e:
        print("log: nie udalo sie obciac pliku:", e)


def log(*parts):
    """Istotne zdarzenie: port szeregowy + plik (jesli wlaczony)."""
    line = uptime() + "  " + " ".join(str(p) for p in parts)
    print(line)
    if not config.settings.get("log_file"):
        return
    try:
        _trim()
        with open(FILE, "a") as f:
            f.write(line + "\n")
    except OSError as e:
        print("log: nie zapisano:", e)


def trace(*parts):
    """Drobnica (np. kazde zapytanie HTTP) - tylko port szeregowy."""
    print(uptime() + "  " + " ".join(str(p) for p in parts))


def read(limit=6000):
    """Ostatnie bajty logu - dla panelu."""
    try:
        size = os.stat(FILE)[6]
        with open(FILE) as f:
            if size > limit:
                f.seek(size - limit)
                f.readline()          # nie zaczynaj od polowy linii
            return f.read()
    except OSError:
        return ""
    except MemoryError:
        return "(log za duzy, odczytaj przez USB)"


def clear():
    try:
        with open(FILE, "w") as f:
            f.write(uptime() + "  log wyczyszczony\n")
        return True
    except OSError as e:
        print("log: nie wyczyszczono:", e)
        return False


def task_error(loop, context):
    """Zapisuje wyjatek, ktory zabil zadanie w tle.

    Bez tego takie zadanie ginie po cichu - i wlasnie tak moze zniknac nasluch
    HTTP: animacje chodza dalej, a serwer po prostu przestaje odbierac.
    Traceback trafia do log.txt, wiec przetrwa noc i restart."""
    exc = context.get("exception")
    if exc is None:
        log("problem w zadaniu:", context.get("message", "?"))
        return
    try:
        import io
        buf = io.StringIO()
        sys.print_exception(exc, buf)
        log("ZADANIE PADLO:\n" + buf.getvalue().strip())
    except Exception:
        log("ZADANIE PADLO:", repr(exc))
