"use-strict"
function update(jsonData) {
	console.log(jsonData)
	if (!jsonData.valid) {
		window.location.href = "/index";
	}
	var prev_roll = true;
	for (const [index, element] of jsonData.workers.entries()) {
		var elem = document.getElementById('wrk-' + index + '-wip-queue')
		elem.innerHTML = element.wip_queue;
		elem = document.getElementById('wrk-' + index + '-roll')
		elem.innerHTML = element.roll_num;
		elem = document.getElementById('wrk-' + index + '-rolled')
		if (element.rolled) {
			elem.innerHTML = "✅";
			if (prev_roll) {
				elem = document.getElementById('wrk-' + index + '-prod');
				elem.innerHTML = element.production;
			}
		}
		else {
			elem.innerHTML = "❌";
			elem = document.getElementById('wrk-' + index + '-prod');
			elem.innerHTML = '-';
			console.log(index + "false");
			prev_roll = false;
		}
		elem = document.getElementById('wrk-' + index + '-min')
		elem.innerHTML = element.roll_min;
		elem = document.getElementById('wrk-' + index + '-max')
		elem.innerHTML = element.roll_max;
		elem = document.getElementById('wrk-' + index + '-mult')
		elem.innerHTML = element.multiplier;
	}
	var elem = document.getElementById('end-amount');
		elem.innerHTML = jsonData.end_amount;
	elem = document.getElementById('supply');
	elem.innerHTML = jsonData.supply;
	elem = document.getElementById('supply-roll');
	elem.innerHTML = jsonData.supply_roll;
	elem = document.getElementById('supply-min');
	elem.innerHTML = jsonData.supply_min;
	elem = document.getElementById('supply-max');
	elem.innerHTML = jsonData.supply_max;
	elem = document.getElementById('supply-mult');
	elem.innerHTML = jsonData.supply_multiplier;
	elem = document.getElementById('supply-prod');
	elem.innerHTML = jsonData.supply_production;
	elem = document.getElementById('round-num')
	elem.innerHTML = "Round Number: " + String(jsonData.step_num+1) + "     Max WIP: " + String(jsonData.max_wip);
	if (document.getElementById('round-button')) {
		elem = document.getElementById('round-button');
		if (!jsonData.all_rolled) {
			elem.style.display = 'none';
		}
		else {
			elem.style.display = '';
		}
	}
}

function call_update() {
	let game_key = document.cookie.split('; ')
		.find(row => row.startsWith('game_key='))
		.split('=')[1];
	fetch('/api/game_status/' + game_key, {
		method: 'GET',
		//other options
		}).then(response => response.json())
		.then(
			response => update(response)
		);
}

function update_gm(jsonData) {
	for (const [index, element] of jsonData.workers.entries()) {
		elem = document.getElementById('edit-wrk-' + index + '-min_roll')
		elem.value = element.roll_min;
		elem = document.getElementById('edit-wrk-' + index + '-max_roll')
		elem.value = element.roll_max;
		elem = document.getElementById('edit-wrk-' + index + '-multiplier')
		elem.value = element.multiplier;
	}
	var elem = document.getElementById('edit-supply-min_roll')
	elem.value = jsonData.supply_min;
	elem = document.getElementById('edit-supply-max_roll')
	elem.value = jsonData.supply_max;
	elem = document.getElementById('edit-supply-multiplier')
	elem.value = jsonData.supply_multiplier;
}

function gm_update() {
	let game_key = document.cookie.split('; ')
		.find(row => row.startsWith('game_key='))
		.split('=')[1];
	fetch('/api/game_status/' + game_key, {
		method: 'GET',
		//other options
		}).then(response => response.json())
		.then(
			response => update_gm(response)
		);
}