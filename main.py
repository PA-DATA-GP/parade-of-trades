import os
import json
import forms
from datetime import datetime, timedelta
from flask import Flask, session, request, render_template, send_from_directory, redirect, url_for, abort, flash, send_file, jsonify
from flask.helpers import make_response
from custom_utils import random_id, secure_rng
from sqlalchemy import and_
from db_models.db import db
from db_models.worker import Worker
from db_models.game import Game

app = Flask(__name__)
# random key if flask_key env var is unset
app.secret_key = os.getenv('FLASK_KEY', random_id(64))
endpoint_secret = os.getenv('ENDPOINT_SECRET')
# use env var, otherwise local sqlite db. ORMs are flexible like that
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sqlite.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(dict(
  PREFERRED_URL_SCHEME = 'https'
))
db.init_app(app)

@app.before_first_request
def before_first_request():
    db.create_all()
    exp_games = Game.query.filter(and_(Game.tombstone == False, Game.creation_time <= (datetime.now()-timedelta(hours=6)))).all()
    for exp in exp_games:
        exp.tombstone = True
    db.session.commit()

@app.route('/')
@app.route('/index')
def index_page():
    return send_from_directory(app.static_folder, 'trades_index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory(app.static_folder, os.path.join('css', path))

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory(app.static_folder, os.path.join('js', path))

@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    form = forms.NewGame()
    if request.method == 'POST' and form.validate_on_submit():
        new_game = Game.new_game(form.start_amount.data, form.num_workers.data, form.rng_min.data, form.rng_max.data)
        
        resp = make_response(redirect(url_for('game_master', game_key=new_game.game_key)))
        resp.set_cookie('gm_key', new_game.gm_key)
        resp.set_cookie('game_key', new_game.game_key)
        return resp
    return render_template('new_game.html', form=form)

@app.route('/gm/<game_key>')
def game_master(game_key):
    game = Game.get_game(request.cookies['game_key'])
    if not game:
            resp = make_response(redirect(url_for('new_game')))
            # resp.delete_cookie('game_key')
            # resp.delete_cookie('gm_key')
            # resp.delete_cookie('player_key')
            return resp
    supply_form = forms.EditWorker(prefix='edit-supply')
    form = [forms.EditWorker(prefix=f'edit-wrk-{ind}') for ind in range(game.get_num_workers())]
    return render_template('gm.html', game=game, supply_form=supply_form, forms=form)

@app.route('/join_game', methods=['GET', 'POST'])
def join_game():
    form = forms.JoinGame()
    if request.method == 'POST' and form.validate_on_submit():
        game = Game.get_game(form.game_key.data)
        if not game:
            resp = make_response(redirect(url_for('index_page')))
            return resp
        untaken = Worker.query.filter_by(game_id=game.id, taken=False).order_by(Worker.worker_index).first()
        if untaken != None:
            untaken.taken = True
            untaken.username = form.username.data
            db.session.commit()
            resp = make_response(redirect(url_for('player')))
            resp.set_cookie('player_key', untaken.user_key)
            resp.set_cookie('game_key', game.game_key)
        return resp
    return render_template('player_join.html', form=form)

@app.route('/player')
def player():
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        return make_response(redirect(url_for('index_page')))
    else:
        worker = Worker.get_by_userkey(request.cookies['player_key'])
        return render_template('player.html', game=game, worker=worker, wrk_num=worker.worker_index)

@app.route('/spectate_join', methods=['GET', 'POST'])
def spectate_join():
    form = forms.SpectateGame()
    if request.method == 'POST' and form.validate_on_submit():
        game = Game.get_game(form.game_key.data)
        if not game:
            form.game_key.errors.append('Game key does not match any in our records.')
            return render_template('spectate_join.html', form=form)
        resp = make_response(redirect(url_for('spectate', game_key=form.game_key.data)))
        resp.set_cookie('game_key', form.game_key.data)
        return resp
    return render_template('spectate_join.html', form=form)

@app.route('/spectate/<game_key>')
def spectate(game_key):
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        return redirect(url_for('spectate_join'))
    return render_template('spectate.html', game=game)

@app.route('/api/gm/edit_workers', methods=['POST'])
def edit_workers():
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.cookies['gm_key'] != game.gm_key:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    req_dict = request.form.to_dict()
    if request.method == 'POST' and req_dict['btn'] == 'Update Players':
        game.supply_multiplier = int(req_dict['edit-supply-multiplier'])
        game.supply_rng_min = int(req_dict['edit-supply-min_roll'])
        game.supply_rng_max = int(req_dict['edit-supply-max_roll'])
        for ind, wrk in enumerate(Worker.get_workers(game.id)):
            wrk.multiplier = int(req_dict[f'edit-wrk-{ind}-multiplier'])
            wrk.rng_min = int(req_dict[f'edit-wrk-{ind}-min_roll'])
            wrk.rng_max = int(req_dict[f'edit-wrk-{ind}-max_roll'])
        db.session.commit()
        return redirect(url_for('game_master', game_key=request.cookies['game_key']))
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/gm/roll_all', methods=['GET', 'POST'])
def roll_all(): # get probably not req.
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.cookies['gm_key'] != game.gm_key:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        for wrk in Worker.get_workers(game.id):
            wrk.roll()
        game.update_production_status()
        return game_status(request.cookies['game_key'])
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/gm/roll_all_force', methods=['GET', 'POST'])
def roll_all_force(): # get probably not req.
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.cookies['gm_key'] != game.gm_key:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        game.supply_roll = game.supply_multiplier*secure_rng.choice([game.supply_rng_min, game.supply_rng_max])
        game.supply_production = min([game.supply, game.supply_roll])
        for wrk in Worker.get_workers(game.id):
            wrk.roll_num = wrk.multiplier*secure_rng.choice([wrk.rng_min, wrk.rng_max])
            wrk.rolled = True
        db.session.commit()
        game.update_production_status()
        return game_status(request.cookies['game_key'])
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))
    
@app.route('/api/gm/next_step', methods=['GET', 'POST'])
def next_step(): # get probably not req.
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.cookies['gm_key'] != game.gm_key:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        game.step()
        game.update_production_status()
        return game_status(request.cookies['game_key'])
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/gm/get_data', methods=['GET', 'POST'])
def get_data(): # get probably not req.
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.cookies['gm_key'] != game.gm_key:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        return game.log
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/player/roll_self', methods=['GET', 'POST'])
def roll_self():
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if Worker.get_by_userkey(request.cookies['player_key']) == None:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        Worker.get_by_userkey(request.cookies['player_key']).roll()
        game.update_production_status()
        return game_status(request.cookies['game_key'])
    return redirect(make_response(redirect(url_for('index_page'))))

@app.route('/api/player/next_step', methods=['GET', 'POST'])
def player_step():
    game = Game.get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if Worker.get_by_userkey(request.cookies['player_key']) == None:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        if all([wrk.rolled for wrk in Worker.get_workers(game.id)]):
            game.step()
        return game_status(request.cookies['game_key'])
    return redirect(make_response(redirect(url_for('index_page'))))


@app.route('/api/game_status/<game_key>')
def game_status(game_key):
    game_inst = Game.get_game(game_key)
    if game_inst != None:
        return game_inst.get_status()
    else:
        return {'valid': False}