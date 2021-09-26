from hmac import new
from urllib.parse import urlparse, urljoin
from worker import Worker
from flask import request
from custom_utils import random_id, secure_rng

class Game:
	def __init__(self, start_amount, num_workers, rng_min, rng_max):
		self.game_key = random_id(4)
		self.gm_key = random_id(64)
		self.supply = start_amount
		self.supply_rng_min = rng_min
		self.supply_rng_max = rng_max
		self.supply_multiplier = 1
		self.end_amount = 0
		self.num_workers = num_workers
		self.workers = [Worker(rng_min, rng_max) for _ in range(num_workers)]
		self.workers_dict = {wrk.key: wrk for wrk in self.workers}
		self.taken_worker = [False for _ in self.workers]
		self.step_num = 0
		self.supply_roll = secure_rng.choice([self.supply_rng_min, self.supply_rng_max])
		self.log = dict()
		self.max_wip = 0
		self.supply_production = min([self.supply, self.supply_roll])

	def __bool__(self):
		return True

	def reset_worker(self, worker_ind):
		new_worker = Worker()
		self.workers[worker_ind] = new_worker
		self.taken_worker[worker_ind] = False
		self.worker_keys[worker_ind] = new_worker

	def get_status(self):
		ret = dict()
		ret['valid'] = True
		ret['num_workers'] = self.num_workers
		ret['supply'] = self.supply
		ret['supply_min'] = self.supply_rng_min
		ret['supply_max'] = self.supply_rng_max
		ret['supply_roll'] = self.supply_roll
		ret['supply_multiplier'] = self.supply_multiplier
		ret['end_amount'] = self.end_amount
		ret['step_num'] = self.step_num
		self.supply_production = min([self.supply, self.supply_roll])
		ret['supply_production'] = self.supply_production
		if self.workers[0].rolled:
			self.workers[0].production = min([self.workers[0].roll_num, self.workers[0].wip_queue + self.supply_production])
			for ind, wkr in enumerate(self.workers[1:]):
				ind = ind + 1 # clearest way I can put this, since slice re-indexes
				if wkr.rolled:
					wkr.production = min([wkr.roll_num, wkr.wip_queue + self.workers[ind-1].production])
					print(ind, wkr.roll_num, wkr.wip_queue + self.workers[ind-1].production, wkr.production)
				else:
					break
		ret['workers'] = [wrk.get_status() for wrk in self.workers]
		ret['all_rolled'] = all([wrk.rolled for wrk in self.workers])
		ret['max_wip'] = self.max_wip
		return ret

	def step(self):
		if all([wrk.rolled for wrk in self.workers]):
			self.log[self.step_num] = {
				'board': {
					'supply': self.supply,
					'queues': [wrk.wip_queue for wrk in self.workers],
					'end_amount': self.end_amount
				},
				'rolls': {
					'supply': self.supply_roll,
					'worker_rolls': [wrk.roll_num for wrk in self.workers]
				}
			}
			if self.supply_roll > self.supply:
				self.supply_roll = self.supply
				self.supply = 0
			else:
				self.supply -= self.supply_roll
			self.workers[0].wip_queue += self.supply_roll

			processed = self.workers[0].process()
			for wrk in self.workers[1:]:
				wrk.wip_queue += processed
				processed = wrk.process()
			self.end_amount += processed
			
			if max([wrk.wip_queue for wrk in self.workers]) > self.max_wip:
				self.max_wip = max([wrk.wip_queue for wrk in self.workers])

			self.step_num += 1
			self.supply_roll = self.supply_multiplier*secure_rng.choice([self.supply_rng_min, self.supply_rng_max])
			return (True, '')
		else:
			return (False, "Not all Rolled")