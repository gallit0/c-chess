#!/usr/bin/env python3


from tensorflow import keras as K
import numpy as np
import chess


def fen_to_bitboard(fen):
    board = chess.Board(fen)
    piece_to_int = {'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
                    'p': -1, 'n': -2, 'b': -3, 'r': -4, 'q': -5, 'k': -6, '.': 0}

    board_array = np.zeros((8, 8), dtype=int)
    for row in range(8):
        for col in range(8):
            square = chess.square(col, 7 - row)
            piece = board.piece_at(square)
            if piece is not None:
                board_array[row, col] = piece_to_int[piece.symbol()]

    possible_moves = [move.uci() for move in board.legal_moves]
    moves_array = np.zeros((512, 64, 64), dtype=int)
    for idx, move in enumerate(possible_moves):
        from_square, to_square = chess.square(ord(move[0]) - ord('a'), 7 - (ord(move[1]) - ord('1'))), \
                                 chess.square(ord(move[2]) - ord('a'), 7 - (ord(move[3]) - ord('1')))
        moves_array[idx, from_square, to_square] = 1

    return board_array, moves_array


def new_model(lr=0.001):
    board_input_layer = K.layers.Input(shape=(8, 8))
    moves_input_layer = K.layers.Input(shape=(512, 64, 64))

    board_flattened = K.layers.Flatten()(board_input_layer)
    moves_flattened = K.layers.Flatten()(moves_input_layer)

    merged_inputs = K.layers.concatenate([board_flattened, moves_flattened])

    hidden_layer = K.layers.Dense(64, activation='relu')(merged_inputs)
    output_layer = K.layers.Dense(4, activation='linear')(hidden_layer)

    model = K.models.Model(inputs=[board_input_layer, moves_input_layer], outputs=output_layer)
    model.compile(loss='mse', optimizer=K.optimizers.Adam(lr=lr))
    return model


if __name__ == '__main__':
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    board = chess.Board(fen)
    possible_moves = [move.uci() for move in board.legal_moves]
    model = new_model()
    brd, moves= fen_to_bitboard(fen)
    print(brd)
    output = model.predict(([brd], [moves]))
    print(output)
    
