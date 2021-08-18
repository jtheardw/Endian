import argparse
import json
import os

import chess.polyglot

DEFAULT_SETTINGS = {
    'engine': None,
    'config': 'configs/config.json',
    'no_config': False,
    'engine_settings': {},

    'run_games': False,

    'engine_dir': 'engines/',
    'all_engines': False,
    'engine_names': [],

    'opening_book': None,
    'opening_book_max_ply': 10,
    'opening_fen': None,

    'clock_time': 30000,
    'clock_inc': 1000,

    'run_puzzles': False,
    'puzzle_suite': None,
    'puzzle_movetime': 10000
}


def coalesce(*args):
    for arg in args:
        if arg is not None:
            return arg
    return None

class Settings:
    def _load_config(self, config_file):
        if os.path.isfile(config_file):
            try:
                with open(config_file) as f:
                    print(f"Reading settings from file {os.path.basename(config_file)}...")
                    return json.loads(f.read())
            except Exception:
                print(f"Exception reading config file {config_file}")
                raise
        return {}

    def _empty_init(self):
        self.engine = None
        self.engine_settings = None

        self.run_games = None
        self.engines = None
        self.opening_book = None
        self.opening_book_ply = None
        self.opening_fen = None
        self.clock_time = None
        self.clock_inc = None

        self.run_puzzles = None
        self.puzzle_suite = None
        self.puzzle_movetime = None

    def __init__(self, arg_dict):
        # for each config param:
        #  - if it was specified as a command line param, use that value
        #  - otherwise, if it was specified in the config JSON, use that value
        #  - otherwise use the default

        self._empty_init()
        no_config = coalesce(arg_dict.get('no_config'), DEFAULT_SETTINGS.get('no_config'))
        config = {}
        if not no_config:
            config = self._load_config(coalesce(arg_dict.get('config'), DEFAULT_SETTINGS.get('config')))

        # jank but fun closure
        def _layer_settings(key, formatter=lambda x: x):
            formatted_arg = None
            if arg_dict.get(key) is not None:
                formatted_arg = formatter(arg_dict[key])
            return coalesce(formatted_arg, config.get(key), DEFAULT_SETTINGS.get(key))

        self.engine = _layer_settings('engine')
        self.engine_settings = _layer_settings('engine_settings', formatter=json.loads)

        self.run_games = _layer_settings('run_games')

        self.vs_engines = []
        if self.run_games:
            engine_dir = _layer_settings('engine_dir')
            all_engines = _layer_settings('all_engines')
            if all_engines:
                # filter out directories
                engine_subpaths = list(filter(lambda x: os.path.isfile(x), os.listdir(engine_dir)))
            else:
                engine_names = _layer_settings('engine_names', formatter=lambda x: x.split(','))
                engine_subpaths = [x.strip() for x in engine_names]
            self.vs_engines = [os.path.join(engine_dir, subpath) for subpath in engine_subpaths]

        opening_book_fname = _layer_settings('opening_book')
        self.opening_book_ply = _layer_settings('opening_book_max_ply')
        if opening_book_fname is not None and self.opening_book_ply > 0:
            try:
                self.opening_book = chess.polyglot.open_reader(opening_book_fname)
            except Exception:
                print(f"Exception when trying to open opening book {opening_book_fname}")
                raise
        else:
            self.opening_book_ply = 0

        # TODO currently, you can't override this with None as it is right now...
        self.opening_fen = _layer_settings('opening_fen')

        self.clock_time = _layer_settings('clock_time')
        self.clock_inc = _layer_settings('clock_inc')

        self.run_puzzles = _layer_settings('run_puzzles')
        if self.run_puzzles:
            self.puzzle_suite = _layer_settings('puzzle_suite')
            self.puzzle_movetime = _layer_settings('puzzle_movetime')

    def verify(self):
        # return false if something crucial is missing
        if self.engine is None:
            # no engine
            return False, "Missing engine"
        if not self.run_games and not self.run_puzzles:
            # we're not testing anything
            return False, "No tests"
        if self.run_games:
            if not self.vs_engines:
                return False, "No opponent engines"
        if self.run_puzzles:
            if not self.puzzle_suite:
                return False, "No puzzles specified"

        return True, ""


def get_settings():
    parser = get_settings_arg_parser()
    args = parser.parse_args()

    arg_settings = {
        'engine': args.engine,
        'config': args.config,
        'no_config': args.no_config,
        'engine_settings': args.engine_settings,
        'run_games': args.run_games,
        'engine_dir': args.engine_dir,
        'all_engines': args.all_engines,
        'engine_names': args.opponent_engines,
        'opening_book': args.opening_book,
        'opening_book_max_ply': args.opening_book_max_ply,
        'opening_fen': args.opening_fen,
        'clock_time': args.clock_time,
        'clock_inc': args.clock_inc,
        'run_puzzles': args.run_puzzles,
        'puzzle_suite': args.puzzle_suite,
        'puzzle_movetime': args.puzzle_movetime
    }

    return Settings(arg_settings)


def get_settings_arg_parser():
    parser = argparse.ArgumentParser(description='Specify test parameters')


    # main
    parser.add_argument("--engine", default=None, help="Engine to test")
    parser.add_argument("--config", default=None, help="Config file to apply")
    parser.add_argument("--no-config", action="store_true", help="Don't use a config file")
    parser.add_argument("--engine-settings", default=None, help="JSON string specifying all options to set for engines")


    # games
    parser.add_argument("--run-games", default=None, action="store_true", help="Give engine a guantlet of games")

    ## engines to use
    parser.add_argument("--engine-dir", type=str, default=None, help="Directory with engines to play against")
    parser.add_argument("--all-engines", default=None, action="store_true", help="Use all engines in directory")
    parser.add_argument("--opponent-engines", type=str, default=None, help="comma separated list specific engine names to play against")

    ## opening position
    parser.add_argument("--opening-book", type=str, default=None, help="polyglot opening book file for games")
    parser.add_argument("--opening-book-max-ply", type=int, default=None, help="polyglot opening book for games")
    parser.add_argument("--opening-fen", type=str, default=None, help="opening position to use for games.  Overrides any opening book")

    ## time controls
    parser.add_argument("--clock-time", type=int, default=None, help="clock time to start with for each engine in milliseconds")
    parser.add_argument("--clock-inc", type=int, default=None, help="increment for each move in milliseconds")


    # puzzles
    parser.add_argument("--run-puzzles", default=None, action="store_true", help="Give engine a guantlet of puzzles specified in EPD.")

    ## puzzles to use
    parser.add_argument("--puzzle-suite", type=str, default=None, help="EPD file containing a series of puzzles to test the engine with")

    ## time controls
    parser.add_argument("--puzzle-movetime", type=int, default=None, help="Amount of milliseconds to give the engine on each puzzle position")

    return parser
