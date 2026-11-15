# Povzetek pogovora: Raziskovalni dnevnik

Datum: 15. 11. 2026

## Cilj
Aplikacija za pregled raziskav, ki jih delam v različnih AI orodjih (Claude, Grok, Gemini). Za vsako raziskavo bi imel seznam s trenutnim stanjem, časovnico sprememb ter komentarji in opombami.

## Moji odgovori na vprašanja
- Raziskave so večinoma v spletnih vmesnikih AI orodij.
- Za vsako raziskavo želim trenutno stanje, časovnico dopolnitev in sprememb.
- Raziskave dodajam sproti, več jih delam hkrati.
- Računalnik: Windows 11, Device name DESKTOP-GTi14, Intel Core Ultra 9 185H, 32 GB RAM.
- Aplikacija je samo za mene.
- Želim profesionalen videz z možnostjo dopisovanja, shranjevanja komentarjev in opomb.
- Brez omejitev glede shranjevanja podatkov.
- Računi: 3× Claude, 3× Grok (xAI), 1× Gemini.
- Aplikacija naj sama predlaga povzetke. Odločil sem se, da lahko začnem z ročnim vnosom.

## Predlagana rešitev
- **Namizna aplikacija za Windows 11**, lokalna, brez oblaka.
- Podatki v lokalni bazi SQLite.
- **Hibridni pristop (C):** zavihki za vsak račun za pregled in prijavo, branje odprtih pogovorov, rezervni uvoz izvozov.
- Ozadje z osveževanjem na 30 minut. Zavihki se naložijo šele, ko jih odpreš.
- Funkcije: seznam raziskav z iskanjem in filtri, trenutno stanje (ročno popravljivo), časovnica z datumi, komentarji in opombe, povezava na pogovor, izvoz v Markdown ali PDF, varnostna kopija.

## Stroški
- Brez API-ja ni dodatnih stroškov. Povzetke napišeš sam ali prilepiš iz odgovora.
- Lokalni model z Ollama je brezplačen in zaseben.
- Brezplačni nivo API-ja obstaja pri nekaterih ponudnikih, pogoji pa se spreminjajo.

## Tehnologija
- Python je primeren: PySide6 (Qt) za vmesnik, QWebEngineView za spletne vmesnike, sqlite3 za bazo, PyInstaller za .exe.
- Alternativa: Electron (JavaScript).

## Lokalni povzetki z Ollama
- Ollama teče lokalno na `http://localhost:11434`.
- Aplikacija pošlje besedilo pogovora modelu z navodilom za strukturiran izhod (JSON).
- Priporočen model za začetek: **qwen2.5:7b**. Kasneje lahko preklopiš na **qwen2.5:14b**.
- Računalnik ima dovolj RAM-a. Grafične kartice NVIDIA ni, zato bo model tekel na procesorju, počasneje, a uporabno.

## Pomembna opozorila
- Samodejno branje spletnih vmesnikov nekateri ponudniki prepovedujejo. Pogoje je treba preveriti pred gradnjo.
- Spletni vmesniki se pogosto spreminjajo, zato bo branje občasno treba popraviti.
- Google morda blokira prijavo v vgrajenih oknih.
- Pogovori lahko vsebujejo občutljive podatke, zato shranjujem le tisto, kar izberem.

## Predlagane faze
1. **Faza 1:** aplikacija z enim zavihkom, ročni vnos, povzetki, seznam, komentarji, lokalna baza.
2. **Faza 2:** vsi računi, samodejno zaznavanje novih pogovorov, časovnica sprememb.
3. **Faza 3:** izvoz v PDF, uvoz izvozov, varnostne kopije, sistemska vrstica.

## Naslednji koraki
1. Namestiti Ollama za Windows in zagnati `ollama pull qwen2.5:7b`.
2. Potrditi, ali faza 1 ustreza, nato napisati Python kodo za povezavo z Ollama in shranjevanje povzetkov.

## Odprta vprašanja
- Preveriti pogoje uporabe za Claude, Grok in Gemini glede samodejnega branja.
- Stanje kredita na računu Claude preveriti v nastavitvah ali na support.claude.com.
