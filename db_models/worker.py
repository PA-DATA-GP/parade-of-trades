from datetime import datetime, timedelta, timezone, tzinfo
from time import time

from sqlalchemy.sql.functions import user
from db_models.db import db

import custom_utils

class Worker(db.Model):
	__tablename__ = 'worker'
	id = db.Column(db.String(64), primary_key=True) # unsure if null byte included
	game_id = db.Column(db.String(64), db.ForeignKey('game.id'), nullable=False)
	worker_index = db.Column(db.Integer)
	user_key = db.Column(db.String(64))
	username = db.Column(db.String(64), nullable=False, default='') # prevent breakage
	wip_queue = db.Column(db.Integer, nullable=False, default=0)
	rng_min = db.Column(db.Integer)
	rng_max = db.Column(db.Integer)
	rolled = db.Column(db.Boolean, nullable=False, default=False)
	roll_num = db.Column(db.Integer, nullable=False, default=1)
	multiplier = db.Column(db.Integer, nullable=False, default=1)
	taken = db.Column(db.Boolean, nullable=False, default=False)
	production = db.Column(db.Integer, nullable=False, default=1)
	
	@classmethod
	def new_worker(cls, game_id: str, worker_index: int, rng_min: int, rng_max: int):
		candidate_id = custom_utils.random_id(64)
		while cls.query.filter_by(id=candidate_id).first() != None:
			candidate_id = custom_utils.random_id(64)

		candidate_uk = custom_utils.random_id(64)
		while cls.query.filter_by(user_key=candidate_uk).first() != None:
			candidate_uk = custom_utils.random_id(64)

		worker_inst = cls(id=candidate_id, user_key=candidate_uk, game_id=game_id,
							worker_index=worker_index, rng_min=rng_min, rng_max=rng_max)
		db.session.add(worker_inst)
		db.session.commit()
		return worker_inst

	@classmethod
	def get_workers(cls, game_id):
		return Worker.query.filter_by(game_id=game_id).order_by(Worker.worker_index)
	
	@classmethod
	def get_by_userkey(cls, user_key):
		return Worker.query.filter_by(user_key=user_key).first()

	def __repr__(self):
		return '<Worker %s> of Game %s Index %d' % (self.id, self.game_id, self.worker_index)

	def get_status(self):
		ret = dict()
		ret['wrk_index'] = self.worker_index
		ret['roll_min'] = self.rng_min
		ret['roll_max'] = self.rng_max
		ret['rolled'] = self.rolled
		ret['roll_num'] = self.roll_num
		ret['wip_queue'] = self.wip_queue
		ret['taken'] = self.taken
		ret['username'] = self.username
		ret['multiplier'] = self.multiplier
		ret['production'] = self.production
		return ret
	
	def roll(self):
		if not self.rolled:
			self.roll_num = self.multiplier*custom_utils.secure_rng.choice([self.rng_min, self.rng_max])
			self.rolled = True
			db.session.commit()
			return (True, self.roll_num)
		else:
			return (False, "Already Rolled.")
	
	def reset_rolled(self):
		self.rolled = False
	
	def process(self):
		self.rolled = False
		if self.roll_num > self.wip_queue:
			buf_val = self.wip_queue
			self.wip_queue = 0
			db.session.commit()
			return buf_val
		else:
			self.wip_queue -= self.roll_num
			db.session.commit()
			return self.roll_num