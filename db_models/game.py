from datetime import datetime, timedelta, timezone, tzinfo
from time import time
from sqlalchemy import func
from db_models.db import db

import custom_utils
from db_models.worker import Worker

class Game(db.Model):
	__tablename__ = 'game'
	id = db.Column(db.String(64), primary_key=True) # unsure if null byte included
	creation_time = db.Column(db.DateTime, nullable=False, default=datetime.now())
	game_key = db.Column(db.String(4))
	gm_key = db.Column(db.String(64))
	supply = db.Column(db.Integer)
	supply_rng_min = db.Column(db.Integer)
	supply_rng_max = db.Column(db.Integer)
	supply_multiplier = db.Column(db.Integer, nullable=False, default=1)
	end_amount = db.Column(db.Integer, nullable=False, default=0)
	step_num = db.Column(db.Integer, nullable=False, default=0)
	supply_roll = db.Column(db.Integer, nullable=False, default=0)
	max_wip = db.Column(db.Integer, nullable=False, default=0)
	supply_production = db.Column(db.Integer)
	workers = db.relationship('Worker', backref=db.backref('game', lazy=True))
	tombstone = db.Column(db.Boolean, nullable=False, default=False)

	@classmethod
	def new_game(cls, start_amount: int, num_workers: int, rng_min: int, rng_max: int):
		candidate_id = custom_utils.random_id(64)
		while cls.query.filter_by(id=candidate_id).first() != None:
			candidate_id = custom_utils.random_id(64)

		candidate_gk = custom_utils.random_id(4)
		while cls.query.filter_by(game_key=candidate_gk, tombstone=False).first() != None:
			candidate_gk = custom_utils.random_id(4)

		candidate_gmk = custom_utils.random_id(64)
		while cls.query.filter_by(gm_key=candidate_gmk).first() != None:
			candidate_gmk = custom_utils.random_id(64)

		supply_roll = custom_utils.secure_rng.choice([rng_min, rng_max])
		supply_production = min([start_amount, supply_roll])
		ng_instance = cls(id=candidate_id, game_key=candidate_gk, gm_key=candidate_gmk, supply=start_amount, supply_rng_min=rng_min,
							supply_rng_max=rng_max, supply_roll=supply_roll, supply_production=supply_production)
		game_id = ng_instance.id
		db.session.add(ng_instance)
		db.session.commit()
		for ind in range(num_workers):
			Worker.new_worker(game_id, ind, rng_min, rng_max)
		return ng_instance

	@classmethod
	def get_game(cls, game_key):
		return Game.query.filter_by(game_key=game_key, tombstone=False).first()

	def reset_worker(self, worker_ind):
		#return one worker and delete, then recreate new.
		Worker.query.filter_by(game_id=self.id, worker_index=worker_ind).first().delete()
		new_worker = Worker.new_worker(self.id, worker_ind, self.supply_rng_min, self.supply_rng_max)
		return new_worker.id

	def get_num_workers(self) -> int:
		return db.session.query(func.count(Worker.id)).filter_by(game_id=self.id).scalar()
	
	def update_production_status(self):
		workers = Worker.get_workers(self.id)
		if workers[0].rolled:
			workers[0].production = min([workers[0].roll_num, workers[0].wip_queue + self.supply_production])
			print(workers[0].roll_num, workers[0].wip_queue, self.supply, self.supply_production)
			for ind, wkr in enumerate(workers[1:]):
				ind = ind + 1 # clearest way I can put this, since slice re-indexes
				if wkr.rolled:
					wkr.production = min([wkr.roll_num, wkr.wip_queue + workers[ind-1].production])
					print(ind, wkr.roll_num, wkr.wip_queue + workers[ind-1].production, wkr.production)
				else:
					break
		db.session.commit()

	def get_status(self):
		ret = dict()
		ret['valid'] = True
		ret['num_workers'] = self.get_num_workers()
		ret['supply'] = self.supply
		ret['supply_min'] = self.supply_rng_min
		ret['supply_max'] = self.supply_rng_max
		ret['supply_roll'] = self.supply_roll
		ret['supply_multiplier'] = self.supply_multiplier
		ret['end_amount'] = self.end_amount
		ret['step_num'] = self.step_num
		ret['supply_production'] = self.supply_production
		workers = Worker.get_workers(self.id)
		ret['workers'] = [wrk.get_status() for wrk in workers]
		ret['all_rolled'] = all([wrk.rolled for wrk in workers])
		ret['max_wip'] = self.max_wip
		return ret

	def step(self):
		workers = Worker.get_workers(self.id)
		if all([wrk.rolled for wrk in workers]):
			# self.log[self.step_num] = {
			# 	'board': {
			# 		'supply': self.supply,
			# 		'queues': [wrk.wip_queue for wrk in workers],
			# 		'end_amount': self.end_amount
			# 	},
			# 	'rolls': {
			# 		'supply': self.supply_roll,
			# 		'worker_rolls': [wrk.roll_num for wrk in workers]
			# 	}
			# }
			if self.supply_roll > self.supply:
				self.supply_roll = self.supply
				self.supply = 0
			else:
				self.supply -= self.supply_roll
			workers[0].wip_queue += self.supply_roll

			processed = workers[0].process()
			for wrk in workers[1:]:
				wrk.wip_queue += processed
				processed = wrk.process()
			self.end_amount += processed
			
			if max([wrk.wip_queue for wrk in workers]) > self.max_wip:
				self.max_wip = max([wrk.wip_queue for wrk in workers])

			self.step_num += 1
			self.supply_roll = self.supply_multiplier*custom_utils.secure_rng.choice([self.supply_rng_min, self.supply_rng_max])
			self.supply_production = min([self.supply, self.supply_roll])
			db.session.commit()
			return (True, '')
		else:
			return (False, "Not all Rolled")