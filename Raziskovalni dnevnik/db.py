"""Lokalna baza SQLite za Raziskovalni dnevnik."""
import sqlite3
from datetime import datetime
from pathlib import Path

VIRI = ["Claude", "Grok", "Gemini", "Drugo"]
STATUSI = ["aktivna", "čakajoča", "zaključena"]

DB_MAPA = Path.home() / "RaziskovalniDnevnik"
DB_POT = DB_MAPA / "dnevnik.db"

SHEMA = """
CREATE TABLE IF NOT EXISTS raziskave (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naslov TEXT NOT NULL,
    vir TEXT NOT NULL,
    povezava TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'aktivna',
    trenutno_stanje TEXT NOT NULL DEFAULT '',
    ustvarjeno TEXT NOT NULL,
    posodobljeno TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dogodki (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raziskava_id INTEGER NOT NULL REFERENCES raziskave(id) ON DELETE CASCADE,
    cas TEXT NOT NULL,
    tip TEXT NOT NULL,
    opis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS komentarji (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raziskava_id INTEGER NOT NULL REFERENCES raziskave(id) ON DELETE CASCADE,
    cas TEXT NOT NULL,
    besedilo TEXT NOT NULL
);
"""


def zdaj():
    """Trenutni čas v obliki ISO, da se pravilno razvršča."""
    return datetime.now().isoformat(timespec="seconds")


def lepo(iso):
    """Pretvori ISO čas v obliko dd.mm.yyyy HH:MM za prikaz."""
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return iso or ""


class Shramba:
    def __init__(self, pot=DB_POT):
        pot.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(pot)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SHEMA)

    def _izvedi(self, sql, parametri=()):
        with self.db:
            return self.db.execute(sql, parametri)

    # Raziskave
    def seznam(self, iskanje="", vir=None):
        sql = "SELECT * FROM raziskave WHERE (naslov LIKE ? OR trenutno_stanje LIKE ?)"
        vzorec = f"%{iskanje}%"
        parametri = [vzorec, vzorec]
        if vir:
            sql += " AND vir = ?"
            parametri.append(vir)
        sql += " ORDER BY posodobljeno DESC, id DESC"
        return [dict(r) for r in self.db.execute(sql, parametri)]

    def dobi(self, rid):
        vrstica = self.db.execute("SELECT * FROM raziskave WHERE id = ?", (rid,)).fetchone()
        return dict(vrstica) if vrstica else None

    def dodaj(self, naslov, vir, povezava=""):
        t = zdaj()
        cur = self._izvedi(
            "INSERT INTO raziskave (naslov, vir, povezava, ustvarjeno, posodobljeno) "
            "VALUES (?, ?, ?, ?, ?)",
            (naslov, vir, povezava, t, t),
        )
        return cur.lastrowid

    def posodobi_podatke(self, rid, naslov, vir, povezava, status):
        self._izvedi(
            "UPDATE raziskave SET naslov = ?, vir = ?, povezava = ?, status = ?, posodobljeno = ? "
            "WHERE id = ?",
            (naslov, vir, povezava, status, zdaj(), rid),
        )

    def nastavi_stanje(self, rid, stanje, tip, opis):
        """Shrani novo trenutno stanje in zapiše dogodek v časovnico."""
        t = zdaj()
        with self.db:
            self.db.execute(
                "UPDATE raziskave SET trenutno_stanje = ?, posodobljeno = ? WHERE id = ?",
                (stanje, t, rid),
            )
            self.db.execute(
                "INSERT INTO dogodki (raziskava_id, cas, tip, opis) VALUES (?, ?, ?, ?)",
                (rid, t, tip, opis),
            )

    def izbrisi(self, rid):
        self._izvedi("DELETE FROM raziskave WHERE id = ?", (rid,))

    # Časovnica
    def dodaj_dogodek(self, rid, tip, opis):
        self._izvedi(
            "INSERT INTO dogodki (raziskava_id, cas, tip, opis) VALUES (?, ?, ?, ?)",
            (rid, zdaj(), tip, opis),
        )

    def dogodki(self, rid):
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM dogodki WHERE raziskava_id = ? ORDER BY cas DESC, id DESC", (rid,)
            )
        ]

    # Komentarji
    def dodaj_komentar(self, rid, besedilo):
        self._izvedi(
            "INSERT INTO komentarji (raziskava_id, cas, besedilo) VALUES (?, ?, ?)",
            (rid, zdaj(), besedilo),
        )

    def komentarji(self, rid):
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM komentarji WHERE raziskava_id = ? ORDER BY cas DESC, id DESC", (rid,)
            )
        ]

    def izbrisi_komentar(self, kid):
        self._izvedi("DELETE FROM komentarji WHERE id = ?", (kid,))
