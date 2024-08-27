#!/usr/bin/env python3
import gym, json
import numpy as np
from gym import spaces
import chess, gym, random
import chess.pgn
from typing import Tuple
from evaluate import Evaluator
from config import DEBUG

class ChessWrapper(gym.ObservationWrapper):
    """
    Chess environment wrapper.
    """
    def __init__(self, env, evaluator) -> None:
        super(ChessWrapper, self).__init__(env)
        self.observation_space = spaces.Box(low=0, high=1, shape=(8, 8, 12), dtype=np.float32)
        self.evaluator = evaluator
        self.update_action_space()

    def update_action_space(self, restart=False) -> None:
        """
        Update the action space based on current board legal moves.
        """
        if self.env._board == None or restart:
            self.env._board = chess.Board()
        self.move_to_index, self.index_to_move = self._create_action_space(self.env._board)
        self.action_space = spaces.Discrete(len(self.move_to_index))

    def _create_action_space(self, board: chess.Board) -> Tuple[dict, dict]:
        move_to_index = {}
        index_to_move = {}
        index = 0
        for move in board.legal_moves:
            move_to_index[move.uci()] = index
            index_to_move[index] = move.uci()
            index += 1
        return move_to_index, index_to_move

    def observation(self, obs) -> np.ndarray:
        return self.board_to_array(obs)

    def board_to_array(self, board: chess.Board) -> np.ndarray:
        """
        Turns a board into a model-readable array.

        Args:
            board (chess.Board): Input board.

        Returns:
            np.ndarray: Processed array board.
        """
        piece_map = {
            chess.PAWN: 0,
            chess.KNIGHT: 1,
            chess.BISHOP: 2,
            chess.ROOK: 3,
            chess.QUEEN: 4,
            chess.KING: 5
        }
        board_array = np.zeros((8, 8, 12), dtype=np.float32)
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                row, col = divmod(square, 8)
                piece_type = piece_map[piece.piece_type]
                color_offset = 6 if piece.color == chess.BLACK else 0
                board_array[row, col, piece_type + color_offset] = 1
        return board_array

    def step(self, action: np.int64, playing=False) -> Tuple[np.ndarray, float, bool, dict]:
        """
        Executes an step on current game state.

        Args:
            action (np.int64): Action to be executed.
        
        Returns:
            np.ndarray: Observation
            float: Reward for current action.
            bool: True if game is finished.
            dict: Info dictionary.
        """
        legal_moves = [str(move) for move in self.env._board.legal_moves]
        chose_ilegal = False
        try:
            move_uci = self.index_to_move[int(action)]
        except KeyError:
            move_uci = random.choice(legal_moves)
            move = random.choice(legal_moves)
            chose_ilegal = True
            info = {'random_move': True}
        if DEBUG:
            print(f'(debug)\nlegal moves: {legal_moves}', )
            print(f'(debug) {self.env._board}')
            print(f'(debug) action: {action} - index_to_move: {self.index_to_move} - move_uci : {move_uci}')
        board_before = self.env._board.copy()
        move = chess.Move.from_uci(move_uci)
        obs, reward, done, info = self.env.step(move)
        board_after = self.env._board.copy()
        if not chose_ilegal and self.evaluator:
            reward += self.evaluator.evaluate_position(done, board_before, board_after, self.env, move)
        if DEBUG:
            print('(debug)', move_uci, reward, done, info)
        if info is None:
            info = {}
        if done and not playing:
            self.update_action_space(restart=True)
        else:
            self.update_action_space()

        if chose_ilegal: reward = -10.0

        return self.observation(obs), reward, done, info

    def render(self, mode='unicode') -> None:
        """
        Render the environment.

        Args:
            mode (str): Mode used to render.
        """
        print(self.env.render(mode=mode))
        print('=' * 15)

    def get_pgn(self) -> str:
        """
        Get an exportable Chess game string.

        Returns:
            str: PGN string containing a whole exportable game of Chess.
        """
        board = self.env._board
        game = chess.pgn.Game.from_board(board)
        exporter = chess.pgn.StringExporter()
        pgn = game.accept(exporter)
        return pgn


class SyzygyWrapper(ChessWrapper):
    def __init__(self, env, evaluator, path='data/val_data/data.json') -> None:
        super().__init__(env, evaluator)
        self.current_position_index = 0
        with open(path, 'r') as file:
            self.positions_expected = json.load(file)
        self.move_to_index, self.index_to_move = self._create_action_space(self.env._board)
    
    def step(self, action: np.int64) -> Tuple[np.ndarray, float, bool, dict]:
        """
        """
        if DEBUG:
            print(f'(debug) Syzygy training -  action: {action} - index_to_move: {self.index_to_move} - move_uci : {self.index_to_move[action]}')
        move_uci = self.index_to_move[action]
        move = chess.Move.from_uci(move_uci)
        is_move_legal = self.env._board.is_legal(move)
        if not is_move_legal:
            legal_moves = [move for move in self.env._board.legal_moves]
            move = random.choice(legal_moves)
            info = {'random_move': True}
        obs, reward, done, info = self.env.step(move)
        if move_uci == self.positions_expected[self.current_position_index][1]:
            reward = 10000.0
        self.current_position_index = (self.current_position_index + 1) % len(self.positions_expected)
        self.env._board = chess.Board(self.positions_expected[self.current_position_index][0])
        if DEBUG:
            print('(debug) Syzygy training -', move_uci, reward, done, info)
        if info is None:
            info = {}

        return self.observation(obs), reward, done, info

