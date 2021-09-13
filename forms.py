import os
from typing import Optional
from flask.app import Flask
from flask_wtf import FlaskForm
from wtforms import PasswordField, BooleanField, StringField, validators, IntegerField, SelectField, ValidationError
from wtforms.fields.core import Label
from wtforms.fields.html5 import DateField, EmailField, IntegerRangeField

class NewGame(FlaskForm):
	start_amount= IntegerField('Starting Supply', [validators.InputRequired(), validators.NumberRange(min=1)], default=100)
	num_workers	= IntegerField('Number of Workers', [validators.InputRequired(), validators.NumberRange(min=1)], default=5)
	rng_min		= IntegerField('Minimum Roll', [validators.InputRequired(), validators.NumberRange(min=1)], default=1)
	rng_max		= IntegerField('Maximum Roll', [validators.InputRequired(), validators.NumberRange(min=1)], default=6)

class JoinGame(FlaskForm):
    username	= StringField('Username', [validators.InputRequired(), validators.Length(min=4, max=50)])
    game_key	= PasswordField('Game Password', [validators.InputRequired(), validators.Length(min=10, max=10)])

class SpectateGame(FlaskForm):
    game_key	= PasswordField('Game Password', [validators.InputRequired(), validators.Length(min=10, max=10)])

class EditWorker(FlaskForm):
	min_roll	= IntegerField('Minimum Roll', [validators.InputRequired(), validators.NumberRange(min=1)])
	max_roll	= IntegerField('Maximum Roll', [validators.InputRequired(), validators.NumberRange(min=1)])
	multiplier	= IntegerField('Multiplier', [validators.InputRequired(), validators.NumberRange(min=1)])
