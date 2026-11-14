TSO simulator - izvoz rezultatov (Windows 11, Python 3.10+)

ZAGON
  Dvoklik na start.bat. Prvic naredi okolje in namesti Playwright (potreben internet).
  Uporablja tvoj Chrome ali Edge. Ce nobenega ni: python -m playwright install chromium

UPORABA
  1. "Odpri simulator" - odpre se brskalnik s tsowiki.eu/simulator.
  2. "Pridobi ime avanture" - prebere id izbrane avanture (npr. BountyHunterNew).
     Rezultati in zemljevid se vedno shranita v isto podmapo s tem imenom.
  3. Sam zazenes simulacijo.
  4. "Pridobi rezultate" - najprej sam pritisne "Show more results", nato prebere vrstice
     (stevilo nastavis z "Preberi vrstic") in obdrzi X generalov. Za vsakega generala vzame
     vojsko z najmanj vojaki, ki se vedno zmaga (100%).
     Naslednji general je drug general z naslednjo najmanjso zmagovito vojsko.
  5. "Shrani zemljevid" - JPEG v isto mapo, pomanjsan, s stevilko tabora na sliki.
  6. "Izvozi ZIP" - rezultati/<avantura>/results.json + map.jpg.

OPOMBE
  - Ce je zemljevid ze bil shranjen pod drugim imenom mape, program poisče obstoječo mapo z istim id avanture in pise vanjo.
  - Vec vrstic preberi, ce je najcenejsa zmaga nizje v tabeli simulatorja.
  - Test brez interneta: python tests/test_rank.py
  - Test z brskalnikom: python tests/test_mock.py

SKRIPTA ZA IGRO (mapa igra/)
  user_camp_solutions.js kopiraj v mapo userscripts (zamenjaj staro).
  Tools -> "Camp Solutions" -> "Izberi mapo" (mapa rezultati).
  "Ločeno okno" odpre okno, ki ostane NAD igro tudi ko kliknes v igro, in vanj vstavi zemljevid.
  Na vrhu okna je seznam za celo avanturo: kateri general in koliko katerih enot
  poslati na vsak tabor, da pade. Slike generalov in enot pridejo iz odjemalca.
  Skripto kopiraj v %localappdata%\tso_portable\userscripts in v odjemalcu pritisni UPDATE.
  Ko okno v igri zapres, se odstrani nevidna plast, da lahko spet klikas po igri.
  Pri vsakem taboru je "Skrij" - skrije resitev, ko tabor premagas. Izbira se shrani.
  "Skriti tabori" jih znova pokaze.
  Ce izbira mape ne dela: "Prilepi JSON".

ZEMLJEVID
  Program shrani pravi JPEG (ne WebP) z narisanimi stevilkami taborov.
  V igri je prikaz manjsi. Ce je stara slika WebP, jo shrani znova.
