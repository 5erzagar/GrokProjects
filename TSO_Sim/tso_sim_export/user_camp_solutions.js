/********************************************
 * Camp Solutions v0.23
 *
 * Shows attack solutions exported by the TSO simulator helper
 * (rezultati/<adventure>/results.json + map.jpg).
 *
 * "Pripravi" sends army command 1031, the same packet as the green check. It does not start an attack.
 * It does not press the green confirm button and does not send an attack.
 *
 * The docked window lets clicks through outside itself, and closing it
 * removes the invisible layer that otherwise swallows game clicks.
 * "Ločeno okno" opens one always-on-top window. A click in the game
 * does not bury it and does not steal the click.
 ********************************************/

var CS_MODAL = 'campSolutionsModal';
var CS_KEY = 'CS_SETTINGS';
var CS_cfg = { folder: '', adventure: '', hidden: {} };
try { $.extend(CS_cfg, settings.read(null, CS_KEY)); } catch (e) { }
if (!CS_cfg.hidden) { CS_cfg.hidden = {}; }
var CS_LANG = CS_cfg.lang === 'en' ? 'en' : 'sl';
var CS_I18N = {
	sl: {
		pin: 'Pripni', pinned: 'Pripeto', pinTitle: 'Pripni: okno ostane nad igro, igro lahko klikneš',
		pick: 'Izberi mapo', map: 'Zemljevid', hiddenCamps: 'Skriti tabori', hideBeaten: 'Skrij premagane',
		restore: 'Povrni', numsHidden: 'Številke skritih', numsShow: 'Številke: pokaži', numsHide: 'Številke: skrij',
		paste: 'Prilepi JSON', close: 'Zapri', showBtn: 'Pokaži', camp: 'Tabor', general: 'General', send: 'Pošlji',
		prepare: 'Pripravi', prepareAll: 'Pripravi vse', win: 'Zmaga', attack: 'Napad', hide: 'Skrij', show: 'Prikaži',
		noCamps: 'V tej datoteki ni taborov.', noSol: 'Ni shranjene rešitve.', noData: 'Ni še podatkov.',
		planTitle: 'Za celo avanturo', planNote: 'Pripravi takoj nastavi enote generalu. V napad ga pošlješ sam. Pripravi vse vzame za vsakega generala največjo vojsko, ki jo rabi za en tabor.',
		needTitle: 'Ocena za celo avanturo', needNote: 'Za vsako enoto je to večje število: seštevek izgub na vseh taborih ali največ, kar kateri general rabi za en napad.',
		gens: 'Generali', loss: 'izguba', sameGen: 'isti general, počakaj, da se vrne',
		campOne: 'tabor', campsMany: 'tabori',
		missingLoss: 'Pri {n} taborih ni podatka o izgubah. V programu znova klikni «Pridobi rezultate».',
		hiddenNote: '{n} skritih taborov. Klikni «Skriti tabori», če jih želiš nazaj.',
		notFound: 'Generala «{name}» ni na tem otoku.',
		star: '{name}: je v zvezdnem meniju, ni v igri. Enote niso dodeljene.',
		task: '{name}: na nalogi, ukaz ni poslan.',
		sent: '{name}: poslano {units}. V napad ga pošlji sam.',
		opening: ' Odpiram okno.',
		short: '{name}: zmanjka {what}. Ukaz ni poslan.',
		needLine: '{unit} (rabi {need}, na voljo {have})',
		lang: 'EN'
	},
	en: {
		pin: 'Pin', pinned: 'Pinned', pinTitle: 'Pin: the window stays above the game and the game stays clickable',
		pick: 'Choose folder', map: 'Map', hiddenCamps: 'Hidden camps', hideBeaten: 'Hide beaten',
		restore: 'Restore', numsHidden: 'Hidden numbers', numsShow: 'Numbers: show', numsHide: 'Numbers: hide',
		paste: 'Paste JSON', close: 'Close', showBtn: 'Show', camp: 'Camp', general: 'General', send: 'Send',
		prepare: 'Prepare', prepareAll: 'Prepare all', win: 'Victory', attack: 'Attack', hide: 'Hide', show: 'Show',
		noCamps: 'This file has no camps.', noSol: 'No saved solution.', noData: 'No data yet.',
		planTitle: 'Whole adventure', planNote: 'Prepare sets the general’s units at once. You still send him to attack. Prepare all uses the largest army that general needs for one camp.',
		needTitle: 'Estimate for the whole adventure', needNote: 'For each unit this is the larger number: losses added across camps, or the most any general needs for one attack.',
		gens: 'Generals', loss: 'loss', sameGen: 'same general, wait until he returns',
		campOne: 'camp', campsMany: 'camps',
		missingLoss: '{n} camps have no loss data. Click “Get results” in the program again.',
		hiddenNote: '{n} hidden camps. Click “Hidden camps” to see them.',
		notFound: 'General “{name}” is not on this island.',
		star: '{name}: is in the star menu, not in the game. Units were not assigned.',
		task: '{name}: on a task, command was not sent.',
		sent: '{name}: sent {units}. You send him to attack.',
		opening: ' Opening the window.',
		short: '{name}: short of {what}. Command was not sent.',
		needLine: '{unit} (needs {need}, available {have})',
		lang: 'SL'
	}
};
function CS_t(key) {
	var pack = CS_I18N[CS_LANG] || CS_I18N.sl;
	return (pack[key] != null ? pack[key] : CS_I18N.sl[key]) || key;
}
function CS_tf(key, map) {
	var s = CS_t(key);
	for (var k in (map || {})) { s = s.split('{' + k + '}').join(String(map[k])); }
	return s;
}

var CS_data = null;
var CS_folder = null;
var CS_mapFile = null;
var CS_note = '';
var CS_showHidden = false;
var CS_mapOpen = true;
var CS_zoom = 1;
var CS_numScale = Math.max(0.5, Math.min(2.5, Number(CS_cfg.numScale) || 1));
var CS_popWin = null;
var CS_popLoader = null;
var CS_liftOn = false;
var CS_prepTimer = null;
var CS_prepSeen = 0;
var CS_pinned = false;
var CS_pinTimer = null;
var CS_armyAnchor = null;

function CS_save() {
	try {
		settings.settings[CS_KEY] = {};
		settings.store(CS_cfg, CS_KEY);
	} catch (e) { }
}

function CS_esc(s) {
	return String(s == null ? '' : s)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

function CS_nice(id) {
	return String(id || '').replace(/([a-z0-9])([A-Z])/g, '$1 $2');
}

function CS_units(units, icons) {
	var parts = [];
	for (var k in (units || {})) {
		if (!units[k]) { continue; }
		var icon = icons ? CS_unitIcon(k) : '';
		parts.push('<span class="cs-unit">' + icon + units[k] + ' × ' + CS_esc(CS_nice(k)) + '</span>');
	}
	return parts.join(' ');
}

function CS_sum(units) {
	var n = 0;
	for (var k in (units || {})) { n += Number(units[k]) || 0; }
	return n;
}

function CS_shortName(name) {
	return String(name || '').replace(/\s*\([^)]*\)/g, ' ').replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
}

function CS_general(a) {
	var name = CS_shortName(a.general_name) || CS_nice(a.general_base || a.general_id);
	return '<span class="cs-gencell">' + CS_specIcon(a) + ' <b>' + CS_esc(name) + '</b></span>';
}

var CS_typeIndex = null;

function CS_iconTry(names, px) {
	if (typeof getImageTag !== 'function') { return ''; }
	for (var i = 0; i < names.length; i++) {
		if (!names[i]) { continue; }
		try {
			var html = getImageTag(String(names[i]), px, px);
			if (html && html.indexOf('<img') >= 0) {
				return html.replace('<img', '<img class="cs-ico"');
			}
		} catch (e) { }
	}
	return '';
}

function CS_indexTypes() {
	if (CS_typeIndex) { return CS_typeIndex; }
	CS_typeIndex = {};
	try {
		var cols = game.zone.GetArmy(game.player.GetPlayerId()).GetSquadsCollection_vector();
		cols.forEach(function (item) {
			var t = String(item.GetType());
			if (t) { CS_typeIndex[t.toLowerCase()] = t; }
		});
	} catch (e) { }
	return CS_typeIndex;
}

function CS_unitIcon(id) {
	var key = String(id || '');
	var known = CS_indexTypes()[key.toLowerCase()];
	return CS_iconTry([known, key, key + '.png'], '20px');
}

function CS_specIcon(a) {
	var want = String((a && a.general_name) || '').toLowerCase();
	var base = String((a && (a.general_base || a.general_id)) || '').toLowerCase().replace(/\s+/g, '');
	try {
		var list = game.gi.mCurrentPlayerZone.GetSpecialists_vector();
		for (var i = 0; i < list.length; i++) {
			var spec = list[i];
			var n = '';
			try { n = String(spec.getName(false) || ''); } catch (e) { n = ''; }
			var flat = n.toLowerCase().replace(/\s+/g, '');
			var hit = (want && n.toLowerCase().indexOf(want) >= 0) || (base && flat.indexOf(base) >= 0);
			if (!hit) { continue; }
			var icon = '';
			try { icon = spec.getIconID(); } catch (e2) { }
			if (!icon) { try { icon = spec.getDefinition().icon_string; } catch (e3) { } }
			var tag = CS_iconTry([icon], '26px');
			if (tag) { return tag; }
		}
	} catch (e4) { }
	return CS_iconTry([a && a.general_base, a && a.general_id, 'icon_general.png'], '26px');
}

function CS_bestSol(c) {
	var sols = (c && c.solutions) || [];
	for (var i = 0; i < sols.length; i++) {
		if (sols[i].victory_percent == null || sols[i].victory_percent >= 100) { return sols[i]; }
	}
	return sols[0] || null;
}

function CS_attacker(s) {
	return (s && s.setup && s.setup.attackers && s.setup.attackers[0]) || null;
}

function CS_netLoss(s) {
	var src = (s && s.losses) || {};
	var out = {};
	for (var k in src) {
		var v = src[k];
		var n = (v && typeof v === 'object') ? Number(v.avg != null ? v.avg : v.max) : Number(v);
		if (!isFinite(n) || n <= 0) { continue; }
		out[k] = Math.ceil(n - 1e-9);
	}
	return out;
}

function CS_planHtml(data, includeHidden, withPrep) {
	var camps = (data && data.camps) || [];
	var rows = '';
	var lossSum = {};
	var attackMax = {};
	var gens = {};
	var shown = 0;
	var missing = 0;
	camps.forEach(function (c) {
		if (CS_isHidden(c) && !includeHidden) { return; }
		var s = CS_bestSol(c);
		var a = CS_attacker(s);
		if (!a) { return; }
		shown++;
		var num = CS_esc(CS_num(c));
		var gname = CS_shortName(a.general_name) || CS_nice(a.general_base || a.general_id || '');
		var gkey = String(a.general_id || gname);
		if (!gens[gkey]) { gens[gkey] = { name: gname, icon: CS_specIcon(a), camps: [] }; }
		gens[gkey].camps.push(num);
		var units = a.units || {};
		for (var uk in units) {
			var un = Number(units[uk]) || 0;
			if (un > (attackMax[uk] || 0)) { attackMax[uk] = un; }
		}
		var loss = CS_netLoss(s);
		var lossKeys = 0;
		for (var lk in loss) {
			lossKeys++;
			lossSum[lk] = (lossSum[lk] || 0) + loss[lk];
		}
		if (!lossKeys) { missing++; }
		var low = s.victory_percent != null && s.victory_percent < 100;
		var prep = '';
		if (withPrep) {
			prep = '<div><button type="button" class="cs-prep" data-general="' + CS_esc(gname) + '" data-units="' + CS_esc(JSON.stringify(units)) + '">' + CS_t('prepare') + '</button></div>';
		}
		var rowCls = CS_isHidden(c) ? ' class="is-hidden"' : '';
		rows += '<tr' + rowCls + ' data-num="' + num + '" data-loss="' + CS_esc(JSON.stringify(loss)) + '" data-units="' + CS_esc(JSON.stringify(units)) + '"><td class="cs-rank">' + num + '</td><td><div class="cs-gencell">' + CS_specIcon(a) + ' <b>' + CS_esc(gname) + '</b> ' +
			(low ? '<span class="cs-low">' + CS_esc(s.victory_percent) + '%</span>' : '<span class="cs-win">100%</span>') +
			prep + '</div></td><td>' + CS_units(units, true) +
			(lossKeys ? '<div class="cs-loss">' + CS_t('loss') + ' ' + CS_units(loss, true) + '</div>' : '') +
			'</td></tr>';
	});
	if (!shown) { return ''; }
	var genBits = '';
	for (var gk in gens) {
		var g = gens[gk];
		var note = g.camps.length > 1
			? '<span class="cs-low">' + CS_t('campsMany') + ' ' + g.camps.join(', ') + ' — ' + CS_t('sameGen') + '</span>'
			: '<span class="cs-type">' + CS_t('campOne') + ' ' + g.camps.join(', ') + '</span>';
		genBits += '<div class="cs-genline">' + g.icon + ' <b>' + CS_esc(g.name) + '</b> ' + note + '</div>';
	}
	var need = {};
	var nk;
	for (nk in lossSum) { need[nk] = lossSum[nk]; }
	for (nk in attackMax) { need[nk] = Math.max(need[nk] || 0, attackMax[nk] || 0); }
	var miss = missing ? '<p class="cs-plan-note">' + CS_tf('missingLoss', { n: missing }) + '</p>' : '';
	return '<section class="cs-plan">' +
		'<div class="cs-plan-title">' + CS_t('planTitle') + ' <button type="button" class="cs-prepall">' + CS_t('prepareAll') + '</button></div>' +
		'<p class="cs-plan-note">' + CS_t('planNote') + '</p>' +
		'<table class="cs-tbl cs-plan-tbl"><thead><tr><th>' + CS_t('camp') + '</th><th>' + CS_t('general') + '</th><th>' + CS_t('send') + '</th></tr></thead><tbody>' +
		rows + '</tbody></table>' +
		'<div class="cs-need-title">' + CS_t('needTitle') + '</div>' +
		'<div class="cs-need" id="cs-need">' + (CS_units(need, true) || '—') + '</div>' +
		'<p class="cs-plan-note">' + CS_t('needNote') + '</p>' +
		miss +
		'<div class="cs-need-title">' + CS_t('gens') + '</div>' + genBits +
		'</section>';
}

function CS_campKey(c) {
	return String(c.camp_id || c.tab || '');
}

function CS_num(c) {
	var camps = (CS_data && CS_data.map && CS_data.map.camps) || [];
	for (var i = 0; i < camps.length; i++) {
		if (camps[i].id === c.camp_id && camps[i].number != null) { return String(camps[i].number); }
	}
	return String((c.tab || '').replace(/^Camp\s*/i, ''));
}

function CS_hiddenList() {
	var name = (CS_data && CS_data.adventure) || CS_cfg.adventure || '';
	return (CS_cfg.hidden && CS_cfg.hidden[name]) || [];
}

function CS_isHidden(c) {
	var key = CS_campKey(c);
	var list = CS_hiddenList();
	return list.indexOf(key) >= 0 || list.indexOf(CS_num(c)) >= 0;
}

function CS_setHidden(c, hidden) {
	var name = (CS_data && CS_data.adventure) || CS_cfg.adventure || '';
	if (!name) { return; }
	if (!CS_cfg.hidden[name]) { CS_cfg.hidden[name] = []; }
	var key = CS_campKey(c);
	var list = CS_cfg.hidden[name].filter(function (x) { return x !== key && x !== CS_num(c); });
	if (hidden) {
		list.push(key);
		var num = CS_num(c);
		if (num && list.indexOf(num) < 0) { list.push(num); }
	}
	CS_cfg.hidden[name] = list;
	CS_save();
	CS_writeHiddenFile(list);
	CS_pushPop();
}

function CS_restoreAll() {
	var name = (CS_data && CS_data.adventure) || CS_cfg.adventure || '';
	if (name) { CS_cfg.hidden[name] = []; }
	CS_showHidden = false;
	CS_save();
	CS_writeHiddenFile([]);
	CS_pushPop();
	CS_render();
}

function CS_writeHiddenFile(list) {
	try {
		if (!CS_folder || !CS_cfg.adventure) { return; }
		var f = CS_folder.resolvePath(CS_cfg.adventure).resolvePath('hidden.json');
		var fs = new air.FileStream();
		fs.open(f, air.FileMode.WRITE);
		fs.writeUTFBytes(JSON.stringify({ hidden: list, hideNumbers: CS_cfg.hideNumbers !== false }));
		fs.close();
	} catch (e) { }
}

function CS_mergeHiddenFile() {
	try {
		if (!CS_folder || !CS_cfg.adventure) { return; }
		var f = CS_folder.resolvePath(CS_cfg.adventure).resolvePath('hidden.json');
		if (!f.exists) { return; }
		var j = JSON.parse(CS_readText(f));
		var list = j.hidden || [];
		var name = (CS_data && CS_data.adventure) || CS_cfg.adventure;
		CS_cfg.hidden[name] = list;
		CS_cfg.hidden[CS_cfg.adventure] = list;
		if (typeof j.hideNumbers === 'boolean') { CS_cfg.hideNumbers = j.hideNumbers; }
	} catch (e) { }
}

function CS_tableHtml(data, includeHidden, withPrep) {
	var camps = (data && data.camps) || [];
	if (!camps.length) { return '<div class="cs-empty">' + CS_t('noCamps') + '</div>'; }
	var hiddenCount = 0;
	var out = CS_planHtml(data, includeHidden, withPrep);
	camps.forEach(function (c) {
		var hidden = CS_isHidden(c);
		if (hidden) { hiddenCount++; }
		if (hidden && !includeHidden) { return; }
		var num = CS_esc(CS_num(c));
		var key = CS_esc(CS_campKey(c));
		out += '<section class="cs-card' + (hidden ? ' is-hidden' : '') + '" id="cs-camp-' + num + '">';
		out += '<table class="cs-top"><tbody><tr>';
		out += '<td class="cs-badge">' + num + '</td>';
		out += '<td class="cs-enemy">' + (CS_units(c.enemy_units) || '—') + '</td>';
		out += '<td class="cs-act"><button type="button" class="cs-hide" data-key="' + key + '" data-num="' + num + '" data-hidden="' + (hidden ? '1' : '0') + '">' + (hidden ? CS_t('show') : CS_t('hide')) + '</button></td>';
		out += '</tr></tbody></table>';
		var sols = c.solutions || [];
		if (!sols.length) {
			out += '<div class="cs-empty">' + CS_t('noSol') + '</div></section>';
			return;
		}
		out += '<table class="cs-tbl cs-detail"><thead><tr><th>#</th><th>' + CS_t('win') + '</th><th>' + CS_t('general') + '</th><th>' + CS_t('attack') + '</th><th>Σ</th></tr></thead><tbody>';
		sols.forEach(function (s) {
			var a = (s.setup && s.setup.attackers && s.setup.attackers[0]) || null;
			var win = s.victory_percent == null ? '' : s.victory_percent + '%';
			var low = s.victory_percent != null && s.victory_percent < 100;
			var total = s.unit_total != null ? s.unit_total : (a ? CS_sum(a.units) : '');
			var gname = a ? (CS_shortName(a.general_name) || CS_nice(a.general_base || a.general_id || '')) : '';
			var prep = '';
			if (withPrep && a) {
				prep = '<div><button type="button" class="cs-prep" data-general="' + CS_esc(gname) + '" data-units="' + CS_esc(JSON.stringify(a.units || {})) + '">' + CS_t('prepare') + '</button></div>';
			}
			out += '<tr>' +
				'<td class="cs-rank">' + CS_esc(s.rank || '') + '</td>' +
				'<td class="' + (low ? 'cs-low' : 'cs-win') + '">' + CS_esc(win) + '</td>' +
				'<td><div class="cs-gencell">' + (a ? CS_general(a) : '—') + prep + '</div></td>' +
				'<td>' + (a ? CS_units(a.units, true) : CS_esc(s.row_text || '')) + '</td>' +
				'<td class="cs-sum">' + CS_esc(total) + '</td></tr>';
		});
		out += '</tbody></table></section>';
	});
	if (hiddenCount && !includeHidden) {
		out += '<div class="cs-hidden-note">' + CS_tf('hiddenNote', { n: hiddenCount }) + '</div>';
	}
	return out;
}

// ---------- file access (AIR) ----------

function CS_readText(file) {
	var fs = new air.FileStream();
	fs.open(file, air.FileMode.READ);
	var s = fs.readUTFBytes(fs.bytesAvailable);
	fs.close();
	return s;
}

function CS_dataUri(file, mime) {
	var fs = new air.FileStream();
	fs.open(file, air.FileMode.READ);
	var ba = new air.ByteArray();
	fs.readBytes(ba, 0, fs.bytesAvailable);
	fs.close();
	ba.position = 0;
	var bin = '';
	var n = ba.length;
	for (var i = 0; i < n; i++) { bin += String.fromCharCode(ba.readUnsignedByte()); }
	return 'data:' + mime + ';base64,' + btoa(bin);
}

function CS_listAdventures(dir) {
	var list = [];
	try {
		dir.getDirectoryListing().forEach(function (f) {
			if (f.isDirectory && f.name.indexOf('_') !== 0 && f.resolvePath('results.json').exists) {
				list.push(f.name);
			}
		});
	} catch (e) { CS_note = 'Mape ni mogoče prebrati: ' + e.message; }
	return list.sort();
}

function CS_resolveRoot(dir) {
	var pick = null;
	if (dir.resolvePath('results.json').exists) {
		pick = dir.name;
		dir = dir.parent;
	}
	var advs = CS_listAdventures(dir);
	if (advs.length === 0 && dir.resolvePath('rezultati').exists) {
		dir = dir.resolvePath('rezultati');
		advs = CS_listAdventures(dir);
	}
	if (pick && advs.indexOf(pick) < 0) { advs.push(pick); }
	return { root: dir, adventures: advs, pick: pick };
}

function CS_names(dir) {
	var n = [];
	try { dir.getDirectoryListing().forEach(function (f) { n.push(f.name); }); } catch (e) { }
	return n.slice(0, 12).join(', ');
}

function CS_openFolder(path) {
	try {
		CS_folder = new air.File();
		CS_folder.nativePath = path;
		return CS_folder.exists && CS_folder.isDirectory;
	} catch (e) { return false; }
}

function CS_pickMapFile(dir) {
	var names = ['map.jpg', 'map.jpeg', 'map.png'];
	for (var i = 0; i < names.length; i++) {
		var f = dir.resolvePath(names[i]);
		if (f.exists) { return f; }
	}
	return null;
}

function CS_locateMap(dir) {
	var local = CS_pickMapFile(dir);
	if (local) { return local; }
	var want = (CS_data && CS_data.adventure) || dir.name;
	try {
		dir.parent.getDirectoryListing().forEach(function (f) {
			if (local || !f.isDirectory || f.nativePath === dir.nativePath) { return; }
			var pic = CS_pickMapFile(f);
			if (!pic) { return; }
			var same = f.name === dir.name || f.name === want;
			if (!same) {
				try {
					var j = JSON.parse(CS_readText(f.resolvePath('results.json')));
					same = j.adventure === want;
				} catch (e) { same = false; }
			}
			if (same) { local = pic; }
		});
	} catch (e) { }
	return local;
}

function CS_load(adventure) {
	CS_data = null;
	CS_mapFile = null;
	try {
		var dir = CS_folder.resolvePath(adventure);
		CS_data = JSON.parse(CS_readText(dir.resolvePath('results.json')));
		CS_mapFile = CS_locateMap(dir);
		CS_cfg.adventure = adventure;
		CS_mergeHiddenFile();
		CS_save();
		CS_note = 'Shranjeno ' + (CS_data.saved || '?') + (CS_data.camps ? ' · ' + CS_data.camps.length + ' taborov' : '');
		if (CS_mapFile && CS_mapFile.parent.nativePath !== dir.nativePath) {
			CS_note += ' · zemljevid je bil v drugi mapi, prikazan je od tam';
		}
	} catch (e) { CS_note = 'results.json ni berljiv: ' + e.message; }
}

// ---------- window ----------

function CS_css() {
	var s = document.getElementById('csCSS');
	if (!s) {
		s = document.createElement('style');
		s.id = 'csCSS';
		document.head.appendChild(s);
	}
	var M = '#' + CS_MODAL;
	s.textContent = [
		M + '{pointer-events:none !important;position:static !important;width:0 !important;height:0 !important;overflow:visible !important;}',
		M + ' .modal-dialog{pointer-events:auto !important;position:fixed !important;top:8px;right:12px;left:auto;bottom:auto;margin:0 !important;width:420px;max-width:96vw;max-height:calc(100vh - 16px) !important;overflow:hidden !important;}',
		M + ' .modal-content{max-height:calc(100vh - 16px) !important;overflow:hidden !important;display:flex !important;flex-direction:column !important;}',
		M + ' .modal-content,' + M + ' .modal-header,' + M + ' .modal-body,' + M + ' .modal-footer{background:#221c16 !important;color:#f4efe6 !important;border-color:#3d3428 !important;}',
		M + ' .modal-header{cursor:move;border-bottom:1px solid #3d3428 !important;flex:0 0 auto !important;}',
		M + ' .modal-body{position:relative !important;flex:1 1 auto !important;min-height:0 !important;overflow:hidden !important;}',
		M + ' .modal-footer{flex:0 0 auto !important;display:block !important;border-top:1px solid #3d3428 !important;text-align:right !important;}',
		M + ' .btnClose{background:#e4c27a !important;color:#1a140e !important;border:0 !important;border-radius:4px !important;padding:6px 16px !important;font-weight:700 !important;}',
		M + ' .cs-head{position:relative !important;min-height:28px;}',
		M + ' .cs-pin{position:absolute !important;right:4px;top:0;background:#3a3126 !important;color:#e4c27a !important;border:1px solid #e4c27a !important;border-radius:4px;padding:3px 10px !important;cursor:pointer;font:700 12px/1.2 Arial,sans-serif !important;}',
		M + ' .cs-pin.is-on{background:#e4c27a !important;color:#1a140e !important;}',
		M + ' .cs-maptools button{margin:0 4px 0 0 !important;background:#3a3126 !important;color:#f4efe6 !important;border:1px solid #e4c27a !important;border-radius:4px;padding:3px 8px !important;}',
		M + ' .cs-bar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;}',
		M + ' .cs-bar button{margin:0 !important;padding:5px 10px !important;cursor:pointer;color:#1a140e !important;background:#e4c27a !important;border:0 !important;border-radius:4px !important;font:600 12px/1.2 Arial,sans-serif !important;}',
		M + ' .cs-bar button.cs-ghost{background:#3a3126 !important;color:#f4efe6 !important;}',
		M + ' .cs-in{color:#1a140e !important;background:#fffaf3 !important;border:1px solid #c6a15a !important;border-radius:4px;padding:4px 6px;}',
		M + ' .cs-note{font:12px/1.4 Arial,sans-serif;margin:8px 0 0;color:#d9cbb3 !important;}',
		M + ' .cs-pastebox{margin-top:8px;}',
		M + ' .cs-mapbox{position:relative !important;z-index:8 !important;margin:0 0 8px;background:#140f0c;border:1px solid #5c4c34;border-radius:6px;padding:8px;text-align:center;}',
		M + ' .cs-res{position:absolute !important;left:0 !important;right:0 !important;bottom:0 !important;overflow-y:scroll !important;overflow-x:hidden !important;}',
		M + ' .cs-maptools{text-align:left !important;margin:0 0 6px !important;}',
		M + ' .cs-title{font:600 15px/1.2 Georgia,serif;color:#f3e6cc !important;letter-spacing:.02em;margin:0 0 8px;}',
		M + ' .cs-mapview{height:220px;overflow:auto !important;text-align:left !important;background:#100c09;}',
		M + ' .cs-mapview canvas,' + M + ' .cs-mapview img{max-width:none !important;max-height:none !important;display:block;}',
		M + ' .cs-loss{color:#e2b15a !important;font:12px/1.3 Arial,sans-serif !important;margin-top:3px;}',
		M + ' .cs-gencell{display:block !important;line-height:1.25 !important;}',
		M + ' .cs-gencell .cs-prep{display:block !important;margin:3px 0 0 0 !important;}',
		M + ' .cs-prep{margin-left:0 !important;background:#3a3126 !important;color:#f4efe6 !important;border:1px solid #e4c27a !important;border-radius:4px;padding:2px 8px;cursor:pointer;}',
		M + ' .cs-prepall{margin-left:8px !important;background:#3a3126 !important;color:#f4efe6 !important;border:1px solid #e4c27a !important;border-radius:4px;padding:2px 8px;cursor:pointer;font:600 12px/1.2 Arial,sans-serif !important;}',
		M + ' .cs-top,' + M + ' .cs-tbl{display:table !important;width:100% !important;border-collapse:collapse !important;table-layout:fixed !important;margin:0 0 4px;}',
		M + ' .cs-top tr,' + M + ' .cs-tbl tr{display:table-row !important;width:auto !important;}',
		M + ' .cs-top td,' + M + ' .cs-tbl th,' + M + ' .cs-tbl td{display:table-cell !important;vertical-align:middle !important;text-align:left !important;padding:4px 6px !important;white-space:normal !important;}',
		M + ' .cs-tbl th{font:600 11px/1.2 Arial,sans-serif !important;letter-spacing:.04em;text-transform:uppercase;color:#1a140e !important;background:#c6a15a !important;}',
		M + ' .cs-detail th:nth-child(1),' + M + ' .cs-detail td:nth-child(1){width:36px !important;}',
		M + ' .cs-detail th:nth-child(2),' + M + ' .cs-detail td:nth-child(2){width:64px !important;}',
		M + ' .cs-detail th:nth-child(5),' + M + ' .cs-detail td:nth-child(5){width:48px !important;text-align:right !important;}',
		M + ' .cs-plan-tbl th:nth-child(1),' + M + ' .cs-plan-tbl td:nth-child(1){width:52px !important;}',
		M + ' .cs-plan-tbl th:nth-child(2),' + M + ' .cs-plan-tbl td:nth-child(2){width:38% !important;}',
		M + ' .cs-plan{margin:0 0 12px;background:#1c1814;border:1px solid #c6a15a;border-radius:6px;padding:8px;}',
		M + ' .cs-plan-title,' + M + ' .cs-need-title{font:600 13px/1.3 Georgia,serif;color:#f3e6cc !important;margin:8px 0 4px;}',
		M + ' .cs-plan-note{color:#d9cbb3 !important;font:12px/1.4 Arial,sans-serif;margin:0 0 6px;}',
		M + ' .cs-unit{display:inline-block !important;margin:0 10px 4px 0 !important;white-space:nowrap !important;color:#f4efe6 !important;}',
		M + ' .cs-genline{margin:2px 0;color:#f4efe6 !important;}',
		M + ' img.cs-ico{width:22px !important;height:22px !important;vertical-align:middle !important;margin:0 4px 0 0 !important;}',
		M + ' .cs-card{margin-top:8px;background:#2b241c;border:1px solid #3d3428;border-radius:6px;padding:8px;}',
		M + ' .cs-badge{width:32px !important;text-align:center !important;color:#f3e6cc !important;background:#1a140e !important;border:1px solid #e4c27a;border-radius:13px;font:700 12px/26px Arial,sans-serif !important;padding:0 !important;}',
		M + ' .cs-enemy{color:#f4efe6 !important;font:13px/1.35 Arial,sans-serif !important;}',
		M + ' .cs-act{width:84px !important;text-align:right !important;}',
		M + ' .cs-hide{background:#3a3126 !important;color:#f4efe6 !important;border:1px solid #5c4c34 !important;border-radius:4px;padding:3px 8px;cursor:pointer;}',
		M + ' .cs-tbl td{border-top:1px solid rgba(255,255,255,.06);color:#f4efe6 !important;font:13px/1.35 Arial,sans-serif !important;}',
		M + ' .cs-card b,' + M + ' .cs-type{color:#f4efe6 !important;}',
		M + ' .cs-type{color:#cbbfa8 !important;font-weight:400;}',
		M + ' .cs-rank{color:#e4c27a !important;font-weight:700;}',
		M + ' .cs-win{color:#b7e0b0 !important;}',
		M + ' .cs-low{color:#e2b15a !important;}',
		M + ' .cs-sum{text-align:right !important;color:#e4c27a !important;font-weight:700;}',
		M + ' .cs-empty,' + M + ' .cs-hidden-note{color:#d9cbb3 !important;font:12px/1.4 Arial,sans-serif;padding:4px 0;}',
		M + ' .cs-card.is-hidden{opacity:.55;}'
	].join('');
}

function CS_fit() {
	var $m = $('#' + CS_MODAL);
	if (!$m.length) { return; }
	var vh = window.innerHeight || (document.documentElement && document.documentElement.clientHeight) || 720;
	var max = Math.max(280, vh - 16);
	var dialog = $m.find('.modal-dialog')[0];
	var content = $m.find('.modal-content')[0];
	var header = $m.find('.modal-header')[0];
	var footer = $m.find('.modal-footer')[0];
	var body = $m.find('.modal-body')[0];
	function pin(el, prop, value) {
		if (el) { el.style.setProperty(prop, value, 'important'); }
	}
	pin(dialog, 'max-height', max + 'px');
	pin(dialog, 'overflow', 'hidden');
	pin(content, 'max-height', max + 'px');
	pin(content, 'overflow', 'hidden');
	var head = header ? header.offsetHeight : 0;
	var foot = footer && footer.offsetHeight ? footer.offsetHeight : 48;
	var bodyMax = max - head - foot - 4;
	if (bodyMax < 80) { bodyMax = 80; }
	pin(body, 'height', bodyMax + 'px');
	pin(body, 'max-height', bodyMax + 'px');
	pin(body, 'min-height', '0');
	pin(body, 'overflow', 'hidden');
	pin(body, 'position', 'relative');
	var map = $m.find('.cs-mapbox')[0];
	var res = $m.find('.cs-res')[0];
	var top = 0;
	if (map && map.offsetHeight && $m.find('.cs-mapbox').is(':visible')) {
		top = map.offsetTop + map.offsetHeight + 8;
	}
	if (res) {
		pin(res, 'position', 'absolute');
		pin(res, 'left', '0');
		pin(res, 'right', '0');
		pin(res, 'top', top + 'px');
		pin(res, 'bottom', '0');
		pin(res, 'overflow-y', 'scroll');
		pin(res, 'overflow-x', 'hidden');
	}
	if (dialog) {
		var top = parseFloat(dialog.style.top || '');
		if (isNaN(top) || top < 8) { pin(dialog, 'top', '8px'); }
	}
	CS_applyClip();
}

function CS_host() {
	try { return window.legacyHtmlLoader || window.htmlLoader || null; } catch (e) { return null; }
}

function CS_applyClip() {
	if (!CS_pinned) { return; }
	var host = CS_host();
	var dialog = document.querySelector('#' + CS_MODAL + ' .modal-dialog');
	if (!host || !dialog) { return; }
	var rect = dialog.getBoundingClientRect();
	var margin = 8;
	var x = Math.max(0, Math.floor(rect.left) - margin);
	var y = Math.max(0, Math.floor(rect.top) - margin);
	var w = Math.max(40, Math.ceil(rect.width) + margin * 2);
	var h = Math.max(40, Math.ceil(rect.height) + margin * 2);
	var box = null;
	try { if (air && air.Rectangle) { box = new air.Rectangle(x, y, w, h); } } catch (e0) { box = null; }
	if (!box) {
		try { box = new window.runtime.flash.geom.Rectangle(x, y, w, h); } catch (e1) { box = null; }
	}
	if (!box) {
		try {
			if (window.FloatingModalHost) { FloatingModalHost.activate($('#' + CS_MODAL)); }
		} catch (e2) { }
		return;
	}
	try {
		var stage = window.nativeWindow.stage;
		host.width = Math.max(w, stage.stageWidth || w);
		host.height = Math.max(h, stage.stageHeight || h);
		host.scrollRect = box;
		host.x = x;
		host.y = y;
		CS_applyClip.failed = false;
	} catch (e) {
		if (!CS_applyClip.failed) {
			CS_applyClip.failed = true;
			CS_note = 'Pripni ni uspel: ' + e.message;
			try { $('#' + CS_MODAL + ' .cs-note').text(CS_note); } catch (e2) { }
		}
	}
}

function CS_clearClip() {
	var host = CS_host();
	if (!host) { return; }
	try {
		host.scrollRect = null;
		host.x = 0;
		host.y = 0;
		var stage = window.nativeWindow.stage;
		if (stage) {
			host.width = stage.stageWidth;
			host.height = stage.stageHeight;
		}
	} catch (e) { }
}

function CS_setPinned(on) {
	CS_pinned = !!on;
	var $b = $('#' + CS_MODAL + ' .cs-pin');
	$b.toggleClass('is-on', CS_pinned);
	$b.text(CS_pinned ? CS_t('pinned') : CS_t('pin'));
	if (CS_pinTimer) { clearInterval(CS_pinTimer); CS_pinTimer = null; }
	if (!CS_pinned) {
		CS_clearClip();
		CS_note = 'Odpeto.';
		$('#' + CS_MODAL + ' .cs-note').text(CS_note);
		return;
	}
	if (!CS_host()) {
		CS_pinned = false;
		$b.removeClass('is-on').text('Pripni');
		CS_note = 'Pripni ni uspel: sloj igre ni dosegljiv.';
		$('#' + CS_MODAL + ' .cs-note').text(CS_note);
		return;
	}
	CS_applyClip();
	setTimeout(CS_applyClip, 60);
	CS_pinTimer = setInterval(CS_applyClip, 400);
}

function CS_drag() {
	var $d = $('#' + CS_MODAL + ' .modal-dialog');
	var ox = 0, oy = 0;
	$('#' + CS_MODAL + ' .modal-header').on('mousedown', function (e) {
		if ($(e.target).is('button, select, input, textarea')) { return; }
		e.preventDefault();
		var off = $d.offset();
		$d.css({ left: off.left + 'px', top: off.top + 'px', right: 'auto' });
		ox = e.clientX; oy = e.clientY;
		$(document).on('mousemove.csdrag', function (ev) {
			var o = $d.offset();
			$d.css({ left: (o.left + ev.clientX - ox) + 'px', top: (o.top + ev.clientY - oy) + 'px' });
			ox = ev.clientX; oy = ev.clientY;
			CS_applyClip();
		});
		$(document).on('mouseup.csdrag', function () { $(document).off('.csdrag'); });
	});
}

function CS_disarmFocus() {
	try {
		var C = $.fn.modal.Constructor.prototype;
		if (!CS_disarmFocus.saved) {
			CS_disarmFocus.saved = C.enforceFocus || function () {};
		}
		C.enforceFocus = function () {};
		if (C._enforceFocus) { C._enforceFocus = function () {}; }
	} catch (e) { }
	try { $(document).off('focusin.modal focusin.bs.modal'); } catch (e2) { }
}

function CS_unlock() {
	CS_pinned = false;
	if (CS_pinTimer) { clearInterval(CS_pinTimer); CS_pinTimer = null; }
	CS_clearClip();
	CS_disarmFocus();
	try {
		if (CS_disarmFocus.saved && $.fn.modal) {
			$.fn.modal.Constructor.prototype.enforceFocus = CS_disarmFocus.saved;
		}
	} catch (e) { }
	var $m = $('#' + CS_MODAL);
	try { $m.hide(); } catch (e2) { }
	$m.remove();
	var other = $('div.modal:visible').not('#' + CS_MODAL);
	if (!other.length) {
		$('.modal-backdrop').remove();
		$('body').removeClass('modal-open');
		try {
			document.body.style.overflow = '';
			document.body.style.paddingRight = '';
		} catch (e3) { }
	}
	try { $(document).off('focusin.modal focusin.bs.modal'); } catch (e4) { }
}

function CS_Menu() {
	$("div[role='dialog']:not(#" + CS_MODAL + "):visible").modal("hide");
	$('#' + CS_MODAL).remove();
	CS_css();
	createModalWindow(CS_MODAL, 'Camp Solutions');
	$('#' + CS_MODAL).attr('data-floating-modal', 'false');

	$('#' + CS_MODAL + ' .modal-header').html(
		'<div class="container-fluid">' +
		'<div class="cs-head"><div class="cs-title">Camp Solutions</div>' +
		'<button type="button" class="cs-pin" title="' + CS_esc(CS_t('pinTitle')) + '">' + CS_t('pin') + '</button>' +
		'<button type="button" class="cs-lang">' + CS_t('lang') + '</button></div>' +
		'<div class="cs-bar">' +
		'<button type="button" class="cs-pick">' + CS_t('pick') + '</button>' +
		'<select class="cs-adv cs-in" style="min-width:180px;"></select>' +
		'<button type="button" class="cs-ghost cs-mapbtn">' + CS_t('map') + '</button>' +
		'<button type="button" class="cs-ghost cs-hiddenbtn">' + CS_t('hiddenCamps') + '</button>' +
		'<button type="button" class="cs-ghost cs-restore">' + CS_t('restore') + '</button>' +
		'<button type="button" class="cs-ghost cs-nums">' + CS_t('numsHidden') + '</button>' +
		'<button type="button" class="cs-ghost cs-paste">' + CS_t('paste') + '</button>' +
		'<button type="button" class="cs-close">' + CS_t('close') + '</button></div>' +
		'<div class="cs-note"></div>' +
		'<div class="cs-pastebox">' +
		'<textarea class="cs-in cs-text" rows="5" style="width:100%;box-sizing:border-box;"></textarea>' +
		'<button type="button" class="cs-pasteok">' + CS_t('showBtn') + '</button></div>' +
		'</div>'
	);
	$('#' + CS_MODAL + 'Data').html('<div class="cs-mapbox" style="display:none;"></div><div class="cs-res"></div>');
	$('#' + CS_MODAL + ' .cs-pastebox').hide();

	var $m = $('#' + CS_MODAL);
	$m.find('.cs-pick').click(function () {
		try {
			var dir = new air.File();
			dir.addEventListener('select', function (e) {
				CS_cfg.folder = e.target.nativePath;
				CS_save();
				CS_init();
			});
			dir.browseForDirectory('Izberi mapo rezultati');
		} catch (e) { CS_note = 'Izbira mape ni na voljo: ' + e.message + '. Uporabi «Prilepi JSON».'; CS_render(); }
	});
	$m.find('.cs-adv').on('change', function () {
		if ($(this).val()) { CS_load($(this).val()); CS_render(); }
	});
	$m.find('.cs-paste').click(function () { $m.find('.cs-pastebox').toggle(); CS_fit(); });
	$m.find('.cs-pasteok').click(function () {
		try {
			CS_data = JSON.parse($m.find('.cs-text').val());
			CS_mapFile = null;
			CS_note = 'Prilepljeno: ' + (CS_data.adventure || '?');
		} catch (e) { CS_data = null; CS_note = 'Neveljaven JSON: ' + e.message; }
		CS_render();
	});
	$m.find('.cs-mapbtn').click(function () {
		CS_mapOpen = !CS_mapOpen;
		var $mp = $m.find('.cs-mapbox');
		if (!CS_mapOpen) { $mp.hide(); return; }
		CS_showMap($mp, 220);
	});
	$m.find('.cs-hiddenbtn').click(function () {
		CS_showHidden = !CS_showHidden;
		$(this).text(CS_showHidden ? CS_t('hideBeaten') : CS_t('hiddenCamps'));
		CS_render();
	});
	$m.find('.cs-restore').click(function () { CS_restoreAll(); });
	$m.find('.cs-nums').click(function () {
		CS_cfg.hideNumbers = CS_cfg.hideNumbers === false;
		CS_save();
		CS_writeHiddenFile(CS_hiddenList());
		CS_pushPop();
		CS_render();
	});
	$m.on('click', '.cs-zoomin', function () { CS_zoom = Math.min(4, (CS_zoom || 1) * 1.5); CS_applyZoom($m); });
	$m.on('click', '.cs-zoomout', function () { CS_zoom = Math.max(1, (CS_zoom || 1) / 1.5); CS_applyZoom($m); });
	$m.on('click', '.cs-zoomreset', function () { CS_zoom = 1; CS_applyZoom($m); });
	$m.on('click', '.cs-numin, .cs-numout', function () {
		var step = $(this).hasClass('cs-numin') ? 0.2 : -0.2;
		CS_numScale = Math.max(0.5, Math.min(2.5, Math.round(((CS_numScale || 1) + step) * 10) / 10));
		CS_cfg.numScale = CS_numScale;
		CS_save();
		var $mp = $m.find('.cs-mapbox');
		if ($mp.is(':visible')) { CS_showMap($mp, 220); }
	});
	$m.find('.cs-pin').click(function () {
		CS_setPinned(!CS_pinned);
	});
	$m.find('.cs-lang').click(function () {
		CS_LANG = CS_LANG === 'en' ? 'sl' : 'en';
		CS_cfg.lang = CS_LANG;
		CS_save();
		CS_Menu();
	});
	$m.on('click', '.cs-prepall', function () {
		var msg = CS_prepareAll();
		CS_note = msg;
		$m.find('.cs-note').text(msg);
	});
	$m.on('click', '.cs-prep', function () {
		var units = {};
		try { units = JSON.parse($(this).attr('data-units') || '{}'); } catch (e) { }
		var msg = CS_prepare({ name: $(this).attr('data-general') || '', units: units });
		CS_note = msg;
		$m.find('.cs-note').text(msg);
	});
	$m.find('.cs-close').click(function () {
		try { $m.modal('hide'); } catch (e) { CS_unlock(); return; }
		setTimeout(function () {
			if ($('#' + CS_MODAL).is(':visible')) { CS_unlock(); }
		}, 120);
	});
	$m.on('click', '.cs-hide', function () {
		var key = $(this).attr('data-key');
		var camps = (CS_data && CS_data.camps) || [];
		for (var i = 0; i < camps.length; i++) {
			if (CS_campKey(camps[i]) === key) {
				CS_setHidden(camps[i], !CS_isHidden(camps[i]));
				break;
			}
		}
		CS_render();
	});

	CS_drag();
	CS_init();
	CS_disarmFocus();
	var $modal = $('#' + CS_MODAL);
	try {
		$modal.modal({ backdrop: false, keyboard: true, show: true });
	} catch (e) {
		try { $modal.modal('show'); } catch (e2) { }
	}
	setTimeout(function () {
		$('.modal-backdrop').remove();
		$('body').removeClass('modal-open');
		CS_disarmFocus();
		CS_fit();
	}, 0);
	setTimeout(function () {
		$('.modal-backdrop').remove();
		$('body').removeClass('modal-open');
		CS_fit();
	}, 300);
	$(window).off('resize.csfit').on('resize.csfit', CS_fit);
	CS_fit();
	CS_setPinned(true);
	$modal.on('click', '[data-dismiss="modal"], [data-dismiss], .close', function () {
		setTimeout(CS_unlock, 30);
	});
	$modal.on('hidden.bs.modal hidden', function () {
		setTimeout(CS_unlock, 0);
	});
}

function CS_isWebp(file) {
	try {
		var fs = new air.FileStream();
		fs.open(file, air.FileMode.READ);
		var head = fs.readUTFBytes(12);
		fs.close();
		return head.substr(0, 4) === 'RIFF' && head.substr(8, 4) === 'WEBP';
	} catch (e) { return false; }
}

function CS_mapUri() {
	if (!CS_mapFile) { return ''; }
	var ext = CS_mapFile.extension ? String(CS_mapFile.extension).toLowerCase() : 'jpg';
	var mime = ext === 'png' ? 'image/png' : 'image/jpeg';
	try { return CS_dataUri(CS_mapFile, mime); } catch (e) { return ''; }
}

function CS_showMap($box, maxH) {
	$box.empty().show();
	$box.append(
		'<div class="cs-maptools">' +
		'<button type="button" class="cs-zoomin" title="Povečaj zemljevid">+</button>' +
		'<button type="button" class="cs-zoomout" title="Pomanjšaj zemljevid">−</button>' +
		'<button type="button" class="cs-zoomreset">Original</button>' +
		'<button type="button" class="cs-numout" title="Manjše številke taborov">Št −</button>' +
		'<button type="button" class="cs-numin" title="Večje številke taborov">Št +</button></div>' +
		'<div class="cs-mapview"></div>'
	);
	var $view = $box.find('.cs-mapview');
	if (!CS_mapFile) {
		$view.text('Za to avanturo ni zemljevida. V programu klikni «Shrani zemljevid» (shrani se v isto mapo kot rezultati).');
		return;
	}
	if (CS_isWebp(CS_mapFile)) {
		$view.text('Zemljevid je WebP, odjemalec ga ne prikaže. Shrani ga znova z novim programom — naredi pravi JPEG.');
		return;
	}
	var uri = CS_mapUri();
	if (!uri) { $view.text('Zemljevida ni mogoče prebrati.'); return; }
	CS_paintInto($view, uri, maxH || 220);
}

function CS_applyZoom($root) {
	var z = CS_zoom || 1;
	$root.find('.cs-mapview canvas, .cs-mapview img').each(function () {
		var w = Number(this.getAttribute('data-fit-w')) || this.width || 0;
		var h = Number(this.getAttribute('data-fit-h')) || this.height || 0;
		if (!w || !h) { return; }
		this.style.width = Math.round(w * z) + 'px';
		this.style.height = Math.round(h * z) + 'px';
		this.style.maxWidth = 'none';
		this.style.maxHeight = 'none';
	});
}

function CS_pinSkip(c) {
	if (CS_cfg.hideNumbers === false) { return false; }
	var hidden = {};
	CS_hiddenList().forEach(function (k) { hidden[String(k)] = 1; });
	((CS_data && CS_data.camps) || []).forEach(function (camp) {
		if (!CS_isHidden(camp)) { return; }
		hidden[CS_campKey(camp)] = 1;
		hidden[CS_num(camp)] = 1;
		if (camp.camp_id) { hidden[String(camp.camp_id)] = 1; }
	});
	return !!(hidden[c.id] || hidden[String(c.number)]);
}

function CS_paintInto($box, uri, maxH) {
	var canvas = document.createElement('canvas');
	canvas.style.maxHeight = maxH + 'px';
	$box.append(canvas);
	var img = new Image();
	img.onload = function () {
		var scale = Math.min(1, maxH / img.height, ($box.width() || 680) / img.width);
		canvas.width = Math.max(1, Math.round(img.width * scale));
		canvas.height = Math.max(1, Math.round(img.height * scale));
		var g = canvas.getContext('2d');
		g.drawImage(img, 0, 0, canvas.width, canvas.height);
		var map = (CS_data && CS_data.map) || {};
		var sw = map.width || img.width;
		var sh = map.height || img.height;
		var hidden = {};
		CS_hiddenList().forEach(function (k) { hidden[k] = 1; });
		(map.camps || []).forEach(function (c) {
			if (c.x == null || c.y == null) { return; }
			if (CS_pinSkip(c)) { return; }
			var x = c.x / sw * canvas.width;
			var y = c.y / sh * canvas.height;
			var r = Math.max(12, Math.round(Math.max(34, canvas.width * 0.07) * (CS_numScale || 1)));
			g.beginPath();
			g.arc(x, y, r, 0, Math.PI * 2);
			g.fillStyle = 'rgba(22,16,10,0.92)';
			g.fill();
			g.lineWidth = Math.max(3, Math.round(r * 0.12));
			g.strokeStyle = '#e4c27a';
			g.stroke();
			g.fillStyle = '#f7f1e6';
			g.font = '700 ' + Math.round(r) + 'px Arial';
			g.textAlign = 'center';
			g.textBaseline = 'middle';
			g.fillText(String(c.number), x, y + 0.5);
		});
		canvas.setAttribute('data-fit-w', String(canvas.width));
		canvas.setAttribute('data-fit-h', String(canvas.height));
		CS_applyZoom($box.closest('.cs-mapbox').length ? $box.closest('.cs-mapbox') : $(canvas).parent());
		CS_fit();
	};
	img.onerror = function () { $box.text('Zemljevida ni mogoče narisati.'); };
	img.src = uri;
}

function CS_popCss() {
	return 'html,body{height:100%;overflow:hidden;}' +
		'body{margin:0;background:#1a1612;color:#f4efe6;font:13px/1.4 Arial,sans-serif;}' +
		'#cs-top{position:absolute;left:0;right:0;top:0;z-index:5;background:#1a1612;}' +
		'#list{position:absolute;left:0;right:0;bottom:0;overflow:auto;padding:10px 12px 24px;}' +
		'header.cs-bar{background:#221c16;padding:10px 12px 8px;border-bottom:1px solid #3d3428;}' +
		'h1{font:600 16px/1.2 Georgia,serif;margin:0 0 4px;color:#f3e6cc;}' +
		'#cs-pin{float:right;background:#e4c27a;color:#1a140e;border:0;border-radius:4px;padding:4px 10px;font-weight:700;cursor:pointer;}' +
		'#cs-pin.off{background:#3a3126;color:#e4c27a;border:1px solid #e4c27a;}' +
		'header.cs-bar p{margin:0;color:#d9cbb3;font-size:12px;}' +
		'.map{background:#140f0c;border:1px solid #5c4c34;border-radius:6px;padding:8px;margin:8px 12px;}' +
		'.cs-maptools{margin:0 0 6px;}' +
		'.cs-maptools button{margin:0 4px 0 0;background:#3a3126;color:#f4efe6;border:1px solid #5c4c34;border-radius:4px;padding:3px 8px;cursor:pointer;}' +
		'.cs-mapview{height:260px;overflow:auto;background:#100c09;text-align:left;}' +
		'.cs-mapview canvas,.cs-mapview img{max-width:none;max-height:none;display:block;}' +
		'.cs-loss{color:#e2b15a;font-size:12px;margin-top:3px;}' +
		'.cs-prep{margin-left:6px;background:#3a3126;color:#f4efe6;border:1px solid #e4c27a;border-radius:4px;padding:2px 8px;cursor:pointer;}' +
		'.cs-card{margin-top:8px;background:#2b241c;border:1px solid #3d3428;border-radius:6px;padding:8px;}' +
		'table.cs-top,table.cs-tbl{width:100%;border-collapse:collapse;table-layout:fixed;margin:0 0 4px;}' +
		'.cs-top td,.cs-tbl th,.cs-tbl td{padding:4px 6px;vertical-align:middle;text-align:left;}' +
		'.cs-tbl th{background:#c6a15a;color:#1a140e;font:600 11px/1.2 Arial,sans-serif;letter-spacing:.04em;text-transform:uppercase;}' +
		'.cs-tbl th:nth-child(1),.cs-detail td:nth-child(1){width:36px;}' +
		'.cs-detail th:nth-child(2),.cs-detail td:nth-child(2){width:72px;}' +
		'.cs-detail th:nth-child(5),.cs-detail td:nth-child(5){width:48px;text-align:right;}' +
		'.cs-plan{margin:0 0 12px;background:#1c1814;border:1px solid #c6a15a;border-radius:6px;padding:8px;}' +
		'.cs-plan-title,.cs-need-title{font:600 13px/1.3 Georgia,serif;color:#f3e6cc;margin:8px 0 4px;}' +
		'.cs-plan-note{color:#d9cbb3;font-size:12px;margin:0 0 6px;}' +
		'.cs-plan-tbl th:nth-child(1),.cs-plan-tbl td:nth-child(1){width:52px;}' +
		'.cs-plan-tbl th:nth-child(2),.cs-plan-tbl td:nth-child(2){width:38%;}' +
		'.cs-unit{display:inline-block;margin:0 10px 4px 0;white-space:nowrap;}' +
		'.cs-genline{margin:2px 0;}' +
		'img.cs-ico{width:22px;height:22px;vertical-align:middle;margin:0 4px 0 0;}' +
		'.cs-badge{width:32px;text-align:center;color:#f3e6cc;background:#1a140e;border:1px solid #e4c27a;border-radius:13px;font-weight:700;}' +
		'.cs-enemy{color:#f4efe6;}' +
		'.cs-act{width:84px;text-align:right;}' +
		'.cs-tbl td{border-top:1px solid rgba(255,255,255,.08);}' +
		'button.cs-hide{background:#3a3126;color:#f4efe6;border:1px solid #5c4c34;border-radius:4px;padding:3px 8px;cursor:pointer;}' +
		'.cs-card.is-hidden, tr.is-hidden{display:none;}' +
		'.cs-rank,.cs-sum{color:#e4c27a;font-weight:700;}' +
		'.cs-win{color:#b7e0b0;} .cs-low{color:#e2b15a;} .cs-type{color:#cbbfa8;}';
}

function CS_popout() {
	if (!CS_data) { CS_note = 'Najprej izberi avanturo.'; CS_render(); return; }
	var uri = '';
	var mapNote = '';
	if (CS_mapFile && CS_isWebp(CS_mapFile)) {
		mapNote = '<div class="map">Zemljevid je WebP in ga to okno ne prikaže. Shrani ga znova (JPEG).</div>';
	} else if (CS_mapFile) {
		uri = CS_mapUri();
		if (!uri) { mapNote = '<div class="map">Zemljevida ni mogoče prebrati.</div>'; }
	} else {
		mapNote = '<div class="map">Ni zemljevida. Shrani ga v programu, v isto mapo kot rezultate.</div>';
	}
	var mapMeta = (CS_data && CS_data.map) || {};
	var hiddenPath = '';
	var preparePath = '';
	var statusPath = '';
	try {
		if (CS_folder && CS_cfg.adventure) {
			var dir = CS_folder.resolvePath(CS_cfg.adventure);
			hiddenPath = dir.resolvePath('hidden.json').nativePath;
			preparePath = dir.resolvePath('prepare.json').nativePath;
			statusPath = dir.resolvePath('prepare-status.json').nativePath;
		}
	} catch (e) { hiddenPath = ''; }
	var payload = {
		uri: uri,
		map: mapMeta,
		hidden: CS_hiddenList(),
		hiddenPath: hiddenPath,
		preparePath: preparePath,
		statusPath: statusPath,
		hideNumbers: CS_cfg.hideNumbers !== false,
		numScale: CS_numScale || 1,
		maxH: 260,
		L: {
			show: CS_t('show'), hide: CS_t('hide'),
			numsShow: CS_t('numsShow'), numsHide: CS_t('numsHide'),
			pinned: CS_t('pinned'), pinFail: CS_t('pin') + ': ',
			restored: CS_t('restore'),
			prepareAll: CS_t('prepareAll'),
			noFolder: CS_t('pick')
		}
	};
	var mapBox = uri
		? '<div class="map" id="map"><div class="cs-maptools">' +
			'<button type="button" id="cs-zin">+</button>' +
			'<button type="button" id="cs-zout">−</button>' +
			'<button type="button" id="cs-zorig">' + CS_t('restore') + '</button>' +
			'<button type="button" id="cs-nout" title="' + CS_esc(CS_t('numsHide')) + '">−</button>' +
			'<button type="button" id="cs-nin" title="' + CS_esc(CS_t('numsShow')) + '">+</button>' +
			'<button type="button" id="cs-restore">' + CS_t('restore') + '</button>' +
			'<button type="button" id="cs-nums">' + CS_t('numsHidden') + '</button></div>' +
			'<div class="cs-mapview" id="mapview"></div></div>'
		: mapNote;
	var html = '<!doctype html><html><head><meta charset="utf-8"><title>Camp Solutions</title><style>' + CS_popCss() + '</style></head><body>' +
		'<div id="cs-top"><header class="cs-bar"><button type="button" id="cs-pin" class="is-on" title="' + CS_esc(CS_t('pinTitle')) + '">' + CS_t('pinned') + '</button><h1>' + CS_esc(CS_data.adventure || 'Camp') + '</h1><p id="cs-status">' + CS_esc(CS_note) + '</p></header>' +
		mapBox + '</div>' +
		'<div id="list">' + CS_tableHtml(CS_data, true, true) + '</div>' +
		'<script>var PAYLOAD=' + JSON.stringify(payload) + ';var ZOOM=1;' + CS_POP_JS + '</script></body></html>';
	try {
		CS_bindLift();
		if (CS_popWin && !CS_popWin.closed) {
			try { CS_popWin.close(); } catch (eClose) { }
			CS_popWin = null;
		}
		var opts = new air.NativeWindowInitOptions();
		opts.alwaysInFront = true;
		try { opts.systemChrome = air.NativeWindowSystemChrome.STANDARD; } catch (eOpt) { }
		try { opts.type = air.NativeWindowType.NORMAL; } catch (eType) { }
		var loader = air.HTMLLoader.createRootWindow(true, opts, true, new air.Rectangle(48, 36, 820, 920));
		try {
			var nw = loader.stage.nativeWindow;
			nw.alwaysInFront = true;
			nw.title = 'Camp Solutions';
			CS_popWin = nw;
			nw.addEventListener(air.Event.CLOSE, function () {
				CS_popWin = null;
				if (CS_prepTimer) { clearInterval(CS_prepTimer); CS_prepTimer = null; }
			});
		} catch (e0) { }
		loader.loadString(html);
		CS_popLoader = loader;
		CS_startPreparePoll();
		setTimeout(CS_liftPop, 80);
	} catch (e1) {
		try {
			var w = window.open('', 'csPopout', 'width=760,height=900,scrollbars=yes,resizable=yes');
			w.document.open(); w.document.write(html); w.document.close();
		} catch (e2) { CS_note = 'Ločeno okno ni na voljo: ' + e2.message; CS_render(); }
	}
}

function CS_liftPop() {
	setTimeout(function () {
		try {
			if (!CS_popWin || CS_popWin.closed) { return; }
			if (String(CS_popWin.displayState) === 'minimized') { return; }
			var active = air.NativeApplication.nativeApplication.activeWindow;
			if (active === CS_popWin) { return; }
			CS_popWin.alwaysInFront = true;
			CS_popWin.orderToFront();
		} catch (e) { }
	}, 50);
}

function CS_bindLift() {
	if (CS_liftOn) { return; }
	CS_liftOn = true;
	try { window.nativeWindow.addEventListener(air.Event.ACTIVATE, CS_liftPop); } catch (e) { }
	try { window.addEventListener('mousedown', CS_liftPop, true); } catch (e2) { }
}

var CS_POP_JS = [
	'var air = window.air;',
	'if (!air || !air.File) {',
	'  var rt = window.runtime;',
	'  if (rt && rt.flash && rt.flash.filesystem) {',
	'    air = { File: rt.flash.filesystem.File, FileStream: rt.flash.filesystem.FileStream, FileMode: rt.flash.filesystem.FileMode };',
	'  }',
	'}',
	'function status(t){ var p=document.getElementById("cs-status"); if(p) p.textContent=t; }',
	'function applyZoom(c){ if(!c) return; c.style.width=Math.round(c.width*ZOOM)+"px"; c.style.height=Math.round(c.height*ZOOM)+"px"; }',
	'function paint(){',
	'  if(!PAYLOAD.uri) return;',
	'  var box=document.getElementById("mapview"); if(!box) return;',
	'  box.innerHTML="";',
	'  var img=new Image();',
	'  img.onload=function(){',
	'    var maxH=PAYLOAD.maxH||260;',
	'    var scale=Math.min(1, maxH/img.height, 700/img.width);',
	'    var c=document.createElement("canvas");',
	'    c.width=Math.max(1,Math.round(img.width*scale));',
	'    c.height=Math.max(1,Math.round(img.height*scale));',
	'    var g=c.getContext("2d"); g.drawImage(img,0,0,c.width,c.height);',
	'    var map=PAYLOAD.map||{}; var sw=map.width||img.width; var sh=map.height||img.height;',
	'    var hidden={}; (PAYLOAD.hidden||[]).forEach(function(k){ hidden[String(k)]=1; });',
	'    var hideNums=PAYLOAD.hideNumbers!==false;',
	'    (map.camps||[]).forEach(function(camp){',
	'      if(camp.x==null) return;',
	'      if(hideNums && (hidden[camp.id]||hidden[String(camp.number)])) return;',
	'      var x=camp.x/sw*c.width, y=camp.y/sh*c.height;',
	'      var ns=PAYLOAD.numScale||1, r=Math.max(12, Math.round(Math.max(34,c.width*0.07)*ns));',
	'      g.beginPath(); g.arc(x,y,r,0,6.2832); g.fillStyle="rgba(22,16,10,.92)"; g.fill();',
	'      g.lineWidth=Math.max(3,Math.round(r*0.12)); g.strokeStyle="#e4c27a"; g.stroke();',
	'      g.fillStyle="#f7f1e6"; g.font="700 "+Math.round(r)+"px Arial"; g.textAlign="center"; g.textBaseline="middle";',
	'      g.fillText(String(camp.number), x, y+.5);',
	'    });',
	'    box.appendChild(c); applyZoom(c); pinList();',
	'  };',
	'  img.src=PAYLOAD.uri;',
	'}',
	'function pinList(){',
	'  var top=document.getElementById("cs-top");',
	'  var list=document.getElementById("list");',
	'  if(!top||!list) return;',
	'  list.style.top=top.offsetHeight+"px";',
	'}',
	'function up(el, tag){ tag=tag.toUpperCase(); while(el && (!el.tagName || el.tagName!==tag)) el=el.parentNode; return el; }',
	'function writeJson(path, obj){',
	'  var f=new air.File(); f.nativePath=path;',
	'  var fs=new air.FileStream(); fs.open(f, air.FileMode.WRITE);',
	'  fs.writeUTFBytes(JSON.stringify(obj)); fs.close();',
	'}',
	'function saveHidden(){',
	'  try {',
	'    if(PAYLOAD.hiddenPath && window.air){',
	'      var f=new air.File(); f.nativePath=PAYLOAD.hiddenPath;',
	'      var fs=new air.FileStream(); fs.open(f, air.FileMode.WRITE);',
	'      fs.writeUTFBytes(JSON.stringify({hidden:PAYLOAD.hidden||[], hideNumbers:PAYLOAD.hideNumbers!==false}));',
	'      fs.close();',
	'    }',
	'  } catch(e) {}',
	'  try { if(window.CS_onHidden) window.CS_onHidden(PAYLOAD.hidden||[], PAYLOAD.hideNumbers!==false); } catch(e2) {}',
	'}',
	'function refreshNeed(){',
	'  var box=document.getElementById("cs-need"); if(!box) return;',
	'  var sum={}, peak={};',
	'  var rows=document.getElementsByTagName("tr");',
	'  for(var i=0;i<rows.length;i++){',
	'    var row=rows[i]; if(!row.getAttribute("data-loss") && !row.getAttribute("data-units")) continue;',
	'    if(row.style.display==="none" || String(row.className).indexOf("is-hidden")>=0) continue;',
	'    var loss={}, units={};',
	'    try { loss=JSON.parse(row.getAttribute("data-loss")||"{}"); } catch(e) {}',
	'    try { units=JSON.parse(row.getAttribute("data-units")||"{}"); } catch(e2) {}',
	'    for(var k in loss){ sum[k]=(sum[k]||0)+(Number(loss[k])||0); }',
	'    for(var u in units){ var n=Number(units[u])||0; if(n>(peak[u]||0)) peak[u]=n; }',
	'  }',
	'  var keys={}; for(var a in sum) keys[a]=1; for(var b in peak) keys[b]=1;',
	'  var parts=[]; for(var u2 in keys){ var v=Math.max(sum[u2]||0, peak[u2]||0); if(v>0) parts.push(v+" × "+u2); }',
	'  box.textContent=parts.length?parts.join("   "):"—";',
	'}',
	'function syncRows(){',
	'  var set={}; (PAYLOAD.hidden||[]).forEach(function(k){ set[String(k)]=1; });',
	'  var buttons=document.getElementsByTagName("button");',
	'  for(var i=0;i<buttons.length;i++){',
	'    var b=buttons[i]; if(String(b.className).indexOf("cs-hide")<0) continue;',
	'    var key=b.getAttribute("data-key"), num=b.getAttribute("data-num");',
	'    var hidden=!!(set[key]||set[String(num)]);',
	'    var sec=up(b,"SECTION"); if(sec) sec.style.display=hidden?"none":"";',
	'    b.setAttribute("data-hidden", hidden?"1":"0");',
	'    b.textContent=hidden?(PAYLOAD.L&&PAYLOAD.L.show)||"Show":(PAYLOAD.L&&PAYLOAD.L.hide)||"Hide";',
	'  }',
	'  var rows=document.getElementsByTagName("tr");',
	'  for(var r=0;r<rows.length;r++){',
	'    var n=rows[r].getAttribute("data-num"); if(!n) continue;',
	'    var off=!!set[String(n)];',
	'    rows[r].style.display=off?"none":"";',
	'    if(off) rows[r].className=(rows[r].className||"")+" is-hidden";',
	'    else rows[r].className=String(rows[r].className||"").replace("is-hidden","");',
	'  }',
	'  var nb=document.getElementById("cs-nums");',
	'  if(nb) nb.textContent=PAYLOAD.hideNumbers===false?((PAYLOAD.L&&PAYLOAD.L.numsShow)||"Numbers: show"):((PAYLOAD.L&&PAYLOAD.L.numsHide)||"Numbers: hide");',
	'  refreshNeed(); paint(); pinList();',
	'}',
	'document.addEventListener("click", function(ev){',
	'  var b=up(ev.target, "BUTTON"); if(!b) return;',
	'  var id=b.id||"";',
	'  var canvas=document.getElementById("mapview") && document.getElementById("mapview").getElementsByTagName("canvas")[0];',
	'  if(id==="cs-zin"){ ZOOM=Math.min(4, ZOOM*1.5); applyZoom(canvas); return; }',
	'  if(id==="cs-zout"){ ZOOM=Math.max(1, ZOOM/1.5); applyZoom(canvas); return; }',
	'  if(id==="cs-zorig"){ ZOOM=1; applyZoom(canvas); return; }',
	'  if(id==="cs-nin" || id==="cs-nout"){',
	'    var ns=PAYLOAD.numScale||1;',
	'    PAYLOAD.numScale=Math.max(0.5, Math.min(2.5, Math.round((ns+(id==="cs-nin"?0.2:-0.2))*10)/10));',
	'    paint(); return;',
	'  }',
	'  if(id==="cs-pin"){',
	'    try {',
	'      var nw = window.nativeWindow;',
	'      if (!nw && window.htmlLoader) nw = window.htmlLoader.stage.nativeWindow;',
	'      nw.alwaysInFront = !nw.alwaysInFront;',
	'      if (nw.alwaysInFront) { b.className = "is-on"; status("Pripeto: okno ostane nad igro, igro lahko klikneš."); }',
	'      else { b.className = "off"; status("Odpeto: okno lahko gre za igro."); }',
	'    } catch (err) { status("Pripni ni uspel: " + err.message); }',
	'    return;',
	'  }',
	'  if(id==="cs-restore"){ PAYLOAD.hidden=[]; saveHidden(); syncRows(); status("Vsi tabori so spet prikazani."); return; }',
	'  if(id==="cs-nums"){ PAYLOAD.hideNumbers=PAYLOAD.hideNumbers===false; saveHidden(); syncRows(); return; }',
	'  if(String(b.className).indexOf("cs-prepall")>=0){',
	'    if(!PAYLOAD.preparePath){ status("Ni mape avanture, zato Pripravi ne doseže igre."); return; }',
	'    try {',
	'      var allId=new Date().getTime();',
	'      writeJson(PAYLOAD.preparePath, {id:allId, all:true, name:"", units:{}});',
	'      PAYLOAD.waitId=allId;',
	'      status("Pošiljam vse generale...");',
	'    } catch(errAll) { status("Ukaza ni bilo mogoče zapisati: "+errAll.message); }',
	'    return;',
	'  }',
	'  if(String(b.className).indexOf("cs-prep")>=0){',
	'    var units={}; try { units=JSON.parse(b.getAttribute("data-units")||"{}"); } catch(e) {}',
	'    var name=b.getAttribute("data-general")||"";',
	'    if(!PAYLOAD.preparePath){ status("Ni mape avanture, zato Pripravi ne doseže igre."); return; }',
	'    try {',
	'      var id=new Date().getTime();',
	'      writeJson(PAYLOAD.preparePath, {id:id, name:name, units:units});',
	'      PAYLOAD.waitId=id;',
	'      status("Pošiljam «"+name+"» v igro...");',
	'    } catch(err) { status("Ukaza ni bilo mogoče zapisati: "+err.message); }',
	'    return;',
	'  }',
	'  if(String(b.className).indexOf("cs-hide")<0) return;',
	'  var key=b.getAttribute("data-key"), num=b.getAttribute("data-num");',
	'  var list=(PAYLOAD.hidden||[]).slice();',
	'  var hide=b.getAttribute("data-hidden")!=="1";',
	'  list=list.filter(function(k){ return k!==key && k!==num; });',
	'  if(hide){ if(key) list.push(key); if(num && list.indexOf(num)<0) list.push(num); }',
	'  PAYLOAD.hidden=list; saveHidden(); syncRows();',
	'});',
	'try { if (window.nativeWindow) { window.nativeWindow.alwaysInFront = true; window.nativeWindow.addEventListener("nativeWindowResize", pinList); } } catch (e) {}',
	'try { window.addEventListener("resize", pinList); } catch (e2) {}',
	'setInterval(function(){',
	'  if(!PAYLOAD.waitId || !PAYLOAD.statusPath) return;',
	'  try {',
	'    var f=new air.File(); f.nativePath=PAYLOAD.statusPath; if(!f.exists) return;',
	'    var fs=new air.FileStream(); fs.open(f, air.FileMode.READ);',
	'    var txt=fs.readUTFBytes(fs.bytesAvailable); fs.close();',
	'    var j=JSON.parse(txt);',
	'    if(j && j.id===PAYLOAD.waitId && j.msg){ status(j.msg); if(j.done) PAYLOAD.waitId=0; }',
	'  } catch(e) {}',
	'}, 400);',
	'setTimeout(pinList, 50);',
	'syncRows();'
].join('\n');

function CS_prepFile(name) {
	try {
		if (!CS_folder || !CS_cfg.adventure) { return null; }
		return CS_folder.resolvePath(CS_cfg.adventure).resolvePath(name);
	} catch (e) { return null; }
}

function CS_writeStatus(id, msg, done) {
	var file = CS_prepFile('prepare-status.json');
	if (!file || !id) { return; }
	try {
		var fs = new air.FileStream();
		fs.open(file, air.FileMode.WRITE);
		fs.writeUTFBytes(JSON.stringify({ id: id, msg: msg, done: !!done }));
		fs.close();
	} catch (e) { }
}

function CS_pollPrepare() {
	var file = CS_prepFile('prepare.json');
	if (!file || !file.exists) { return; }
	var job = null;
	try { job = JSON.parse(CS_readText(file)); } catch (e) { return; }
	if (!job || !job.id || job.id === CS_prepSeen) { return; }
	CS_prepSeen = job.id;
	try {
		var msg = job.all ? CS_prepareAll() : CS_prepare(job);
		CS_writeStatus(job.id, msg, false);
	} catch (err) {
		CS_writeStatus(job.id, 'Pripravi ni uspel: ' + err.message, true);
	}
}

function CS_startPreparePoll() {
	if (CS_prepTimer) { clearInterval(CS_prepTimer); }
	CS_prepTimer = setInterval(CS_pollPrepare, 400);
}

function CS_pushPop() {
	try {
		if (!CS_popLoader || !CS_popLoader.window || !CS_popLoader.window.PAYLOAD) { return; }
		var w = CS_popLoader.window;
		w.PAYLOAD.hidden = CS_hiddenList().slice();
		w.PAYLOAD.hideNumbers = CS_cfg.hideNumbers !== false;
		if (w.syncRows) { w.syncRows(); }
	} catch (e) { }
}

function CS_onHidden(list, hideNumbers) {
	var name = (CS_data && CS_data.adventure) || CS_cfg.adventure || '';
	if (name) { CS_cfg.hidden[name] = (list || []).slice(); }
	CS_cfg.hideNumbers = hideNumbers !== false;
	CS_save();
	if ($('#' + CS_MODAL).is(':visible')) { CS_render(); }
}

var CS_UNIT_LABELS = {
	recruit: 'Recruit', bowman: 'Bowman', militia: 'Militia', cavalry: 'Cavalry',
	longbowman: 'Longbowman', soldier: 'Soldier', crossbowman: 'Crossbowman',
	'elite soldier': 'EliteSoldier', elitesoldier: 'EliteSoldier', cannoneer: 'Cannoneer',
	swordsman: 'Swordsman', 'mounted swordsman': 'MountedSwordsman', knight: 'Knight',
	marksman: 'Marksman', 'armored marksman': 'ArmoredMarksman',
	'mounted marksman': 'MountedMarksman', besieger: 'Besieger'
};

function CS_stageRoots() {
	var roots = [];
	try {
		var wins = air.NativeApplication.nativeApplication.openedWindows;
		for (var i = 0; i < wins.length; i++) {
			try { if (wins[i].stage) { roots.push(wins[i].stage); } } catch (e) { }
		}
	} catch (e2) { }
	return roots;
}

function CS_walkStage(fn) {
	var roots = CS_stageRoots();
	var seen = 0;
	for (var r = 0; r < roots.length; r++) {
		var stack = [roots[r]];
		while (stack.length && seen < 25000) {
			var o = stack.pop();
			seen++;
			try { fn(o); } catch (e) { }
			var n = 0;
			try { n = o.numChildren || 0; } catch (e2) { n = 0; }
			for (var i = n - 1; i >= 0; i--) {
				try { stack.push(o.getChildAt(i)); } catch (e3) { }
			}
		}
	}
	return seen;
}

function CS_unitLabels() {
	var map = {
		recruit: 'Recruit', bowman: 'Bowman', militia: 'Militia', cavalry: 'Cavalry',
		longbowman: 'Longbowman', soldier: 'Soldier', crossbowman: 'Crossbowman',
		'elite soldier': 'EliteSoldier', elitesoldier: 'EliteSoldier', cannoneer: 'Cannoneer',
		swordsman: 'Swordsman', 'mounted swordsman': 'MountedSwordsman', knight: 'Knight',
		marksman: 'Marksman', 'armored marksman': 'ArmoredMarksman',
		'mounted marksman': 'MountedMarksman', besieger: 'Besieger'
	};
	var ids = ['Recruit', 'Militia', 'Soldier', 'EliteSoldier', 'Cavalry', 'Bowman', 'Longbowman', 'Crossbowman', 'Cannoneer', 'Swordsman', 'MountedSwordsman', 'Knight', 'Marksman', 'ArmoredMarksman', 'MountedMarksman', 'Besieger'];
	for (var i = 0; i < ids.length; i++) {
		var id = ids[i];
		map[id.toLowerCase()] = id;
		try {
			var a = loca.GetText('RES', id);
			var b = loca.GetText('LAB', id);
			if (a) { map[String(a).toLowerCase()] = id; }
			if (b) { map[String(b).toLowerCase()] = id; }
		} catch (e) { }
	}
	return map;
}

function CS_knownUnit(name) {
	var raw = String(name || '').replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
	if (!raw || raw.length > 40) { return ''; }
	var labels = CS_unitLabels();
	if (labels[raw.toLowerCase()]) { return labels[raw.toLowerCase()]; }
	var flat = raw.replace(/\s+/g, '');
	if (labels[flat.toLowerCase()]) { return labels[flat.toLowerCase()]; }
	return '';
}

function CS_textsIn(node, maxDepth) {
	var out = [];
	var stack = [{ n: node, d: 0 }];
	var steps = 0;
	while (stack.length && steps < 80) {
		var item = stack.pop();
		steps++;
		var o = item.n;
		try {
			if (typeof o.text === 'string' && o.text && String(o.text).length < 48) { out.push(String(o.text)); }
		} catch (e) { }
		if (item.d >= maxDepth) { continue; }
		var n = 0;
		try { n = o.numChildren || 0; } catch (e2) { n = 0; }
		for (var i = 0; i < n; i++) {
			try { stack.push({ n: o.getChildAt(i), d: item.d + 1 }); } catch (e3) { }
		}
	}
	return out;
}

function CS_rowOf(tf) {
	var node = tf;
	for (var d = 0; d < 8 && node; d++) {
		var texts = CS_textsIn(node, 3);
		var ids = [];
		for (var i = 0; i < texts.length; i++) {
			var id = CS_knownUnit(texts[i]);
			if (id && ids.indexOf(id) < 0) { ids.push(id); }
		}
		if (ids.length === 1) { return { id: ids[0], row: node }; }
		try { node = node.parent; } catch (e) { break; }
	}
	return null;
}

function CS_isAmountField(o) {
	var text = null;
	try { text = o.text; } catch (e) { return false; }
	if (typeof text !== 'string') { return false; }
	if (/^\s*\d+\s*\/\s*\d+\s*$/.test(text)) { return true; }
	var kind = '';
	try { kind = String(o.type || ''); } catch (e2) { }
	if (kind === 'input' && /^\s*\d*\s*$/.test(text)) { return true; }
	try {
		if (o.maxChars > 0 && o.maxChars <= 8 && /^\s*\d*\s*$/.test(text)) { return true; }
	} catch (e3) { }
	return false;
}

function CS_shownAmount(current, value) {
	var m = String(current || '').match(/^\s*\d+\s*\/\s*(\d+)\s*$/);
	if (m) { return value + ' / ' + m[1]; }
	return String(value);
}

function CS_setField(tf, value) {
	var wrote = false;
	try { tf.text = String(value); wrote = true; } catch (e) { }
	try {
		var Ev = game.def('flash.events::Event');
		tf.dispatchEvent(new Ev(Ev.CHANGE, true));
	} catch (e3) { }
	return wrote;
}

function CS_setSlider(row, amount) {
	if (!row) { return; }
	var stack = [row];
	var steps = 0;
	while (stack.length && steps < 50) {
		var o = stack.pop();
		steps++;
		try {
			if (typeof o.value === 'number' && (typeof o.maximum === 'number' || typeof o.max === 'number' || typeof o.mMax === 'number')) {
				o.value = amount;
			}
		} catch (e) { }
		try { if (typeof o.SetValue === 'function') { o.SetValue(amount); } } catch (e2) { }
		try { if (typeof o.setValue === 'function') { o.setValue(amount); } } catch (e3) { }
		try { if (typeof o.SetAmount === 'function') { o.SetAmount(amount); } } catch (e4) { }
		var n = 0;
		try { n = o.numChildren || 0; } catch (e5) { n = 0; }
		for (var i = 0; i < n; i++) {
			try { stack.push(o.getChildAt(i)); } catch (e6) { }
		}
	}
}

function CS_fillArmy(units, seen, phase) {
	var found = 0;
	var inputs = 0;
	CS_walkStage(function (o) {
		if (!CS_isAmountField(o)) { return; }
		inputs++;
		var row = CS_rowOf(o);
		if (!row || seen[row.id]) { return; }
		var current = '';
		try { current = o.text; } catch (e) { }
		var amount = units[row.id] != null ? (parseInt(units[row.id], 10) || 0) : 0;
		if (phase !== 'value') {
			if (CS_setField(o, CS_shownAmount(current, 0))) { found++; }
			CS_setSlider(row.row, 0);
		}
		if (phase !== 'zero') {
			if (amount > 0) { CS_setField(o, CS_shownAmount(current, amount)); }
			CS_setSlider(row.row, amount);
			seen[row.id] = 1;
			found++;
		}
		CS_armyAnchor = row.row;
	});
	return { found: found, inputs: inputs };
}

function CS_armyVisible() {
	var n = 0;
	CS_walkStage(function (o) {
		try {
			if (typeof o.text === 'string' && /^\s*\d+\s*\/\s*\d+\s*$/.test(o.text)) { n++; }
		} catch (e) { }
	});
	return n >= 3;
}

function CS_press(o) {
	var ME = game.def('flash.events::MouseEvent');
	try { o.dispatchEvent(new ME(ME.MOUSE_DOWN, true)); } catch (e) { }
	try { o.dispatchEvent(new ME(ME.MOUSE_UP, true)); } catch (e2) { }
	try { o.dispatchEvent(new ME(ME.CLICK, true)); } catch (e3) { }
}

function CS_clickConfirm() {
	var root = CS_armyAnchor;
	var hops = 0;
	while (root && root.parent && hops < 16) {
		var kids = 0;
		try { kids = root.numChildren || 0; } catch (e0) { kids = 0; }
		if (kids > 12 && hops > 2) { break; }
		try { root = root.parent; } catch (e1) { break; }
		hops++;
	}
	if (!root) { return ''; }
	var Point = null;
	try { Point = air.Point || window.runtime.flash.geom.Point; } catch (eP) { Point = null; }
	function place(o) {
		if (!Point) { return null; }
		try {
			var p = o.localToGlobal(new Point(0, 0));
			var w = Number(o.width) || 0;
			var h = Number(o.height) || 0;
			if (w < 24 || h < 18) { return null; }
			return { x: p.x, y: p.y, w: w, h: h };
		} catch (e) { return null; }
	}
	var clicked = '';
	var stack = [root];
	var steps = 0;
	var bottom = [];
	var win = place(root);
	while (stack.length && steps < 900) {
		var o = stack.pop();
		steps++;
		var blob = '';
		try { blob = String(o.name || ''); } catch (e2) { blob = ''; }
		var n = 0;
		try { n = o.numChildren || 0; } catch (e3) { n = 0; }
		for (var i = 0; i < n && i < 8; i++) {
			try { blob += ' ' + String(o.getChildAt(i).name || ''); } catch (e4) { }
		}
		var ok = /accept|confirm|apply|checkmark|btnok|buttonok|okbutton|submit|commit|approve|btn_ok|m_ok|icon_ok/i.test(blob);
		var bad = /cancel|close|abort|attack|adventure|transfer|retreat|retrench|preview|decline|delete|remove|checkif/i.test(blob);
		var pos = place(o);
		var inBand = !!(win && pos && pos.w <= 88 && pos.h <= 72 && pos.y > win.y + win.h * 0.68 && pos.x > win.x + win.w * 0.28);
		if (inBand && !bad) { bottom.push({ o: o, x: pos.x, ok: ok }); }
		for (var c = n - 1; c >= 0; c--) {
			try { stack.push(o.getChildAt(c)); } catch (e6) { }
		}
	}
	if (bottom.length) {
		var named = [];
		for (var b = 0; b < bottom.length; b++) { if (bottom[b].ok) { named.push(bottom[b]); } }
		var pick = named.length ? named : bottom;
		pick.sort(function (a, b) { return a.x - b.x; });
		try { CS_press(pick[0].o); clicked = 'check'; } catch (e7) { }
	}
	return clicked;
}

function CS_clickEliteToggle() {
	var clicked = false;
	CS_walkStage(function (o) {
		if (clicked) { return; }
		var name = '';
		try { name = String(o.name || ''); } catch (e) { }
		if (!/UnitSwitch|SwitchUnit|ToElite|ToNormal|eliteSwitch|btnElite|SwitchTo|UnitType/i.test(name)) { return; }
		try {
			var ME = game.def('flash.events::MouseEvent');
			o.dispatchEvent(new ME(ME.CLICK, true));
			clicked = true;
		} catch (e2) { }
	});
	return clicked;
}

function CS_tryOpenGeneral(spec, grid, allowBuilding) {
	var gi = game.gi;
	try { gi.mCurrentCursor.mCurrentSpecialist = spec; } catch (e0) { }
	var targets = [gi, gi && gi.mCurrentCursor, gi && gi.mMouseCursor, spec];
	for (var t = 0; t < targets.length; t++) {
		var obj = targets[t];
		if (!obj) { continue; }
		var keys = [];
		try { for (var k in obj) { keys.push(k); } } catch (e1) { }
		for (var i = 0; i < keys.length; i++) {
			var key = keys[i];
			if (typeof obj[key] !== 'function') { continue; }
			if (!/^(show|open|select|display)/i.test(key) || !/specialist|general/i.test(key)) { continue; }
			try { obj[key](spec); return true; } catch (e2) {
				try { obj[key](); return true; } catch (e3) { }
			}
		}
	}
	try {
		if (allowBuilding && grid) { gi.SelectBuilding(game.zone.mStreetDataMap.GetBuildingByGridPos(grid)); return true; }
	} catch (e4) { }
	return false;
}

function CS_unitLine(units) {
	var parts = [];
	for (var k in (units || {})) {
		var n = parseInt(units[k], 10) || 0;
		if (n > 0) { parts.push(n + '× ' + CS_nice(k)); }
	}
	return parts.join(', ');
}

function CS_freePool() {
	var have = {};
	try {
		var cols = game.zone.GetArmy(game.player.GetPlayerId()).GetSquadsCollection_vector();
		for (var i = 0; i < cols.length; i++) {
			var id = String(cols[i].GetType());
			have[id] = (have[id] || 0) + (Number(cols[i].GetAmount()) || 0);
		}
	} catch (e) { }
	return have;
}

function CS_ownArmy(spec) {
	var own = {};
	try {
		var squads = spec.GetArmy().GetSquadsCollection_vector();
		for (var i = 0; i < squads.length; i++) {
			var id = String(squads[i].GetType());
			own[id] = (own[id] || 0) + (Number(squads[i].GetAmount()) || 0);
		}
	} catch (e) { }
	return own;
}

function CS_findGeneral(name) {
	var spec = null;
	var TYPE = game.def('Enums::SPECIALIST_TYPE');
	var list = game.gi.mCurrentPlayerZone.GetSpecialists_vector();
	var want = CS_shortName(name).toLowerCase();
	var me = game.player.GetPlayerId();
	for (var i = 0; i < list.length; i++) {
		var item = list[i];
		try { if (!TYPE.IsGeneral(item.GetType())) { continue; } } catch (e0) { }
		try { if (item.getPlayerID() != me) { continue; } } catch (e1) { }
		var n = '';
		try { n = String(item.getName(false) || '').replace(/<[^>]+>/g, ''); } catch (e2) { }
		var flat = n.toLowerCase();
		if (flat === want || (want && (flat.indexOf(want) >= 0 || want.indexOf(flat) >= 0))) {
			spec = item;
			if (flat === want) { break; }
		}
	}
	return spec;
}

function CS_generalPlace(spec) {
	var task = null;
	try { task = spec.GetTask(); } catch (e0) { }
	if (task != null) {
		try {
			var Travel = game.def('Specialists::cSpecialistTask_TravelToStarMenu');
			if (Travel && task instanceof Travel) { return 'star'; }
		} catch (e1) { }
		return 'task';
	}
	var grid = 0;
	try { grid = spec.GetGarrisonGridIdx(); } catch (e2) { }
	if (!(grid > 0)) { return 'star'; }
	return 'ok';
}

function CS_sendArmy(spec, units) {
	var VO = game.def('Communication.VO::dRaiseArmyVO');
	var Res = game.def('Communication.VO::dResourceVO');
	var vo = new VO();
	vo.armyHolderSpecialistVO = spec.CreateSpecialistVOFromSpecialist();
	var count = 0;
	for (var k in units) {
		var amount = parseInt(units[k], 10) || 0;
		if (amount <= 0) { continue; }
		var res = new Res();
		res.name_string = k;
		res.amount = amount;
		vo.unitSquads.addItem(res);
		count++;
	}
	if (!count) { return 'ni enot za poslati'; }
	game.gi.mClientMessages.SendMessagetoServer(1031, game.gi.mCurrentViewedZoneID, vo);
	return '';
}

function CS_prepare(req, pool, openWindow) {
	var name = String((req && req.name) || '');
	var units = (req && req.units) || {};
	var spec = null;
	try { spec = CS_findGeneral(name); } catch (e) {
		return 'Generala ni mogoče poiskati: ' + e.message;
	}
	if (!spec) { return CS_tf('notFound', { name: name }); }
	var place = 'ok';
	try { place = CS_generalPlace(spec); } catch (ePlace) { place = 'ok'; }
	if (place === 'star') { return CS_tf('star', { name: name }); }
	if (place === 'task') { return CS_tf('task', { name: name }); }
	var own = CS_ownArmy(spec);
	var have = {};
	var src = pool || CS_freePool();
	var k;
	for (k in src) { have[k] = src[k]; }
	for (k in own) { have[k] = (have[k] || 0) + own[k]; }
	var missing = [];
	for (k in units) {
		var need = parseInt(units[k], 10) || 0;
		if (need > (have[k] || 0)) { missing.push(CS_tf('needLine', { unit: CS_nice(k), need: need, have: (have[k] || 0) })); }
	}
	if (missing.length) { return CS_tf('short', { name: name, what: missing.join(', ') }); }
	var err = '';
	try { err = CS_sendArmy(spec, units); } catch (eSend) { return name + ': ukaza ni bilo mogoče poslati: ' + eSend.message; }
	if (err) { return name + ': ' + err + '.'; }
	if (pool) {
		for (k in own) { pool[k] = (pool[k] || 0) + own[k]; }
		for (k in units) {
			var sent = parseInt(units[k], 10) || 0;
			if (sent > 0) { pool[k] = (pool[k] || 0) - sent; }
		}
	}
	if (openWindow !== false) {
		setTimeout(function () {
			try {
				var grid = 0;
				try { grid = spec.GetGarrisonGridIdx(); } catch (eG) { }
				try { if (grid) { game.zone.ScrollToGrid(grid); } } catch (eS) { }
				try { game.gi.mCurrentCursor.mCurrentSpecialist = spec; } catch (eC) { }
				CS_tryOpenGeneral(spec, grid, true);
			} catch (eOpen) { }
		}, 400);
	}
	return CS_tf('sent', { name: name, units: CS_unitLine(units) }) +
		(openWindow !== false ? CS_t('opening') : '');
}

function CS_prepareAll() {
	var camps = (CS_data && CS_data.camps) || [];
	var gens = {};
	var order = [];
	camps.forEach(function (c) {
		if (CS_isHidden(c)) { return; }
		var a = CS_attacker(CS_bestSol(c));
		if (!a) { return; }
		var gname = CS_shortName(a.general_name) || CS_nice(a.general_base || a.general_id || '');
		var key = String(a.general_id || gname);
		if (!gens[key]) { gens[key] = { name: gname, units: {} }; order.push(key); }
		var units = a.units || {};
		for (var u in units) {
			var n = parseInt(units[u], 10) || 0;
			if (n > (gens[key].units[u] || 0)) { gens[key].units[u] = n; }
		}
	});
	if (!order.length) { return 'Ni generalov za pripravo.'; }
	var pool = CS_freePool();
	var lines = [];
	for (var i = 0; i < order.length; i++) {
		lines.push(CS_prepare({ name: gens[order[i]].name, units: gens[order[i]].units }, pool, false));
	}
	return lines.join(' | ');
}

function CS_prepareStatus(name, stats, units, seen) {
	var left = [];
	for (var k in units) {
		if (Number(units[k]) > 0 && !seen[k]) { left.push(k); }
	}
	var found = stats && stats.found ? stats.found : 0;
	var inputs = stats && stats.inputs ? stats.inputs : 0;
	var msg = found
		? ('Vpisanih vrst enot: ' + found + '. Najprej 0, nato vrednost.')
		: ('Okno generala «' + name + '» je odprto, vnosnih polj pa ni bilo (najdenih ' + inputs + ').');
	if (left.length) { msg += ' Manjka: ' + left.join(', ') + '.'; }
	if (!found && !CS_armyVisible()) {
		msg = 'Okna generala «' + name + '» ni bilo. Klikni generala na zemljevidu in znova Pripravi.';
	}
	CS_note = msg;
	try { $('#' + CS_MODAL + ' .cs-note').text(msg); } catch (e0) { }
	if (found) {
		setTimeout(function () {
			var hit = '';
			try { hit = CS_clickConfirm(); } catch (eClick) { hit = ''; }
			var full = msg + (hit ? ' Pritisnil sem zeleno kljukico.' : ' Zelene kljukice nisem našel, pritisni jo ročno.');
			CS_note = full;
			try { $('#' + CS_MODAL + ' .cs-note').text(full); } catch (eNote) { }
			CS_writeStatus(CS_prepSeen, full, true);
		}, 0);
	}
	CS_note = msg;
	try { $('#' + CS_MODAL + ' .cs-note').text(msg); } catch (e0) { }
	CS_writeStatus(CS_prepSeen, msg, true);
	try {
		if (CS_popLoader && CS_popLoader.window) {
			var el = CS_popLoader.window.document.getElementById('cs-status');
			if (el) { el.textContent = msg; }
		}
	} catch (e) { }
}

function CS_init() {
	var $w = $('#' + CS_MODAL);
	var $sel = $w.find('.cs-adv').empty();
	CS_note = '';
	if (CS_cfg.folder && CS_openFolder(CS_cfg.folder)) {
		var r = CS_resolveRoot(CS_folder);
		CS_folder = r.root;
		$sel.append('<option value="">— avantura —</option>');
		r.adventures.forEach(function (a) { $sel.append($('<option>').val(a).text(a)); });
		if (r.adventures.length === 0) {
			CS_note = 'V ' + CS_cfg.folder + ' ni map z results.json. Najdeno: ' + (CS_names(CS_folder) || '(prazno)');
		}
		var pick = r.pick || ((CS_cfg.adventure && r.adventures.indexOf(CS_cfg.adventure) >= 0) ? CS_cfg.adventure :
			(r.adventures.length === 1 ? r.adventures[0] : ''));
		if (pick) { $sel.val(pick); CS_load(pick); }
	} else if (CS_cfg.folder) {
		CS_note = 'Mape ni: ' + CS_cfg.folder;
	} else {
		CS_note = 'Izberi mapo rezultati, ki jo naredi program.';
	}
	CS_render();
}

function CS_render() {
	CS_mergeHiddenFile();
	var $w = $('#' + CS_MODAL);
	$w.find('.cs-res').html(CS_data ? CS_tableHtml(CS_data, CS_showHidden, true) : '<div class="cs-empty">' + CS_t('noData') + '</div>');
	var note = CS_note;
	if (CS_data && CS_data.adventure) { note = CS_data.adventure + ' · ' + note; }
	$w.find('.cs-note').text(note);
	$w.find('.cs-nums').text(CS_cfg.hideNumbers === false ? CS_t('numsShow') : CS_t('numsHide'));
	$w.find('.cs-mapbtn').toggle(!!(CS_mapFile || (CS_data && CS_data.map)));
	if (CS_mapOpen && (CS_mapFile || (CS_data && CS_data.map))) { CS_showMap($w.find('.cs-mapbox'), 220); }
	else { $w.find('.cs-mapbox').hide(); }
	CS_fit();
}

addToolsMenuItem("Camp Solutions", CS_Menu);
try {
	if (typeof customScripts !== 'undefined') {
		customScripts['user_camp_solutions.js'] = {
			name: 'Camp Solutions',
			author: 'camp-solutions',
			title: 'Generali in enote za avanturo',
			description: 'Za izbrano avanturo pokaže, katerega generala in koliko katerih enot poslati na vsak tabor.',
			url: 'https://github.com/fedorovvl/tso_client'
		};
	}
} catch (e) { }
