# Maly serwer DNS na potrzeby "captive portal" w trybie AP.
#
# Odpowiada na KAZDE pytanie o adres tym samym IP - adresem lampki. Telefon po
# podlaczeniu sie do sieci sprawdza lacznosc, dostaje nasza strone zamiast
# oczekiwanej odpowiedzi Google/Apple i sam otwiera panel.
import socket

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


def _skip_name(data, i):
    """Przeskakuje nazwe DNS, zwraca pozycje tuz za nia."""
    n = len(data)
    while i < n:
        ln = data[i]
        if ln == 0:
            return i + 1
        if ln & 0xC0 == 0xC0:      # wskaznik kompresji
            return i + 2
        i += 1 + ln
    return n


def build_reply(query, ip_bytes):
    """Buduje odpowiedz z rekordem A. None = zapytanie do zignorowania."""
    if len(query) < 12 or (query[2] & 0x80):   # to juz jest odpowiedz
        return None
    qend = _skip_name(query, 12)
    if qend + 4 > len(query):
        return None
    qtype = (query[qend] << 8) | query[qend + 1]

    head = bytearray(query[:qend + 4])
    head[2] = 0x81            # QR=1, RD=1
    head[3] = 0x80            # RA=1, bez bledu
    head[6] = 0               # ANCOUNT
    head[7] = 1 if qtype == 1 else 0
    head[8] = 0               # NSCOUNT
    head[9] = 0
    head[10] = 0              # ARCOUNT
    head[11] = 0
    if not head[7]:
        # pytanie o cos innego niz adres IPv4 - odpowiadamy "nic nie mam",
        # zeby nie wysylac rekordu A w odpowiedzi np. na AAAA
        return bytes(head)
    # wskaznik na nazwe z pytania, typ A, klasa IN, TTL 30 s, dlugosc 4
    answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x1e\x00\x04"
    return bytes(head) + answer + ip_bytes


async def serve(ip, port=53):
    try:
        ip_bytes = bytes(int(p) for p in ip.split("."))
    except (ValueError, AttributeError):
        print("DNS: dziwny adres", ip)
        return
    if len(ip_bytes) != 4:
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setblocking(False)
        s.bind(("0.0.0.0", port))
    except OSError as e:
        print("DNS: nie moge zajac portu %d (%s)" % (port, e))
        s.close()
        return

    print("DNS: kazde pytanie kieruje na", ip)
    while True:
        try:
            data, addr = s.recvfrom(320)
        except OSError:
            await asyncio.sleep_ms(40)   # nic nie przyszlo
            continue
        try:
            reply = build_reply(data, ip_bytes)
            if reply:
                s.sendto(reply, addr)
        except Exception as e:
            print("DNS:", e)
        await asyncio.sleep_ms(0)
