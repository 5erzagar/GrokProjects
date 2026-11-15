/********************************************
 * Export General Names v0.1
 *
 * Reads the generals of the current player from the game client and
 * saves them as GeneralList_Names.json (names and ids only, no skills).
 *
 * Run: call TSO_exportGeneralNames() in the userscript console,
 * or paste this file as a userscript and press the button that appears.
 * The file is downloaded by the browser; then put it in TSO_GeneralList.
 ********************************************/

(function () {
	'use strict';

	var OUT_NAME = 'GeneralList_Names.json';

	function clean(s) {
		return String(s == null ? '' : s).replace(/<[^>]+>/g, '').trim();
	}

	// The game object for a specialist can expose its id under different names.
	// The first call that returns a value wins; the chosen name is stored in the file.
	var ID_GETTERS = ['getID', 'GetID', 'getId', 'GetId', 'getSpecialistID', 'GetSpecialistID', 'getUniqueID', 'GetUniqueID'];
	var ID_PROPS = ['mID', 'id', 'specialistID', 'mSpecialistID'];

	function readId(spec) {
		for (var i = 0; i < ID_GETTERS.length; i++) {
			var fn = spec[ID_GETTERS[i]];
			if (typeof fn === 'function') {
				try {
					var v = fn.call(spec);
					if (v != null && String(v) !== '') { return { value: String(v), via: ID_GETTERS[i] + '()' }; }
				} catch (e) { }
			}
		}
		for (var j = 0; j < ID_PROPS.length; j++) {
			try {
				var p = spec[ID_PROPS[j]];
				if (p != null && String(p) !== '' && typeof p !== 'function') { return { value: String(p), via: ID_PROPS[j] }; }
			} catch (e2) { }
		}
		return { value: '', via: '' };
	}

	// Base type of the general (e.g. GeneralVargus). Taken from the type the game reports.
	function readBase(spec) {
		try {
			var t = spec.GetType();
			if (t != null && String(t) !== '') { return String(t); }
		} catch (e) { }
		try {
			var d = spec.getDefinition();
			if (d) {
				var b = d.name || d.base || d.type_name || d.icon_string || '';
				if (b) { return String(b); }
			}
		} catch (e2) { }
		return '';
	}

	function readName(spec) {
		try { return clean(spec.getName(false)); } catch (e) { return ''; }
	}

	function collectGenerals() {
		var TYPE = game.def('Enums::SPECIALIST_TYPE');
		var list = game.gi.mCurrentPlayerZone.GetSpecialists_vector();
		var me = game.player.GetPlayerId();
		var out = [];
		var idSource = '';
		for (var i = 0; i < list.length; i++) {
			var spec = list[i];
			try { if (!TYPE.IsGeneral(spec.GetType())) { continue; } } catch (e0) { continue; }
			try { if (spec.getPlayerID() != me) { continue; } } catch (e1) { }
			var id = readId(spec);
			if (id.via && !idSource) { idSource = id.via; }
			out.push({
				id: id.value,
				base: readBase(spec),
				name: readName(spec)
			});
		}
		return { generals: out, idSource: idSource };
	}

	function download(text, fileName) {
		var blob = new Blob([text], { type: 'application/json' });
		var url = URL.createObjectURL(blob);
		var a = document.createElement('a');
		a.href = url;
		a.download = fileName;
		document.body.appendChild(a);
		a.click();
		setTimeout(function () {
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		}, 1000);
	}

	function exportGeneralNames() {
		var result = collectGenerals();
		var data = {
			version: 1,
			exported: new Date().toISOString(),
			type: 'General',
			specialists: result.generals
		};
		var text = JSON.stringify(data, null, 2);
		download(text, OUT_NAME);
		var missingId = result.generals.filter(function (g) { return !g.id; }).length;
		var msg = 'Generali: ' + result.generals.length +
			(result.idSource ? ' (id iz: ' + result.idSource + ')' : ' (id ni najden)') +
			(missingId ? ', brez id: ' + missingId : '');
		try { console.log('[GeneralNames] ' + msg, data); } catch (e) { }
		return data;
	}

	// Global entry point for the console.
	window.TSO_exportGeneralNames = exportGeneralNames;
})();
