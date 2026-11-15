"""Raziskovalni dnevnik: pregled raziskav iz AI orodij (Claude, Grok, Gemini)."""
import sys

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db import STATUSI, VIRI, Shramba, lepo
from ollama_client import MODEL, OllamaNapaka, povzemi, preveri_dostop

VSI_VIRI = "Vsi viri"


# ---------- pomožne funkcije ----------

def _v_besedilo(vrednost):
    if isinstance(vrednost, list):
        return "\n".join(f"- {x}" for x in vrednost)
    return str(vrednost or "")


# ---------- dialogi ----------

class NovaRaziskavaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova raziskava")
        self.naslov = QLineEdit()
        self.vir = QComboBox()
        self.vir.addItems(VIRI)
        self.povezava = QLineEdit()
        self.povezava.setPlaceholderText("https://...")

        forma = QFormLayout(self)
        forma.addRow("Naslov:", self.naslov)
        forma.addRow("Vir:", self.vir)
        forma.addRow("Povezava:", self.povezava)

        gumbi = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        gumbi.accepted.connect(self._potrdi)
        gumbi.rejected.connect(self.reject)
        forma.addRow(gumbi)

    def _potrdi(self):
        if not self.naslov.text().strip():
            QMessageBox.warning(self, "Manjka naslov", "Vnesi naslov raziskave.")
            return
        self.accept()

    def vrednosti(self):
        return {
            "naslov": self.naslov.text().strip(),
            "vir": self.vir.currentText(),
            "povezava": self.povezava.text().strip(),
        }


class PovzetekDelavec(QThread):
    """Povzemanje poteka v ozadju, da se okno med tem ne zamrzne."""
    koncano = Signal(dict)
    napaka = Signal(str)

    def __init__(self, besedilo):
        super().__init__()
        self.besedilo = besedilo

    def run(self):
        try:
            self.koncano.emit(povzemi(self.besedilo))
        except OllamaNapaka as e:
            self.napaka.emit(str(e))


class PovzetekDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Povzetek z Ollama")
        self.resize(760, 760)
        self.delavec = None

        self.pogovor = QTextEdit()
        self.pogovor.setPlaceholderText("Prilepi besedilo pogovora iz spletnega vmesnika ...")
        self.gumb_povzemi = QPushButton("Povzemi")
        self.gumb_povzemi.clicked.connect(self._povzemi)
        self.oznaka = QLabel(f"Model: {MODEL}")

        self.stanje = QTextEdit()
        self.ugotovitve = QTextEdit()
        self.vprasanja = QTextEdit()
        self.viri = QTextEdit()

        self.gumb_shrani = QPushButton("Shrani kot novo stanje")
        self.gumb_shrani.clicked.connect(self.accept)
        self.gumb_preklici = QPushButton("Prekliči")
        self.gumb_preklici.clicked.connect(self.reject)

        glavni = QVBoxLayout(self)
        glavni.addWidget(QLabel("1. Prilepi pogovor in klikni Povzemi."))
        glavni.addWidget(self.pogovor, 2)
        vrstica = QHBoxLayout()
        vrstica.addWidget(self.gumb_povzemi)
        vrstica.addWidget(self.oznaka, 1)
        glavni.addLayout(vrstica)

        glavni.addWidget(QLabel("2. Pregledaj in po potrebi popravi."))
        for naslov, polje in [
            ("Trenutno stanje", self.stanje),
            ("Ključne ugotovitve", self.ugotovitve),
            ("Odprta vprašanja", self.vprasanja),
            ("Viri", self.viri),
        ]:
            glavni.addWidget(QLabel(naslov))
            glavni.addWidget(polje, 1)

        spodaj = QHBoxLayout()
        spodaj.addStretch()
        spodaj.addWidget(self.gumb_preklici)
        spodaj.addWidget(self.gumb_shrani)
        glavni.addLayout(spodaj)

    def _povzemi(self):
        besedilo = self.pogovor.toPlainText().strip()
        if not besedilo:
            QMessageBox.warning(self, "Ni besedila", "Najprej prilepi besedilo pogovora.")
            return
        self.gumb_povzemi.setEnabled(False)
        self.oznaka.setText("Povzemam ... to lahko traja nekaj minut.")
        self.delavec = PovzetekDelavec(besedilo)
        self.delavec.koncano.connect(self._koncano)
        self.delavec.napaka.connect(self._napaka)
        self.delavec.start()

    def _koncano(self, data):
        self.stanje.setPlainText(_v_besedilo(data.get("trenutno_stanje")))
        self.ugotovitve.setPlainText(_v_besedilo(data.get("kljucne_ugotovitve")))
        self.vprasanja.setPlainText(_v_besedilo(data.get("odprta_vprasanja")))
        self.viri.setPlainText(_v_besedilo(data.get("viri")))
        self.oznaka.setText("Povzetek pripravljen. Preveri in shrani.")
        self.gumb_povzemi.setEnabled(True)

    def _napaka(self, sporocilo):
        QMessageBox.critical(self, "Napaka pri povzemanju", sporocilo)
        self.oznaka.setText("Povzemanje ni uspelo.")
        self.gumb_povzemi.setEnabled(True)

    def done(self, rezultat):
        # Ne zapri dialoga, dokler teče delavec, sicer se program lahko sesuje.
        if self.delavec is not None and self.delavec.isRunning():
            self.delavec.wait()
        super().done(rezultat)

    def rezultat(self):
        delovi = [self.stanje.toPlainText().strip()]
        for naslov, polje in [
            ("Ključne ugotovitve", self.ugotovitve),
            ("Odprta vprašanja", self.vprasanja),
            ("Viri", self.viri),
        ]:
            vsebina = polje.toPlainText().strip()
            if vsebina:
                delovi.append(f"{naslov}:\n{vsebina}")
        return "\n\n".join(d for d in delovi if d)


# ---------- glavno okno ----------

class GlavnoOkno(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raziskovalni dnevnik")
        self.resize(1200, 800)
        self.shramba = Shramba()
        self.trenutna_id = None

        # levi del: seznam raziskav
        self.iskanje = QLineEdit()
        self.iskanje.setPlaceholderText("Išči po naslovu ali stanju ...")
        self.iskanje.textChanged.connect(self.osvezi_seznam)

        self.filter_vira = QComboBox()
        self.filter_vira.addItems([VSI_VIRI] + VIRI)
        self.filter_vira.currentIndexChanged.connect(self.osvezi_seznam)

        self.seznam = QListWidget()
        self.seznam.currentItemChanged.connect(self.prikazi_raziskavo)

        gumb_nova = QPushButton("+ Nova raziskava")
        gumb_nova.clicked.connect(self.nova_raziskava)

        levo = QWidget()
        lv = QVBoxLayout(levo)
        lv.addWidget(self.iskanje)
        lv.addWidget(self.filter_vira)
        lv.addWidget(self.seznam, 1)
        lv.addWidget(gumb_nova)

        # desni zgornji del: podatki in trenutno stanje
        self.naslov = QLineEdit()
        self.vir = QComboBox()
        self.vir.addItems(VIRI)
        self.povezava = QLineEdit()
        self.status = QComboBox()
        self.status.addItems(STATUSI)

        forma = QFormLayout()
        forma.addRow("Naslov:", self.naslov)
        forma.addRow("Vir:", self.vir)
        forma.addRow("Povezava:", self.povezava)
        forma.addRow("Status:", self.status)

        self.stanje = QTextEdit()
        self.stanje.setPlaceholderText("Trenutno stanje raziskave ...")

        self.gumb_odpri = QPushButton("Odpri povezavo")
        self.gumb_odpri.clicked.connect(self.odpri_povezavo)
        self.gumb_podatki = QPushButton("Shrani podatke")
        self.gumb_podatki.clicked.connect(self.shrani_podatke)
        self.gumb_stanje = QPushButton("Shrani stanje")
        self.gumb_stanje.clicked.connect(self.shrani_stanje)
        self.gumb_povzemi = QPushButton("Povzemi z Ollama")
        self.gumb_povzemi.clicked.connect(self.povzemi)
        self.gumb_izbrisi = QPushButton("Izbriši raziskavo")
        self.gumb_izbrisi.clicked.connect(self.izbrisi)
        self.gumbi_raziskave = [
            self.gumb_odpri, self.gumb_podatki, self.gumb_stanje,
            self.gumb_povzemi, self.gumb_izbrisi,
        ]

        vrstica = QHBoxLayout()
        for g in self.gumbi_raziskave:
            vrstica.addWidget(g)
        vrstica.addStretch()

        # desni spodnji del: časovnica in komentarji
        self.casovnica = QListWidget()
        casovnica_panel = QWidget()
        cv = QVBoxLayout(casovnica_panel)
        cv.addWidget(QLabel("Časovnica"))
        cv.addWidget(self.casovnica, 1)

        self.komentarji = QListWidget()
        self.novi_komentar = QLineEdit()
        self.novi_komentar.setPlaceholderText("Nov komentar ...")
        self.novi_komentar.returnPressed.connect(self.dodaj_komentar)
        self.gumb_dodaj_komentar = QPushButton("Dodaj")
        self.gumb_dodaj_komentar.clicked.connect(self.dodaj_komentar)
        self.gumb_brisi_komentar = QPushButton("Izbriši komentar")
        self.gumb_brisi_komentar.clicked.connect(self.izbrisi_komentar)
        self.gumbi_raziskave += [self.gumb_dodaj_komentar, self.gumb_brisi_komentar]

        vrstica_k = QHBoxLayout()
        vrstica_k.addWidget(self.novi_komentar, 1)
        vrstica_k.addWidget(self.gumb_dodaj_komentar)
        vrstica_k.addWidget(self.gumb_brisi_komentar)
        komentarji_panel = QWidget()
        kv = QVBoxLayout(komentarji_panel)
        kv.addWidget(QLabel("Komentarji in opombe"))
        kv.addWidget(self.komentarji, 1)
        kv.addLayout(vrstica_k)

        spodaj = QSplitter()
        spodaj.addWidget(casovnica_panel)
        spodaj.addWidget(komentarji_panel)

        desno = QWidget()
        dv = QVBoxLayout(desno)
        dv.addLayout(forma)
        dv.addWidget(QLabel("Trenutno stanje"))
        dv.addWidget(self.stanje, 1)
        dv.addLayout(vrstica)
        dv.addWidget(spodaj, 1)

        glavni = QSplitter()
        glavni.addWidget(levo)
        glavni.addWidget(desno)
        glavni.setSizes([340, 860])
        self.setCentralWidget(glavni)

        self.posodobi_ollama_stanje()
        self.osvezi_seznam()

    # --- pomožne metode ---

    def posodobi_ollama_stanje(self):
        if preveri_dostop():
            self.statusBar().showMessage(f"Ollama: aktivna, model {MODEL}")
        else:
            self.statusBar().showMessage("Ollama ni dosegljiva. Zaženi Ollama za povzemanje.")

    def _nastavi_gumbe(self, vklopljeno):
        for g in self.gumbi_raziskave:
            g.setEnabled(vklopljeno)

    def _potrebna_izbira(self):
        if self.trenutna_id is None:
            QMessageBox.information(self, "Ni izbrane raziskave", "Najprej izberi raziskavo na seznamu.")
            return False
        return True

    # --- seznam in prikaz ---

    def osvezi_seznam(self, *_):
        izbrana = self.trenutna_id
        vir = None if self.filter_vira.currentText() == VSI_VIRI else self.filter_vira.currentText()

        self.seznam.blockSignals(True)
        self.seznam.clear()
        izbran_item = None
        for r in self.shramba.seznam(self.iskanje.text().strip(), vir):
            item = QListWidgetItem(f"{r['naslov']}\n{r['vir']} · {r['status']} · {lepo(r['posodobljeno'])}")
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            self.seznam.addItem(item)
            if r["id"] == izbrana:
                izbran_item = item
        if izbran_item is not None:
            self.seznam.setCurrentItem(izbran_item)
        self.seznam.blockSignals(False)
        self.prikazi_raziskavo(izbran_item)

    def prikazi_raziskavo(self, current, previous=None):
        if current is None:
            self.trenutna_id = None
            for polje in (self.naslov, self.povezava, self.novi_komentar):
                polje.clear()
            self.stanje.clear()
            self.casovnica.clear()
            self.komentarji.clear()
            self._nastavi_gumbe(False)
            return

        rid = current.data(Qt.ItemDataRole.UserRole)
        r = self.shramba.dobi(rid)
        if r is None:
            return
        self.trenutna_id = rid
        self.naslov.setText(r["naslov"])
        self.vir.setCurrentText(r["vir"])
        self.povezava.setText(r["povezava"])
        self.status.setCurrentText(r["status"])
        self.stanje.setPlainText(r["trenutno_stanje"])

        self.casovnica.clear()
        for d in self.shramba.dogodki(rid):
            self.casovnica.addItem(f"{lepo(d['cas'])}  [{d['tip']}]  {d['opis']}")
        self.osvezi_komentarje()
        self._nastavi_gumbe(True)

    def osvezi_komentarje(self):
        self.komentarji.clear()
        if self.trenutna_id is None:
            return
        for k in self.shramba.komentarji(self.trenutna_id):
            item = QListWidgetItem(f"{lepo(k['cas'])}: {k['besedilo']}")
            item.setData(Qt.ItemDataRole.UserRole, k["id"])
            self.komentarji.addItem(item)

    # --- dejanja ---

    def nova_raziskava(self):
        dialog = NovaRaziskavaDialog(self)
        if dialog.exec():
            v = dialog.vrednosti()
            self.trenutna_id = self.shramba.dodaj(v["naslov"], v["vir"], v["povezava"])
            self.filter_vira.setCurrentIndex(0)
            self.iskanje.clear()
            self.osvezi_seznam()

    def shrani_podatke(self):
        if not self._potrebna_izbira():
            return
        naslov = self.naslov.text().strip()
        if not naslov:
            QMessageBox.warning(self, "Manjka naslov", "Naslov ne sme biti prazen.")
            return
        stara = self.shramba.dobi(self.trenutna_id)
        novi_status = self.status.currentText()
        self.shramba.posodobi_podatke(
            self.trenutna_id, naslov, self.vir.currentText(),
            self.povezava.text().strip(), novi_status,
        )
        if stara["status"] != novi_status:
            self.shramba.dodaj_dogodek(
                self.trenutna_id, "sprememba", f"Status: {stara['status']} → {novi_status}"
            )
        self.osvezi_seznam()

    def shrani_stanje(self):
        if not self._potrebna_izbira():
            return
        besedilo = self.stanje.toPlainText().strip()
        stara = self.shramba.dobi(self.trenutna_id)
        if besedilo == stara["trenutno_stanje"]:
            self.statusBar().showMessage("Ni sprememb v stanju.", 4000)
            return
        self.shramba.nastavi_stanje(self.trenutna_id, besedilo, "sprememba", "Ročno popravljeno stanje")
        self.osvezi_seznam()

    def povzemi(self):
        if not self._potrebna_izbira():
            return
        dialog = PovzetekDialog(self)
        if dialog.exec():
            besedilo = dialog.rezultat()
            if besedilo:
                self.shramba.nastavi_stanje(self.trenutna_id, besedilo, "povzetek", "Povzetek z Ollama, pregledan")
                self.osvezi_seznam()
        self.posodobi_ollama_stanje()

    def odpri_povezavo(self):
        if not self._potrebna_izbira():
            return
        url = self.povezava.text().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.information(self, "Ni povezave", "Raziskava nima shranjene povezave.")

    def izbrisi(self):
        if not self._potrebna_izbira():
            return
        odgovor = QMessageBox.question(
            self, "Izbriši raziskavo",
            "Izbrisati raziskavo skupaj z časovnico in komentarji?",
        )
        if odgovor == QMessageBox.StandardButton.Yes:
            self.shramba.izbrisi(self.trenutna_id)
            self.trenutna_id = None
            self.osvezi_seznam()

    def dodaj_komentar(self):
        if not self._potrebna_izbira():
            return
        besedilo = self.novi_komentar.text().strip()
        if not besedilo:
            return
        self.shramba.dodaj_komentar(self.trenutna_id, besedilo)
        self.novi_komentar.clear()
        self.osvezi_komentarje()

    def izbrisi_komentar(self):
        item = self.komentarji.currentItem()
        if item is None:
            QMessageBox.information(self, "Ni izbire", "Najprej izberi komentar.")
            return
        self.shramba.izbrisi_komentar(item.data(Qt.ItemDataRole.UserRole))
        self.osvezi_komentarje()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    okno = GlavnoOkno()
    okno.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
