from __future__ import print_function
import json
import requests
import unittest
import uuid
from flask import Flask, Response, redirect

app = Flask(__name__)


def _infinity():
    counter = 0
    while True:
        counter += 1
        yield counter


next_id = _infinity()


class Game(object):
    def __init__(self):
        self._id = uuid.uuid4().hex
        # self._id = str(next(next_id))
        print("Creating game:", self._id)
        self._board = [[None] * 3, [None] * 3, [None] * 3]
        self._players = [None, None]
        self._moves = []

    def add_player(self, pid):
        self._players[self._players.index(None)] = pid

    def add_move(self, pid, row, col):
        row, col = map(int, (row, col))
        player = not bool(self._players.index(pid))
        if self._moves and player is self._moves[-1][0]:
            return
        if self._board[row][col] is None:
            self._board[row][col] = player
            self._moves.append((player, row, col))

    def _str_space(self, row, col):
        if self._board[row][col] is None:
            return " "
        return "X" if self._board[row][col] else "O"

    def _winner(self):
        if len(self._moves) < 5:
            return

        def same(first, *rest):
            for r in rest:
                if r is not first:
                    return None
            return first

        # Test rows
        for row in self._board:
            if same(*row):
                return row[0]

        # Test columns
        for col in (0, 1, 2):
            if same(*[r[col] for r in self._board]):
                return r[col]

        # Test diagaonals
        f = self._board[1][1]
        if f is self._board[0][0] and f is self._board[2][2]:
            return f
        if f is self._board[0][2] and f is self._board[2][0]:
            return f

    def __str__(self):
        s = ""
        for r in (0, 1, 2):
            for c in (0, 1, 2):
                s += self._str_space(r, c)
            s += '\n'
        s += '-' * 3
        return s

    def json(self, indent=0):
        j = {
            'id': self._id,
            'players': dict(zip(("O", "X"), self._players)),
            'moves': [("X" if m[0] else "O", m[1], m[2]) for m in self._moves],
            'rows': {0: {'cols': {}},
                     1: {'cols': {}},
                     2: {'cols': {}}, }
        }
        for r in (0, 1, 2):
            for c in (0, 1, 2):
                _pos = self._board[r][c]
                j['rows'][r]['cols'][c] = (None if _pos is None else "X"
                                           if _pos else "O")

        w = self._winner()
        if w is not None:
            j['winner'] = self._players[int(not w)]

        return json.dumps(j, indent=indent)


all_games = {}


@app.route("/games/", methods=['GET'])
def games():
    resp = json.dumps(
        {'games': [g for g in all_games.keys()],
         'count': len(all_games), },
        indent=4)
    return Response(resp, mimetype='application/json')


@app.route("/games/new/", methods=['POST'])
def game_new():
    g = Game()
    while g._id in all_games:
        g = Game()
    all_games[g._id] = g

    resp = g.json(indent=4)

    return Response(resp,
                    status="201 Created",
                    headers={'Location': '/games/{}'.format(g._id)},
                    mimetype="application/json")


@app.route("/games/<game_id>/",
           # Work around browsers sending POST after redirect
           methods=['GET', 'POST'])
def game_by_id(game_id):
    resp = all_games[game_id].json(indent=4)
    return Response(resp, mimetype='application/json')


@app.route("/games/<game_id>/<int:row>/<int:col>/<player_id>/",
           methods=['POST'])
def game_move(game_id, row, col, player_id):
    g = all_games[game_id]
    if None in g._players:
        g.add_player(player_id)
    if player_id in g._players:
        g.add_move(player_id, row, col)
    return redirect('/games/{}/'.format(game_id), code=303)


class TicTacToeServerTest(unittest.TestCase):
    base = 'http://localhost:5000'

    def setUp(self):
        self.s = requests.Session()

        self.game_id = self.s.post(self.base + '/games/new/').json()['id']
        self.game_base = self.base + '/games/{}/'.format(self.game_id)
        self.assertTrue(self.s.get(self.game_base).ok)

    def move(self, p, r, c):
        self.s.post(self.game_base + '{}/{}/{}/'.format(r, c, p))

    def test_horizontal_win(self):
        self.move('A', 0, 0)
        self.move('B', 1, 0)
        self.move('A', 0, 1)
        self.move('B', 2, 0)
        self.move('A', 0, 2)

        self.assertEqual(self.s.get(self.game_base).json()['winner'], 'A')

    def test_vertical_win(self):
        self.move('A', 0, 0)
        self.move('B', 0, 1)
        self.move('A', 1, 0)
        self.move('B', 0, 2)
        self.move('A', 2, 0)

        self.assertEqual(self.s.get(self.game_base).json()['winner'], 'A')

    def test_diag_1_win(self):
        self.move('A', 0, 0)
        self.move('B', 0, 1)
        self.move('A', 1, 1)
        self.move('B', 0, 2)
        self.move('A', 2, 2)

        self.assertEqual(self.s.get(self.game_base).json()['winner'], 'A')

    def test_diag_2_win(self):
        self.move('A', 0, 2)
        self.move('B', 0, 1)
        self.move('A', 1, 1)
        self.move('B', 0, 0)
        self.move('A', 2, 0)

        self.assertEqual(self.s.get(self.game_base).json()['winner'], 'A')


if __name__ == '__main__':
    import socket
    try:
        app.run()
    except socket.error:
        unittest.main()
