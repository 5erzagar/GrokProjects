# Raziskovalni dnevnik: navodila

Lokalna aplikacija za Windows 11. Podatki ostanejo na tvojem računalniku. Povzetke pripravlja lokalni model v Ollama, zato nimaš dodatnih stroškov.

## 1. Namestitev

1. Namesti **Python 3.11 ali novejši** z https://www.python.org/downloads/. Med namestitvijo obkljukaj **Add python.exe to PATH**.
2. Odpri **PowerShell** v mapi *Raziskovalni dnevnik* (v File Explorerju v naslovno vrstico vpiši `powershell` in pritisni Enter).
3. Zaženi namestitveno skripto:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install_ollama.ps1
   ```

   Skripta namesti Ollama (prek `winget`), preveri, ali Ollama teče, prenese model `qwen2.5:7b` (približno 4,7 GB) in namesti knjižnico PySide6.

Če `winget` ni na voljo, Ollama namesti ročno z https://ollama.com/download in nato znova zaženi skripto.

## 2. Zagon

```powershell
python main.py
```

Ob zagonu se v spodnji vrstici prikaže, ali je Ollama dosegljiva.

## 3. Uporaba

- **Nova raziskava:** klikni *+ Nova raziskava*, vnesi naslov, izberi vir (Claude, Grok, Gemini, Drugo) in po želji povezavo.
- **Povzetek:** odpri raziskavo, klikni *Povzemi z Ollama*, v okno prilepi besedilo pogovora iz spletnega vmesnika in klikni *Povzemi*. Počakaj, da model konča (na procesorju lahko traja nekaj minut). Pregledaj in po potrebi popravi polja ter klikni *Shrani kot novo stanje*.
- **Ročno stanje:** v polje *Trenutno stanje* napiši ali popravi besedilo in klikni *Shrani stanje*.
- **Časovnica:** vsaka sprememba stanja, povzetek ali sprememba statusa se zapiše z datumom in uro.
- **Komentarji:** v spodnjem desnem delu dodajaš opombe (Enter ali gumb *Dodaj*). Izbrani komentar lahko izbrišeš.
- **Iskanje in filter:** zgoraj levo išči po naslovu in stanju ali filtriraj po viru.

Besedila pogovorov se ne shranjujejo, shranjeno je le povzeto stanje. Če želiš original, ga shrani kot komentar ali v svojo datoteko.

## 4. Kje so podatki

Baza je v datoteki `C:\Users\<tvoje_ime>\RaziskovalniDnevnik\dnevnik.db`. Varnostno kopijo naredi tako, da datoteko kopiraš na drugo mesto (dokler aplikacija ni zaprta).

## 5. Sprememba modela

V datoteki `ollama_client.py` spremeni vrstico:

```python
MODEL = "qwen2.5:7b"
```

na `"qwen2.5:14b"` (boljša kakovost, počasneje). Novi model najprej prenesi z ukazom `ollama pull qwen2.5:14b`.

## 6. Pogoste težave

| Težava | Rešitev |
|---|---|
| Ob povzemanju piše, da Ollama ni dosegljiva | Odpri aplikacijo Ollama iz menija Start ali zaženi `ollama serve` v PowerShellu. |
| Napaka 404 ali "model not found" | Prenesi model: `ollama pull qwen2.5:7b`. |
| Model ni vrnil veljavnega JSON-a | Poskusi znova. Če se ponavlja, uporabi večji model (14b). |
| Povzemanje traja zelo dolgo | To je normalno na procesorju. Krajši pogovor ali manjši model pospeši. |
| `python` ni prepoznan | Ponovno namesti Python in obkljukaj *Add python.exe to PATH*. |

Besedilo se pri povzemanju omeji na prvih 24.000 znakov. Dolgi pogovori se zato lahko ne povzamejo v celoti. Če se to zgodi, prilepi samo pomembnejši del.

## 7. Kaj še ne vsebuje prva različica

Samodejnega branja spletnih vmesnikov, izvoza v PDF/Markdown, samodejnih varnostnih kopij, temne teme in sistemske vrstice še ni. To so naslednje faze.
