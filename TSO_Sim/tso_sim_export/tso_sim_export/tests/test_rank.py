"""Pure ranking tests. Run: python tests/test_rank.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import resolve_folder, select_best_solutions, finished_tabs, save_results, should_skip_adventure

def sol(gid, name, units, vp, camp="c1"):
    return {
        "victory_percent": vp,
        "row_text": f"{vp}%",
        "setup": {
            "adventure": "BountyHunterNew",
            "enemy": [{"camp_id": camp, "units": {"BanditRecruit": 10}}],
            "attackers": [{
                "general_id": gid,
                "general_base": "GhostGeneral",
                "general_name": name,
                "units": units,
            }],
        },
    }

rows = [
    sol("H1", "", {"Cavalry": 155}, 100),
    sol("H1", "", {"Soldier": 155}, 99.5),
    sol("H1", "", {"Knight": 25}, 100),
    sol("G1", "Ghost1", {"EliteSoldier": 230}, 100),
    sol("G1", "Ghost1", {"Cavalry": 400}, 100),
    sol("G2", "Ghost2", {"Cavalry": 80}, 100),
    sol("G3", "Ghost3", {"Cavalry": 10}, 90),
]
picked, note = select_best_solutions(rows, 2)
assert note == "", note
assert [p["unit_total"] for p in picked] == [25, 80], picked
assert picked[0]["setup"]["attackers"][0]["general_id"] == "H1"
assert picked[1]["setup"]["attackers"][0]["general_name"] == "Ghost2"
assert [p["rank"] for p in picked] == [1, 2]

# no 100%: keep the best percent, still the smallest army of that percent
picked2, note2 = select_best_solutions([
    sol("A", "A", {"Soldier": 50}, 80),
    sol("A", "A", {"Soldier": 20}, 80),
    sol("B", "B", {"Soldier": 30}, 70),
], 3)
assert "80" in note2
assert [p["unit_total"] for p in picked2] == [20]

import tempfile
root = Path(tempfile.mkdtemp())
old = root / "rocno_ime"
old.mkdir()
(old / "results.json").write_text('{"adventure":"BountyHunterNew","camps":[]}', encoding="utf-8")
found = resolve_folder(root, "BountyHunterNew")
assert found == old, found
(root / "BountyHunterNew").mkdir()
(root / "BountyHunterNew" / "map.jpg").write_bytes(b"x")
# results already live in the older folder, so the map must follow them
assert resolve_folder(root, "BountyHunterNew") == old
(root / "BountyHunterNew" / "results.json").write_text(
    '{"adventure":"BountyHunterNew","camps":[]}', encoding="utf-8")
assert resolve_folder(root, "BountyHunterNew").name == "BountyHunterNew"
save_results(root, "BountyHunterNew", [{
    "tab": "Camp 1",
    "camp_id": "1",
    "solutions": [{}, {}, {}],
}])
done = finished_tabs(root, "BountyHunterNew", 3)
assert done == {"Camp 1"}, done
assert finished_tabs(root, "BountyHunterNew", 4) == set()
assert should_skip_adventure(root, "BountyHunterNew", "results")
assert should_skip_adventure(root, "BountyHunterNew", "both")
assert should_skip_adventure(root, "BountyHunterNew", "folder")
assert not should_skip_adventure(root, "MissingAdventure", "both")
print("RANK OK")
