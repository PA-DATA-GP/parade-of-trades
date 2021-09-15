from urllib.parse import urlparse, urljoin
from flask import request
from custom_utils import random_id, secure_rng

class Worker:
	def __init__(self, rng_min, rng_max):
		self.key = random_id(64)
		self.user = ''
		self.buffer = 0
		self.rng_min = rng_min
		self.rng_max = rng_max
		self.rolled = False
		self.roll_num = 1
		self.multiplier = 1
		self.taken = False
		self.production = 1
	
	def get_status(self):
		ret = dict()
		ret['roll_min'] = self.rng_min
		ret['roll_max'] = self.rng_max
		ret['rolled'] = self.rolled
		ret['roll_num'] = self.roll_num
		ret['buffer'] = self.buffer
		ret['taken'] = self.taken
		ret['user'] = self.user
		ret['multiplier'] = self.multiplier
		ret['production'] = self.production
		return ret
	
	def roll(self):
		if not self.rolled:
			self.roll_num = self.multiplier*secure_rng.choice([self.rng_min, self.rng_max])
			self.rolled = True
			return (True, self.roll_num)
		else:
			return (False, "Already Rolled.")
	
	def reset_rolled(self):
		self.rolled = False
	
	def process(self):
		self.rolled = False
		if self.roll_num > self.buffer:
			buf_val = self.buffer
			self.buffer = 0
			return buf_val
		else:
			self.buffer -= self.roll_num
			return self.roll_num 