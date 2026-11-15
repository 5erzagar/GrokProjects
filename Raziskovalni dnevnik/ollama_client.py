"""Povezava z lokalnim modelom v Ollama (http://localhost:11434)."""
import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:7b"          # po potrebi zamenjaj, npr. "qwen2.5:14b"
NAJVEC_ZNAKOV = 24000         # daljša besedila se odrežejo
TIMEOUT_S = 600               # na procesorju lahko povzemanje traja nekaj minut

NAVODILO = (
    "Iz spodnjega pogovora izlušči stanje raziskave. Odgovori samo z JSON objektom "
    "s temi ključi:\n"
    '"trenutno_stanje": kratek povzetek v 3 do 6 stavkih (niz),\n'
    '"kljucne_ugotovitve": seznam nizov,\n'
    '"odprta_vprasanja": seznam nizov,\n'
    '"viri": seznam nizov (imena virov ali povezav, omenjenih v pogovoru).\n'
    "Piši v slovenščini. Če podatka ni v pogovoru, vrni prazen niz ali prazen seznam. "
    "Ne dodajaj ničesar izven JSON objekta.\n\n"
    "POGOVOR:\n"
)


class OllamaNapaka(Exception):
    """Napaka pri komunikaciji z Ollama, sporočilo je namenjeno uporabniku."""


def preveri_dostop(timeout=2):
    """Vrne True, če Ollama teče in odgovarja."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=timeout) as odgovor:
            return odgovor.status == 200
    except (urllib.error.URLError, OSError):
        return False


def povzemi(besedilo):
    """Pošlje pogovor modelu in vrne slovar s ključi trenutno_stanje, kljucne_ugotovitve, ..."""
    besedilo = besedilo[:NAJVEC_ZNAKOV]
    telo = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": NAVODILO + besedilo}],
        "stream": False,
        "format": "json",
        "options": {"num_ctx": 8192, "temperature": 0.2},
    }).encode("utf-8")
    zahteva = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=telo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(zahteva, timeout=TIMEOUT_S) as odgovor:
            podatki = json.loads(odgovor.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OllamaNapaka(
            f"Ollama je vrnila napako {e.code}. Ali je model naložen? "
            f"Zaženi: ollama pull {MODEL}"
        )
    except OSError:
        raise OllamaNapaka(
            "Ollama ni dosegljiva ali je predolgo odgovarjala. "
            "Preveri, ali teče (ikona v sistemski vrstici)."
        )

    vsebina = podatki.get("message", {}).get("content", "")
    try:
        rezultat = json.loads(vsebina)
    except json.JSONDecodeError:
        raise OllamaNapaka("Model ni vrnil veljavnega JSON-a. Poskusi znova.")
    if not isinstance(rezultat, dict):
        raise OllamaNapaka("Model ni vrnil pričakovane oblike. Poskusi znova.")
    return rezultat
