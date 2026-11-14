"""Core logic: drives a visible browser window with the tsowiki.eu combat simulator,
reads the results you already simulated and saves them as JSON (+ map image).

The program can also start the simulator for the adventures you check, using the
settings window. It does not send generals to attack in the game.
"""
from __future__ import annotations

import base64
import datetime
import json
import queue
import re
import threading
import time
import urllib.parse
import zipfile
from pathlib import Path

SIM_URL = "https://tsowiki.eu/simulator/"

# Records everything the page copies to the clipboard (the simulator's "copy" button
# puts a link with the complete solution there).
HOOK_JS = r"""
(() => {
  window.__rv_copied = window.__rv_copied || [];
  const push = (t) => { try { if (t) window.__rv_copied.push(String(t)); } catch (e) {} };
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      const orig = navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = function (t) {
        push(t);
        try { return orig(t).catch(() => {}); } catch (e) { return Promise.resolve(); }
      };
    }
  } catch (e) {}
  try {
    const oe = document.execCommand.bind(document);
    document.execCommand = function (cmd, ...a) {
      if (cmd === 'copy') {
        const el = document.activeElement;
        let t = '';
        try {
          if (el && typeof el.value === 'string') {
            t = el.value.substring(el.selectionStart, el.selectionEnd) || el.value;
          } else { t = String(document.getSelection()); }
        } catch (e) {}
        push(t);
      }
      return oe(cmd, ...a);
    };
  } catch (e) {}
})();
"""

# Shrink the map and paint camp numbers onto the JPEG (the game client cannot show WebP).
TO_JPEG_JS = r"""
async ({src, camps, mapW, mapH, maxW}) => {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.src = src;
  await img.decode();
  const limit = maxW || 1200;
  const scale = Math.min(1, limit / img.naturalWidth);
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(img.naturalWidth * scale));
  c.height = Math.max(1, Math.round(img.naturalHeight * scale));
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0, c.width, c.height);
  return c.toDataURL('image/jpeg', 0.86);
}
"""

# Net losses shown on a simulator result row: column 6 is lost (or already
# lost-minus-recovered), column 7 is recovered when the two are separate.
ROW_LOSS_JS = r"""
(el) => {
  function nums(text) {
    const t = String(text || '').replace(/\u2011/g, '-').replace(/\s+/g, ' ').trim();
    if (!t) return null;
    let m = t.match(/(\d+)\s*-\s*(\d+)(?:\s*\(([\d.,]+)\))?/);
    if (m) {
      const min = +m[1], max = +m[2];
      const avg = m[3] ? parseFloat(m[3].replace(',', '.')) : (min + max) / 2;
      return { min, max, avg };
    }
    m = t.match(/(\d+(?:[.,]\d+)?)/);
    if (!m) return null;
    const v = parseFloat(m[1].replace(',', '.'));
    return { min: v, max: v, avg: v };
  }
  function chips(cell) {
    const out = {};
    if (!cell) return out;
    cell.querySelectorAll('[data-id]').forEach((node) => {
      const id = node.getAttribute('data-id');
      if (!id || out[id]) return;
      const label = node.querySelector('span');
      const amt = nums(label ? label.textContent : '');
      if (amt) out[id] = amt;
    });
    return out;
  }
  const cells = el.children || [];
  const lost = chips(cells[6]);
  const back = chips(cells[7]);
  const net = {};
  Object.keys(lost).forEach((id) => {
    const L = lost[id];
    const R = back[id];
    const avg = R ? Math.max(0, L.avg - R.avg) : L.avg;
    if (avg > 0) net[id] = Math.round(avg * 100) / 100;
  });
  return net;
}
"""

REVEAL_JS = r"""
() => {
  const re = /show more results/i;
  const sels = ['button', 'a', '[role="button"]', 'input[type="button"]', 'div', 'span'];
  for (const sel of sels) {
    for (const el of document.querySelectorAll(sel)) {
      let direct = '';
      for (const n of el.childNodes) {
        if (n.nodeType === 3) direct += n.textContent;
      }
      const t = (direct.trim() || (el.innerText || el.value || '').trim());
      if (!re.test(t) || t.length > 48) continue;
      const st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden') continue;
      const r = el.getBoundingClientRect();
      if (r.width < 8 || r.height < 8) continue;
      el.scrollIntoView({ block: 'center', inline: 'nearest' });
      el.click();
      return true;
    }
  }
  return false;
}
"""

FIND_MAP_JS = r"""
() => {
  const known = document.querySelector('#combat-sim-enemy-camp-map img');
  if (known) {
    known.setAttribute('data-rv-map', '1');
    return { tag: 'IMG', src: known.currentSrc || known.src || '' };
  }
  let best = null, bestArea = 0;
  const ok = (el) => {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') return false;
    return true;
  };
  for (const el of document.querySelectorAll('img, canvas, svg')) {
    if (!ok(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 400 || r.height < 300) continue;
    const area = r.width * r.height;
    if (area > bestArea) { bestArea = area; best = el; }
  }
  if (!best) return null;
  best.setAttribute('data-rv-map', '1');
  return { tag: best.tagName, src: best.currentSrc || best.src || '' };
}
"""

READ_ADVENTURE_JS = r"""
() => {
  const q = (s) => document.querySelector(s);
  let urls = {};
  try {
    urls = JSON.parse((q('#combat-sim-adventure-urls') || {}).textContent || '{}');
  } catch (e) {}
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const main = q('#combat-sim-adventure-button');
  const labelEl = main ? main.querySelector('span:last-of-type') : null;
  const label = labelEl ? labelEl.textContent.trim() : '';
  let id = '';
  if (main && main.value && urls[main.value]) id = main.value;
  if (!id && label) {
    document.querySelectorAll('#combat-sim-adventure-buttons button').forEach((b) => {
      if (!id && norm(b.innerText) === norm(label)) id = b.value || '';
    });
  }
  if (!id) {
    try {
      const qs = new URLSearchParams(location.search);
      const a = qs.get('adventure') || '';
      if (a) id = a;
    } catch (e) {}
  }
  return { id, label, known: !!urls[id] };
}
"""

MAP_META_JS = r"""
async (advId) => {
  const el = document.querySelector('#combat-sim-adventure-urls');
  if (!el) return null;
  let urls = {};
  try { urls = JSON.parse(el.textContent || '{}'); } catch (e) { return null; }
  const url = urls[advId];
  if (!url) return null;
  const data = await (await fetch(url)).json();
  const camps = [];
  const src = data.camps || {};
  Object.keys(src).forEach((key) => {
    const c = src[key] || {};
    const p = c.position || {};
    camps.push({
      id: c.id || key,
      number: c.number,
      x: p.x,
      y: p.y,
      type: c.type || ''
    });
  });
  const map = data.map || {};
  return { width: map.width || null, height: map.height || null, key: map.key || advId, camps };
}
"""


# ---------------------------------------------------------------- parsing

def parse_sim_url(url: str) -> dict | None:
    """Decode a simulator link into plain data. Returns None if it is not one."""
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if "adventure" not in q and "player" not in q:
            return None
        enemy = json.loads(q.get("enemy", ["[]"])[0])
        player = json.loads(q.get("player", ["[]"])[0])
        generals = json.loads(q.get("generals", ["[]"])[0])
        buffs = json.loads(q.get("buffs", ["[]"])[0])
    except Exception:
        return None

    gens = {g.get("id"): g for g in generals if isinstance(g, dict)}
    attackers = []
    for p in player:
        gid = p.get("general")
        g = gens.get(gid, {})
        attackers.append({
            "kind": p.get("kind"),
            "general_id": gid,
            "general_base": g.get("base"),
            "general_name": g.get("name") or "",
            "general_skills": g.get("skills", {}),
            "units": {u["id"]: u["amount"] for u in p.get("units", []) if u.get("amount")},
        })
    camps = [{
        "camp_id": e.get("id"),
        "units": {u["id"]: u["amount"] for u in e.get("units", []) if u.get("amount")},
    } for e in enemy]
    return {
        "adventure": q.get("adventure", [""])[0],
        "buffs": buffs,
        "enemy": camps,
        "attackers": attackers,
    }


def _victory(text: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
    return float(m.group(1).replace(",", ".")) if m else None


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_") or "adventure"


def unit_total(attacker: dict | None) -> int:
    if not attacker:
        return 0
    total = 0
    for amount in (attacker.get("units") or {}).values():
        try:
            total += int(amount)
        except (TypeError, ValueError):
            continue
    return total


def general_key(attacker: dict | None) -> str:
    if not attacker:
        return ""
    return str(attacker.get("general_id") or attacker.get("general_name") or attacker.get("general_base") or "")


def select_best_solutions(solutions: list[dict], limit: int) -> tuple[list[dict], str]:
    """One winning setup per general: the smallest army that still wins.

    Generals are then ordered by that army size. `limit` is how many generals
    to keep (the X cheapest distinct generals). A win is 100% victory.
    If nobody reached 100%, the best victory percent that was actually read is used.
    """
    parsed = []
    for s in solutions:
        setup = s.get("setup") or {}
        attackers = setup.get("attackers") or []
        atk = attackers[0] if attackers else None
        if not atk or not general_key(atk):
            continue
        vp = s.get("victory_percent")
        parsed.append((vp if isinstance(vp, (int, float)) else -1.0, unit_total(atk), general_key(atk), s))

    winners = [p for p in parsed if p[0] >= 100]
    note = ""
    pool = winners
    if not pool:
        if not parsed:
            return [], "nobene prebrane resitve z generalom"
        best_vp = max(p[0] for p in parsed)
        pool = [p for p in parsed if p[0] == best_vp]
        note = f"ni 100% zmage, uporabljam najboljsi odstotek ({best_vp:g}%)"

    best: dict[str, tuple] = {}
    for vp, total, gid, s in pool:
        cur = best.get(gid)
        if cur is None or total < cur[0] or (total == cur[0] and vp > cur[1]):
            best[gid] = (total, vp, s)
    ranked = sorted(best.values(), key=lambda t: (t[0], -t[1], general_key((t[2].get("setup") or {}).get("attackers", [{}])[0])))
    keep = max(1, int(limit or 1))
    out = []
    for i, (total, _vp, s) in enumerate(ranked[:keep], start=1):
        item = dict(s)
        item["rank"] = i
        item["unit_total"] = total
        out.append(item)
    return out, note


# ---------------------------------------------------------------- saving

def resolve_folder(out_dir: Path, adventure: str) -> Path:
    """Prefer the folder that already holds this adventure's results.json.

    A typed display name and the real adventure id used to land in two folders.
    If a previous run already wrote results under either name, keep using that
    folder so the map and the results stay together.
    """
    out_dir = Path(out_dir)
    canonical = out_dir / safe_name(adventure)
    matches: list[Path] = []
    if out_dir.exists():
        for p in sorted(out_dir.iterdir()):
            if not p.is_dir() or p.name.startswith("_"):
                continue
            rj = p / "results.json"
            if not rj.exists():
                continue
            try:
                data = json.loads(rj.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("adventure") == adventure or p.name == safe_name(adventure):
                matches.append(p)
    for p in matches:
        if p.resolve() == canonical.resolve():
            return p
    if len(matches) == 1:
        return matches[0]
    return canonical


def finished_tabs(out_dir: Path, adventure: str, generals: int) -> set[str]:
    """Camp tab labels that already store at least `generals` solutions."""
    if not adventure:
        return set()
    path = resolve_folder(out_dir, adventure) / "results.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    need = max(1, int(generals))
    done = set()
    for camp in data.get("camps") or []:
        if len(camp.get("solutions") or []) < need:
            continue
        tab = str(camp.get("tab") or "").strip()
        if tab:
            done.add(tab)
    return done


UNIT_GROUPS = {
    "Default": [
        "Recruit", "Militia", "Soldier", "EliteSoldier", "Cavalry",
        "Bowman", "Longbowman", "Crossbowman", "Cannoneer",
    ],
    "Elite": [
        "Swordsman", "MountedSwordsman", "Knight", "Marksman",
        "ArmoredMarksman", "MountedMarksman", "Besieger",
    ],
    "BattleBuff": [
        "BattleBuffBomb_random_units_0", "BattleBuffBomb_random_units_2",
        "BattleBuffBomb_random_units_limited_3", "BattleBuffBombCupidosArrow",
        "BattleBuffBomb_random_units_limited", "BattleBuffBomb_random_units",
        "BattleBuffBomb_random_units_limited_2", "BattleBuffKill_random_unit_type_limited",
        "BattleBuffKill_random_unit_type", "BattleBuffKill_random_boss_limited",
        "BattleBuffDestroy_small_camps", "BattleBuffDestroy_small_medium_camps",
    ],
}
KIND_LABELS = {"Default": "Default", "Elite": "Elite", "BattleBuff": "Arrows"}
REPETITIONS = [10, 100, 250, 500, 1000, 5000, 10000, 25000, 50000, 100000]
INCREMENTS = [1, 2, 5, 10, 20, 25, 50]
SORTS = [
    ("LossesValueLow", "Minimum unit losses (value)"),
    ("LossesAmountLow", "Minimum unit losses (amount)"),
    ("MinDurationHigh", "Minimum duration (descending)"),
    ("XP", "Experience"),
    ("Efficiency", "Efficiency (experience/value)"),
]
EXCLUDE_COMBOS = [
    ("Recruit|Militia", "Recruit + Militia"),
    ("Recruit|Soldier", "Recruit + Soldier"),
    ("Militia|Soldier", "Militia + Soldier"),
    ("Recruit|EliteSoldier", "Recruit + Elite Soldier"),
    ("Crossbowman|Cannoneer", "Crossbowman + Cannoneer"),
    ("Swordsman|MountedSwordsman", "Swordsman + Mounted Swordsman"),
    ("Knight|MountedMarksman", "Knight + Mounted Marksman"),
    ("ArmoredMarksman|Besieger", "Armored Marksman + Besieger"),
]
SKIP_MODES = [
    ("none", "Ne preskakuj"),
    ("folder", "Preskoči, če mapa obstaja"),
    ("results", "Preskoči, če je results.json"),
    ("both", "Preskoči, če sta rezultati in zemljevid"),
]
MAP_FILES = ("map.jpg", "map.jpeg", "map.png", "map.webp")


def adventure_files(out_dir: Path, adventure: str) -> tuple[bool, bool, bool]:
    folder = resolve_folder(out_dir, adventure)
    exists = folder.exists()
    has_results = False
    path = folder / "results.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            has_results = bool(data.get("camps"))
        except Exception:
            has_results = path.stat().st_size > 20
    has_map = any((folder / name).exists() for name in MAP_FILES)
    return exists, has_results, has_map


def should_skip_adventure(out_dir: Path, adventure: str, mode: str) -> bool:
    exists, has_results, has_map = adventure_files(out_dir, adventure)
    if mode == "folder":
        return exists
    if mode == "results":
        return has_results
    if mode == "both":
        return has_results and has_map
    return False


LIST_ADVENTURES_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('#combat-sim-adventure-buttons button').forEach((b) => {
    const name = ((b.querySelector('span:last-of-type') || {}).textContent || b.value || '').trim();
    if (b.value) out.push({ id: b.value, name: name || b.value });
  });
  return out;
}
"""

APPLY_SETTINGS_JS = r"""
(cfg) => {
  const fire = (el) => {
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const search = document.getElementById('combat-sim-player-search-toggle');
  if (search && !search.checked) search.click();
  const kind = document.querySelector('input[name="combat-sim-unit-types"][value="' + cfg.unitKind + '"]');
  if (kind && !kind.checked) kind.click();
  const setSelect = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = String(value);
    fire(el);
  };
  setSelect('combat-sim-config-search-threads', cfg.threads);
  const radio = (name, value) => {
    const el = document.querySelector('input[name="' + name + '"][value="' + value + '"]');
    if (el && !el.checked) el.click();
  };
  radio('combat-sim-config-search-repetitions-group', cfg.repetitions);
  radio('combat-sim-config-search-increments-group', cfg.increment);
  radio('combat-sim-config-input-steps-group', cfg.step);
  const box = (id, on) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (!!el.checked !== !!on) el.click();
  };
  box('combat-sim-player-skip-amount', cfg.onlyMax);
  box('combat-sim-config-merge-lost-recovered', cfg.merge);
  box('combat-sim-config-all-camps', cfg.allCamps);
  box('combat-sim-config-skip-victory', cfg.skipVictory);
  setSelect('combat-sim-config-sort-results', cfg.sort);
  const excluded = cfg.exclude || [];
  document.querySelectorAll('#combat-sim-config-search-exclude-combos input').forEach((el) => {
    const want = excluded.indexOf(el.value) >= 0;
    if (!!el.checked !== want) el.click();
  });
  const units = cfg.units || {};
  document.querySelectorAll('#combat-sim-player-units > li').forEach((li) => {
    if (li.dataset.kind !== cfg.unitKind) return;
    const spec = units[li.dataset.id];
    if (!spec) return;
    const inputs = li.querySelectorAll('input.is-unit-search[type="number"]');
    if (inputs[0]) { inputs[0].value = String(spec.min || 0); fire(inputs[0]); }
    if (inputs[1]) { inputs[1].value = String(spec.max || 0); fire(inputs[1]); }
  });
  return true;
}
"""

SELECT_GENERALS_JS = r"""
(names) => {
  const want = {};
  (names || []).forEach((n) => { want[String(n).trim().toLowerCase()] = 1; });
  const root = document.getElementById('combat-sim-player-generals-list-custom');
  if (!root) return { ok: false, picked: [], missing: names || [] };
  const seen = {};
  root.querySelectorAll('button').forEach((b) => {
    const name = String(b.innerText || '').replace(/\s+/g, ' ').trim();
    const key = name.toLowerCase();
    const should = !!want[key];
    if (should) seen[key] = name;
    const on = String(b.className || '').indexOf('selected') >= 0;
    if (should !== on) b.click();
  });
  const missing = [];
  (names || []).forEach((n) => {
    if (!seen[String(n).trim().toLowerCase()]) missing.push(n);
  });
  return { ok: true, picked: Object.keys(seen).map((k) => seen[k]), missing };
}
"""

SIM_STATE_JS = r"""
() => {
  const b = document.getElementById('combat-sim-button');
  const c = document.getElementById('combat-sim-button-counter');
  return {
    on: b ? (b.getAttribute('data-on') || '') : '',
    counter: c ? String(c.value || c.textContent || '') : '',
    text: b ? String(b.innerText || '').replace(/\s+/g, ' ').trim() : ''
  };
}
"""


def save_results(out_dir: Path, adventure: str, camps: list[dict]) -> Path:
    """Merge camps into <out_dir>/<adventure>/results.json (same camp id = replaced)."""
    folder = resolve_folder(out_dir, adventure)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "results.json"
    data = {"adventure": adventure, "camps": []}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    new_tabs = {c.get("tab") for c in camps}
    old = [c for c in data.get("camps", [])
           if not (c.get("camp_id") is None and c.get("tab") in new_tabs)]
    existing = {c.get("camp_id") or c.get("tab"): c for c in old}
    for c in camps:
        existing[c.get("camp_id") or c.get("tab")] = c
    data["camps"] = list(existing.values())
    data["adventure"] = adventure
    data["saved"] = datetime.datetime.now().isoformat(timespec="seconds")
    data["source"] = "tsowiki.eu/simulator"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_map_meta(out_dir: Path, adventure: str, meta: dict) -> Path:
    folder = resolve_folder(out_dir, adventure)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "results.json"
    data: dict = {"adventure": adventure, "camps": []}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {"adventure": adventure, "camps": []}
    data["adventure"] = data.get("adventure") or adventure
    data["map"] = meta
    data.setdefault("camps", [])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_zip(out_dir: Path, zip_path: Path) -> int:
    out_dir = Path(out_dir)
    zip_path = Path(zip_path).resolve()
    n = 0
    files = [f for f in sorted(out_dir.rglob("*"))
             if f.is_file() and "_debug" not in f.parts and f.suffix.lower() != ".zip"
             and f.resolve() != zip_path]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.relative_to(out_dir).as_posix())
            n += 1
    return n


# ---------------------------------------------------------------- browser

class SimBrowser:
    """All Playwright calls run on one worker thread (Playwright requires that)."""

    def __init__(self, profile_dir: Path, headless: bool = False):
        self.profile_dir = Path(profile_dir)
        self.headless = headless
        self._q: queue.Queue = queue.Queue()
        self._pw = None
        self._ctx = None
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    # -- worker plumbing
    def _loop(self):
        while True:
            item = self._q.get()
            if item is None:
                break
            fn, args, done = item
            try:
                res, exc = fn(*args), None
            except Exception as e:  # noqa: BLE001
                res, exc = None, e
            if done:
                done(res, exc)

    def submit(self, fn, *args, done=None):
        self._q.put((fn, args, done))

    def call(self, fn, *args):
        """Blocking helper (used by tests)."""
        ev = threading.Event()
        box = {}

        def done(res, exc):
            box["r"], box["e"] = res, exc
            ev.set()

        self.submit(fn, *args, done=done)
        ev.wait()
        if box["e"]:
            raise box["e"]
        return box["r"]

    # -- operations (run on the worker thread)
    def open(self, url: str = SIM_URL) -> str:
        from playwright.sync_api import sync_playwright

        if self._ctx is not None:
            try:
                pages = [p for p in self._ctx.pages if not p.is_closed()]
                if pages:
                    pages[0].bring_to_front()
                    return "Brskalnik je ze odprt."
            except Exception:
                self._ctx = None
        if self._pw is None:
            self._pw = sync_playwright().start()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        last = None
        for channel in ("chrome", "msedge", None):
            try:
                kw = dict(user_data_dir=str(self.profile_dir), headless=self.headless, no_viewport=True)
                if channel:
                    kw["channel"] = channel
                self._ctx = self._pw.chromium.launch_persistent_context(**kw)
                break
            except Exception as e:  # noqa: BLE001
                last = e
        if self._ctx is None:
            raise RuntimeError(
                "Ne najdem brskalnika (Chrome/Edge). Namesti Chrome ali zaženi: "
                "python -m playwright install chromium\n" + str(last))
        self._ctx.add_init_script(HOOK_JS)
        page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        page.goto(url)
        return "Simulator odprt. Nastavi simulacijo, jo zazeni in klikni 'Pridobi rezultate'."

    def _page(self):
        if self._ctx is None:
            raise RuntimeError("Brskalnik ni odprt - klikni 'Odpri simulator'.")
        pages = [p for p in self._ctx.pages if not p.is_closed()]
        if not pages:
            self._ctx = None
            raise RuntimeError("Brskalnik je zaprt - klikni 'Odpri simulator'.")
        for p in pages:
            if "simulator" in p.url:
                return p
        return pages[0]

    def read_adventure(self) -> dict:
        page = self._page()
        try:
            info = page.evaluate(READ_ADVENTURE_JS) or {}
        except Exception:
            info = {}
        if not info.get("id"):
            try:
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)
                info["id"] = q.get("adventure", [""])[0]
            except Exception:
                info["id"] = ""
        info.setdefault("label", "")
        return info

    def collect(self, generals: int = 3, log=lambda s: None, scan_limit: int = 80, skip=None, stop=None) -> list[dict]:
        page = self._page()
        tabs = []
        loc = page.get_by_text(re.compile(r"^\s*Camp\s+\d+\s*$"))
        seen = set()
        for i in range(loc.count()):
            e = loc.nth(i)
            try:
                if not e.is_visible():
                    continue
                label = e.inner_text().strip()
            except Exception:
                continue
            if label not in seen:
                seen.add(label)
                tabs.append((label, e))
        if not tabs:
            tabs = [("(current)", None)]
            log("Zavihkov Camp ni najti - berem trenutno tabelo.")
        camps = []
        skip = set(skip or [])
        for label, tab in tabs:
            if stop is not None and stop():
                log("Ustavljeno med branjem rezultatov.")
                break
            if label in skip:
                log(f"{label}: že ima dovolj generalov, preskočim.")
                continue
            if tab is not None:
                tab.click()
                page.wait_for_timeout(700)
            self._reveal_results(page, label, log)
            camp = self._read_rows(page, label, generals, scan_limit, log)
            if camps and [x["row_text"] for x in camp["solutions"]] == [x["row_text"] for x in camps[-1]["solutions"]]:
                log(f"OPOZORILO: {label} ima enake vrstice kot prejsnji tabor - zavihek se morda ni preklopil.")
            camps.append(camp)
        return camps

    def _reveal_results(self, page, label, log):
        """The simulator hides the tail of the list behind 'Show more results'."""
        clicks = 0
        while clicks < 40:
            try:
                hit = page.evaluate(REVEAL_JS)
            except Exception:
                break
            if not hit:
                break
            clicks += 1
            page.wait_for_timeout(400)
        if clicks:
            log(f"{label}: 'Show more results' pritisnjen {clicks}×, da so vidne vse vrstice.")
        return clicks

    def _read_rows(self, page, label, generals, scan_limit, log):
        rows = (page.locator("tr:visible")
                .filter(has=page.locator("button, [role=button], a"))
                .filter(has_text=re.compile(r"\d\s*%")))
        total = rows.count()
        n = min(total, max(1, int(scan_limit or 80)))
        if total > n:
            log(f"{label}: vidnih je {total} vrstic, preberem prvih {n}. Povecaj 'Preberi vrstic', ce so cenejsi generali nizje.")
        sols = []
        for r in range(n):
            row = rows.nth(r)
            text = " ".join(row.inner_text().split())
            url = self._copy_link(page, row)
            parsed = parse_sim_url(url) if url else None
            losses = {}
            try:
                losses = row.evaluate(ROW_LOSS_JS) or {}
            except Exception:
                losses = {}
            sols.append({
                "rank": r + 1,
                "victory_percent": _victory(text),
                "row_text": text,
                "link": url,
                "setup": parsed,
                "losses": losses,
            })
            if not url:
                log(f"{label} #{r + 1}: povezave ni uspelo prebrati (glej Diagnostika).")
        picked, note = select_best_solutions(sols, generals)
        camp_id = None
        enemy = None
        for s in picked or sols:
            if s.get("setup") and s["setup"]["enemy"]:
                camp_id = s["setup"]["enemy"][0]["camp_id"]
                enemy = s["setup"]["enemy"][0]["units"]
                break
        extra = f" {note}." if note else ""
        log(f"{label}: prebranih {len(sols)} vrstic, izbranih {len(picked)} generalov (najmanj vojakov ob zmagi).{extra}")
        return {"tab": label, "camp_id": camp_id, "enemy_units": enemy, "solutions": picked,
                "read": datetime.datetime.now().isoformat(timespec="seconds")}

    def _copy_link(self, page, row):
        # Only the copy button. The other buttons apply the army or open a window.
        buttons = row.locator(
            "button[title*='copy'], button[title*='Copy'], button[title*='clipboard'], button[title*='link']"
        )
        target = buttons.last if buttons.count() else row.locator("button, [role=button], a").last
        try:
            page.evaluate("window.__rv_copied = []")
            target.click(timeout=1500)
            page.wait_for_timeout(250)
            copied = page.evaluate("window.__rv_copied || []")
        except Exception:
            return None
        for extra in [p for p in self._ctx.pages if p is not page and not p.is_closed()]:
            copied.append(extra.url)
            extra.close()
        for t in copied:
            if "adventure=" in t or "player=" in t:
                return t
        return None

    def list_adventures(self) -> list[dict]:
        return self._page().evaluate(LIST_ADVENTURES_JS) or []

    def _apply_settings(self, page, settings: dict):
        page.evaluate(APPLY_SETTINGS_JS, {
            "unitKind": settings.get("unit_kind") or "Default",
            "threads": int(settings.get("threads") or 15),
            "repetitions": int(settings.get("repetitions") or 100),
            "increment": int(settings.get("increment") or 5),
            "step": int(settings.get("step") or 5),
            "onlyMax": bool(settings.get("only_max")),
            "merge": bool(settings.get("merge")),
            "allCamps": bool(settings.get("all_camps", True)),
            "skipVictory": bool(settings.get("skip_victory", True)),
            "sort": settings.get("sort") or "Efficiency",
            "exclude": list(settings.get("exclude") or []),
            "units": settings.get("units") or {},
        })

    def _sim_state(self, page) -> dict:
        try:
            return page.evaluate(SIM_STATE_JS) or {}
        except Exception:
            return {}

    def _click_sim_button(self, page):
        page.evaluate("() => { const b = document.getElementById('combat-sim-button'); if (b) b.click(); }")

    def run_batch(self, adventures, settings, out_dir: Path, generals: int, scan: int,
                  generals_file: str, skip_mode: str, stop, pause, log=lambda s: None) -> str:
        page = self._page()
        if generals_file:
            try:
                page.locator("#combat-sim-player-generals-import-btn").set_input_files(generals_file)
                page.wait_for_timeout(500)
                log("Generali uvoženi v simulator.")
            except Exception as exc:  # noqa: BLE001
                log(f"Uvoz generalov ni uspel: {exc}")
        finished = 0
        for item in adventures:
            if stop.is_set():
                self._click_sim_button(page) if self._sim_state(page).get("on") == "true" else None
                return f"Ustavljeno. Končanih avantur: {finished}."
            while pause.is_set() and not stop.is_set():
                page.wait_for_timeout(300)
            if stop.is_set():
                return f"Ustavljeno. Končanih avantur: {finished}."
            adv_id = item.get("id") or ""
            label = item.get("name") or adv_id
            if not adv_id:
                continue
            if should_skip_adventure(out_dir, adv_id, skip_mode):
                log(f"{label}: preskočim.")
                continue
            log(f"{label}: nastavljam simulator.")
            picked = page.evaluate(
                "(id) => { const b = document.querySelector('#combat-sim-adventure-buttons button[value=\"' + id + '\"]'); if (!b) return false; b.click(); return true; }",
                adv_id,
            )
            if not picked:
                log(f"{label}: v seznamu simulatorja je ni.")
                continue
            ready = False
            for _ in range(30):
                if stop.is_set():
                    return f"Ustavljeno. Končanih avantur: {finished}."
                info = {}
                try:
                    info = page.evaluate(READ_ADVENTURE_JS) or {}
                except Exception:
                    info = {}
                if info.get("id") == adv_id:
                    ready = True
                    break
                page.wait_for_timeout(400)
            if not ready:
                log(f"{label}: avantura se ni izbrala.")
                continue
            try:
                self._apply_settings(page, settings)
            except Exception as exc:  # noqa: BLE001
                log(f"{label}: nastavitev ni bilo mogoče vpisati: {exc}")
                continue
            wanted = [str(n) for n in (settings.get("generals_on") or []) if str(n).strip()]
            if not wanted:
                log(f"{label}: ni obkljukanih generalov, simulacija jih ne izbere.")
            else:
                try:
                    picked = page.evaluate(SELECT_GENERALS_JS, wanted) or {}
                except Exception as exc:  # noqa: BLE001
                    picked = {"ok": False, "missing": [str(exc)]}
                if not picked.get("ok"):
                    log(f"{label}: generalov v simulatorju ni bilo mogoče izbrati.")
                elif picked.get("missing"):
                    log(f"{label}: v simulatorju manjka: " + ", ".join(picked["missing"]))
                else:
                    log(f"{label}: izbranih generalov: {len(picked.get('picked') or [])}.")
            page.wait_for_timeout(300)
            log(f"{label}: Start simulation.")
            self._click_sim_button(page)
            started = False
            for _ in range(25):
                if stop.is_set():
                    if self._sim_state(page).get("on") == "true":
                        self._click_sim_button(page)
                    return f"Ustavljeno. Končanih avantur: {finished}."
                state = self._sim_state(page)
                if state.get("on") == "true":
                    started = True
                    break
                page.wait_for_timeout(200)
            if not started:
                state = self._sim_state(page)
                log(f"{label}: simulacija se ni začela ({state.get('text') or 'ni odgovora'}).")
                continue
            last = ""
            shown = 0.0
            while True:
                if stop.is_set():
                    log("Stop: pritiskam Cancel.")
                    if self._sim_state(page).get("on") == "true":
                        self._click_sim_button(page)
                    page.wait_for_timeout(400)
                    return f"Ustavljeno. Končanih avantur: {finished}."
                state = self._sim_state(page)
                counter = state.get("counter") or ""
                now = time.monotonic()
                if counter and counter != last and now - shown > 2:
                    last = counter
                    shown = now
                    log(f"{label}: teče, števec {counter}.")
                if state.get("on") != "true":
                    break
                page.wait_for_timeout(700)
            log(f"{label}: simulacija končana. Berem rezultate.")
            camps = self.collect(generals, log, scan, stop=stop.is_set)
            if stop.is_set():
                if camps:
                    save_results(out_dir, adv_id, camps)
                return f"Ustavljeno. Končanih avantur: {finished}."
            if camps:
                path = save_results(out_dir, adv_id, camps)
                log(f"{label}: shranjeno {path.name}, {len(camps)} taborov.")
            else:
                log(f"{label}: ni vrstic za shraniti.")
            try:
                target = self.save_map(out_dir, adv_id)
                log(f"{label}: zemljevid {target.name}.")
            except Exception as exc:  # noqa: BLE001
                log(f"{label}: zemljevida ni: {exc}")
            finished += 1
            if pause.is_set():
                log("Pavza. Klikni Pavza še enkrat za nadaljevanje.")
        return f"Končano. Obdelanih avantur: {finished}."

    def save_map(self, out_dir: Path, adventure: str) -> Path:
        page = self._page()
        folder = resolve_folder(out_dir, adventure)
        folder.mkdir(parents=True, exist_ok=True)
        meta = None
        try:
            meta = page.evaluate(MAP_META_JS, adventure)
        except Exception:
            meta = None
        camps = (meta or {}).get("camps") or []
        map_w = (meta or {}).get("width")
        map_h = (meta or {}).get("height")

        target = folder / "map.jpg"
        saved = False
        host = ""
        try:
            host = urllib.parse.urlsplit(page.url).netloc
        except Exception:
            host = ""
        remote = f"https://tsowiki.eu/images/maps/{adventure}.webp"
        if "tsowiki" in host:
            saved = self._jpeg_from(page, remote, target, camps, map_w, map_h)

        info = None
        if not saved:
            info = page.evaluate(FIND_MAP_JS)
            if not info:
                page.screenshot(path=str(folder / "map.png"))
                raise RuntimeError(
                    "Zemljevida na strani nisem nasel - shranil sem celoten zaslon (map.png). "
                    "Izberi avanturo in poskusi znova.")
            src = info.get("src") or ""
            if src:
                saved = self._jpeg_from(page, src, target, camps, map_w, map_h)
            if not saved:
                shot = folder / "map.png"
                page.locator('[data-rv-map="1"]').first.screenshot(path=str(shot))
                target = shot
            page.evaluate("document.querySelectorAll('[data-rv-map]').forEach(e => e.removeAttribute('data-rv-map'))")

        # Drop a stale WebP so the game script does not pick it over the JPEG.
        for stale in ("map.webp",):
            p = folder / stale
            if p.exists() and target.suffix.lower() == ".jpg":
                try:
                    p.unlink()
                except Exception:
                    pass

        if meta:
            meta = dict(meta)
            meta["numbered"] = bool(saved and camps)
            meta["file"] = target.name
            save_map_meta(out_dir, adventure, meta)
        return target

    def _jpeg_from(self, page, src: str, target: Path, camps, map_w, map_h) -> bool:
        try:
            data_url = page.evaluate(TO_JPEG_JS, {
                "src": src,
                "camps": camps if camps else [],
                "mapW": map_w,
                "mapH": map_h,
                "maxW": 1200,
            })
            if not data_url or "," not in data_url:
                return False
            target.write_bytes(base64.b64decode(data_url.split(",", 1)[1]))
            return target.stat().st_size > 100
        except Exception:
            return False

    def debug_dump(self, out_dir: Path) -> Path:
        page = self._page()
        folder = Path(out_dir) / "_debug"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        (folder / f"page-{stamp}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(folder / f"page-{stamp}.png"), full_page=True)
        return folder

    def current_adventure(self) -> str:
        return self.read_adventure().get("id") or ""

    def close(self):
        try:
            if self._ctx:
                self._ctx.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._ctx = None
        self._pw = None
