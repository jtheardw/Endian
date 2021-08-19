#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
import sys
import time

import chess
import chess.polyglot

from board import BoardPrinter
from engine import Engine, kill_all_engines
import suite_settings


def get_new_elo(elo1, elo2, result):
    # for results 1 means first player won, 0 means first player lost
    # 0.5 means draw

    K = 32                      # arbitrary.

    r1 = 10**(elo1 / 400.)
    r2 = 10**(elo2 / 400.)

    e1 = r1 / (r1 + r2)
    e2 = r2 / (r1 + r2)

    s1 = result
    s2 = 1 - result

    new_elo1 = elo1 + K * (s1 - e1)
    new_elo2 = elo2 + K * (s2 - e2)

    return new_elo1, new_elo2


def run_game(e1, e2, clock_time, inc, starting_moves=[]):
    # should return winner and num moves
    # 1 means white wins, 0.5 means draw, 0 means black wins
    moves = starting_moves[:]
    board = chess.Board()
    for move in moves:
        board.push(move)

    board_printer = BoardPrinter(active=False, initial_board=board)
    e1.set_printer(board_printer)
    e2.set_printer(board_printer)

    engines = (e1, e2)

    side_to_move = "white" if len(moves) % 2 == 0 else "black"
    engine_to_move = engines[0] if side_to_move == "white" else engines[1]
    # white clock, black clock
    clocks = [clock_time, clock_time]
    while True:
        board_printer.update(board, previous_move=str(moves[-1]) if len(moves) else None)
        if board.is_stalemate():
            return 0.5, len(moves) // 2, "stalemate"
        if board.is_insufficient_material():
            return 0.5, len(moves) // 2, "insufficient_material"
        if board.can_claim_draw():
            return 0.5, len(moves) // 2, "claimable draw"
        if board.is_checkmate():
            # the person who isn't side to move has won
            return (0 if side_to_move == "white" else 1), len(moves) // 2, "mate"

        # otherwise there are moves to be made
        # construct a string telling the engine to move about the current
        # boardstate
        engine_to_move.give_history(moves)
        move, move_duration = engine_to_move.go_w_clock(clocks, inc)
        clock_idx = 0 if side_to_move == "white" else 1

        if clocks[clock_idx] < move_duration:
            # timeout
            return (0 if side_to_move == "white" else 1), len(moves) // 2, "timeout"

        # update clocks
        clocks[clock_idx] += inc - move_duration

        # update board
        try:
            uci_move = chess.Move.from_uci(move)
            board.push(uci_move)
            moves.append(uci_move)
        except Exception:
            # something illegal?
            return (0 if side_to_move == "white" else 1), len(moves) // 2, "illegal move"

        if side_to_move == "white":
            side_to_move = "black"
            engine_to_move = engines[1]
        else:
            side_to_move = "white"
            engine_to_move = engines[0]


def parse_puzzle(epd):
    # TODO: more robust
    # current assumption is:
    # fen but only the first four

    # this is going to be a lot of trial and error
    # based on just seeing epds that come in
    puzzle_info = {}

    tokens = epd.strip().split()
    partial_fen, rest = ' '.join(tokens[:4]), ' '.join(tokens[4:])

    fen = f"{partial_fen} 0 1"  # half-clock, etc. shouldn't matter
    puzzle_info["fen"] = fen

    board = chess.Board(fen)

    if rest[0] == '-':
        rest = rest[2:]
    other_info = map(lambda x: x.strip(), rest.split(';'))

    # TEMP do some sort of recursive descent thing if needed?  For now we're going to make assumptions.
    for info in other_info:
        if not info:
            continue
        tokens = info.split()
        key, value = tokens[0], tokens[1:]
        # print("OTHER", key, value)
        if key == 'am':
            puzzle_info['avoid_move'] = set([str(board.parse_san(v)) for v in re.split('[ ,]+', ' '.join(value))])
        elif key == 'bm':
            puzzle_info['best_move'] = set([str(board.parse_san(v)) for v in re.split(r'[ ,]+', ' '.join(value))])
        elif key == 'id':
            puzzle_info['id'] = ' '.join(value)
        else:
            puzzle_info[key] = ' '.join(value)

    return puzzle_info


def do_one_puzzle(engine, puzzle_epd, movetime):
    puzzle_info = parse_puzzle(puzzle_epd)
    print(f"{engine.name} doing puzzle {puzzle_info.get('id', 'unknown')}")
    print(f"fen: {puzzle_info['fen']}")
    print(f"best moves: {puzzle_info.get('best_move', 'N/a')}")
    print(f"avoid moves: {puzzle_info.get('avoid_move', 'N/a')}")

    engine.give_fen(puzzle_info['fen'])
    move, _ = engine.go_w_movetime(movetime)

    success = True
    if 'best_move' in puzzle_info:
        success = success and move in puzzle_info['best_move']
    if 'avoid_move' in puzzle_info:
        success = success and move not in puzzle_info['avoid_move']

    print(f"{engine.name} chose move {move} with depth {engine.info.get('depth', 'N/a')}")
    if success:
        print("Passed!")
    else:
        print("Failed...")

    return puzzle_info.get('id', 'unknown'), success


def do_puzzle_suite(engine_fname, puzzle_file, movetime, settings={}):
    engine = Engine(engine_fname, settings)
    with open(puzzle_file) as f:
        puzzles = [l.strip() for l in f.read().split('\n') if l.strip()]
        results = []
        for puzzle_epd in puzzles:
            results.append(do_one_puzzle(engine, puzzle_epd, movetime))

    score = sum(map(lambda x: x[1], results))
    return score, len(results)


def run_puzzle_gauntlet(settings):
    # this might just merge with do_puzzle_suite if there's not anything
    # more sophisticated this ends up doing.
    hero = settings.engine
    puzzle_file = settings.puzzle_suite
    movetime = settings.puzzle_movetime
    engine_settings = settings.engine_settings

    print("Starting puzzle gauntlet")
    print(f"Puzzle file: {os.path.basename(puzzle_file)}")
    print(f"Time per Move: {movetime} ms")
    score, total = do_puzzle_suite(hero, puzzle_file, movetime, engine_settings)
    print(f"total score: {score} / {total}")

    return score, total


def engine_battle(e1_fname, e2_fname, book, clock, inc, max_book_ply=10, settings={}):
    # settings should be only read so the default is fine here
    record = [0, 0, 0]          # from e1's perspective, win draw loss
    game_winners = 0

    # just in case an engine does not support FEN, the starting positions
    # will be communicated in moves
    board = chess.Board()
    starting_moves = []

    # determine the starting position that will be played
    if book is not None:
        for i in range(max_book_ply):
            try:
                move = book.choice(board).move
                board.push(move)
                starting_moves.append(move)
            except IndexError:
                break

    e1 = Engine(e1_fname, settings)
    e2 = Engine(e2_fname, settings)

    print(f"Beginning Match: {e1.name} vs. {e2.name}")
    print(f"Starting position is: {board.fen()}")
    print(f"Starting Clock: {clock}, inc: {inc}")
    print()

    # engine 1 as white
    winner, move_count, reason = run_game(e1, e2, clock, inc, starting_moves)
    # if e1 wins here, `winner` is going to be 1, loss is 0
    record_idx = int(2 - (winner * 2))
    record[record_idx] += 1

    print("Game 1 complete")
    if winner == 0.5:
        print(f"Draw for reason: {reason}")
    else:
        print(f"Win by {e1.name if winner else e2.name} via: {reason}")
    print()

    e1.restart()
    e2.restart()

    # engine 1 as black
    winner, move_count, reason = run_game(e2, e1, clock, inc, starting_moves)
    # if e1 wins here, `winner` is going to be 0, loss is 1
    record_idx = int(winner * 2)
    record[record_idx] += 1

    print("Game 2 complete")
    if winner == 0.5:
        print(f"Draw for reason: {reason}")
    else:
        print(f"Win by {e2.name if winner else e1.name} via: {reason}")
    print()

    print(f"Match concluded.  Record is {'-'.join(map(str, record))}")
    print()

    return record


def run_engine_gauntlet(settings):
    hero = settings.engine
    challengers = settings.vs_engines
    overall_record = [0, 0, 0]
    book = settings.opening_book
    clock_time = settings.clock_time
    inc = settings.clock_inc
    max_book_ply = settings.opening_book_ply
    engine_settings = settings.engine_settings

    for challenger in challengers:
        record = engine_battle(
            hero,
            challenger,
            book,
            clock_time,
            inc,
            max_book_ply=max_book_ply,
            settings=engine_settings)

        for i in range(len(record)):
            overall_record[i] += record[i]

    print("Guantlet Concluded.  Overall record: {'-'.join(map(str, overall_record))}")
    return overall_record


def compare_engine_elo(settings):
    hero = settings.engine
    rival = settings.rival_engine
    book = settings.opening_book
    clock_time = settings.elo_clock_time
    inc = settings.elo_inc
    max_book_ply = settings.opening_book_ply
    engine_settings = settings.engine_settings
    num_rounds = settings.elo_rounds

    elo1, elo2 = 1000, 1000

    overall_record = [0, 0, 0]
    for r in range(num_rounds):
        record = engine_battle(
            hero,
            rival,
            book,
            clock_time,
            inc,
            max_book_ply=max_book_ply,
            settings=engine_settings)

        for i in range(len(record)):
            overall_record[i] += record[i]

            # update ELO.  remember the 0th index
            # of record refers to a win by our hero.
            result = 1 - (i / 2)
            for i in range(record[i]):
                elo1, elo2 = get_new_elo(elo1, elo2, result)

        print(f"Rounds passed: {r + 1}")
        print(f"Relative Elo: {int(elo1)} - {int(elo2)}")
        print()

    return elo1, elo2


def main():

    settings = suite_settings.get_settings()

    valid, err = settings.verify()
    if not valid:
        print(f"Settings malformed: {err}")
        sys.exit(1)

    record = None
    puzzle_score, puzzle_total = None, None

    if settings.run_games:
        record = run_engine_gauntlet(settings)
    if settings.run_puzzles:
        puzzle_score, puzzle_total = run_puzzle_gauntlet(settings)
    if settings.compare_elo:
        elo1, elo2 = compare_engine_elo(settings)

    print("Tests complete.  Overall results:")
    if settings.run_games:
        print(f"Engine Guantlet Record: {'-'.join(map(str, record))}")
    if settings.run_puzzles:
        print(f"Puzzle Gauntlet Score: {puzzle_score} / {puzzle_total}")
    if settings.compare_elo:
        print(f"Engine Comparison Elo results: {elo1} - {elo2}")


if __name__ == "__main__":
    try:
        main()
    finally:
        kill_all_engines()
