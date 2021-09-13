from game import Game
import os
import json
from flask import Flask, session, request, render_template, send_from_directory, redirect, url_for, abort, flash, send_file, jsonify
from flask.helpers import make_response
from custom_utils import random_id, secure_rng
import forms

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_KEY', random_id(64))

games = dict()

def get_game(game_key):
    if game_key in games:
        return games[game_key]
    else:
        return False

@app.route('/')
@app.route('/index')
def index_page():
    return send_from_directory(app.static_folder, 'index.html')

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
        new_game = Game(form.start_amount.data, form.num_workers.data, form.rng_min.data, form.rng_max.data)
        games[new_game.game_key] = new_game
        
        resp = make_response(redirect(url_for('game_master', game_key=new_game.game_key)))
        resp.set_cookie('gm_key', new_game.gm_key)
        resp.set_cookie('game_key', new_game.game_key)
        return resp
    return render_template('new_game.html', form=form)

@app.route('/gm/<game_key>')
def game_master(game_key):
    game = get_game(request.cookies['game_key'])
    if not game:
            resp = make_response(redirect(url_for('new_game')))
            # resp.delete_cookie('game_key')
            # resp.delete_cookie('gm_key')
            # resp.delete_cookie('player_key')
            return resp
    supply_form = forms.EditWorker(prefix='edit-supply')
    form = [forms.EditWorker(prefix=f'edit-wrk-{ind}') for ind in range(game.num_workers)]
    return render_template('gm.html', game=game, supply_form=supply_form, forms=form)

@app.route('/join_game', methods=['GET', 'POST'])
def join_game():
    form = forms.JoinGame()
    if request.method == 'POST' and form.validate_on_submit():
        game = get_game(form.game_key.data)
        if not game:
            resp = make_response(redirect(url_for('index_page')))
            return resp
        if not all(game.taken_worker):
            untaken_ind = game.taken_worker.index(False)
            game.taken_worker[untaken_ind] = True
            game.workers[untaken_ind].user = form.username.data
            resp = make_response(redirect(url_for('player')))
            resp.set_cookie('player_key', game.workers[untaken_ind].key)
            resp.set_cookie('game_key', game.game_key)
        return resp
    return render_template('player_join.html', form=form)

@app.route('/player')
def player():
    game = get_game(request.cookies['game_key'])
    if not game:
        return make_response(redirect(url_for('index_page')))
    else:
        worker = game.workers_dict[request.cookies['player_key']]
        wrk_num = game.workers.index(worker)
        return render_template('player.html', game=game, worker=worker, wrk_num=wrk_num)

@app.route('/spectate_join', methods=['GET', 'POST'])
def spectate_join():
    form = forms.SpectateGame()
    if request.method == 'POST' and form.validate_on_submit():
        game = get_game(form.game_key.data)
        if not game:
            form.game_key.errors.append('Game key does not match any in our records.')
            return render_template('spectate_join.html', form=form)
        resp = make_response(redirect(url_for('spectate', game_key=form.game_key.data)))
        resp.set_cookie('game_key', form.game_key.data)
        return resp
    return render_template('spectate_join.html', form=form)

@app.route('/spectate/<game_key>')
def spectate(game_key):
    game = get_game(request.cookies['game_key'])
    if not game:
        return redirect(url_for('spectate_join'))
    return render_template('spectate.html', game=game)

@app.route('/api/gm/edit_workers', methods=['POST'])
def edit_workers():
    game = get_game(request.cookies['game_key'])
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
        for ind, wrk in enumerate(game.workers):
            wrk.multiplier = int(req_dict[f'edit-wrk-{ind}-multiplier'])
            wrk.rng_min = int(req_dict[f'edit-wrk-{ind}-min_roll'])
            wrk.rng_max = int(req_dict[f'edit-wrk-{ind}-max_roll'])
        return redirect(url_for('game_master', game_key=request.cookies['game_key']))
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/gm/roll_all', methods=['GET', 'POST'])
def roll_all(): # get probably not req.
    game = get_game(request.cookies['game_key'])
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
        for wrk in game.workers:
            wrk.roll()
        return game_status(request.cookies['game_key'])
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/gm/roll_all_force', methods=['GET', 'POST'])
def roll_all_force(): # get probably not req.
    game = get_game(request.cookies['game_key'])
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
        game.supply_roll = game.supply_multiplier*secure_rng.randrange(game.supply_rng_min, game.supply_rng_max+1)
        for wrk in game.workers:
            wrk.roll_num = wrk.multiplier*secure_rng.randrange(wrk.rng_min, wrk.rng_max+1)
            wrk.rolled = True
        return game_status(request.cookies['game_key'])
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))
    
@app.route('/api/gm/next_step', methods=['GET', 'POST'])
def next_step(): # get probably not req.
    game = get_game(request.cookies['game_key'])
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
        return game_status(request.cookies['game_key'])
    return redirect(url_for('game_master', game_key=request.cookies['game_key']))

@app.route('/api/gm/get_data', methods=['GET', 'POST'])
def get_data(): # get probably not req.
    game = get_game(request.cookies['game_key'])
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
    game = get_game(request.cookies['game_key'])
    if not game:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.cookies['player_key'] not in game.workers_dict:
        resp = make_response(redirect(url_for('index_page')))
        # resp.delete_cookie('game_key')
        # resp.delete_cookie('gm_key')
        # resp.delete_cookie('player_key')
        return resp
    
    if request.method == 'POST':
        game.workers_dict[request.cookies['player_key']].roll()
        return game_status(request.cookies['game_key'])
    return redirect(make_response(redirect(url_for('index_page'))))

@app.route('/api/game_status/<game_key>')
def game_status(game_key):
    if game_key in games:
        return games[game_key].get_status()
    else:
        return {'valid': False}