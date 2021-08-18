# COLOR ########################################################################################

import chess
import math

class BoardPrinter:
    def __init__(self, active=False, initial_board=chess.Board()):
        self.board = initial_board
        self.previous_move = None
        self.current_move = None
        self.best_move = None
        self.avoid_move = None
        self.active = active

        clear()
        self.update(self.board)

    def _fen_to_display(self, fen):
        # returns [board_list, rights, enpass]
        board, side_to_move, cr, ep, _, _ = fen.split()
        board_lists = []
        board_list = []
        for c in board:
            if c == '/':
                board_lists.append(board_list)
                board_list = []
            if c.lower() in 'pnbrqk':
                board_list.append(c)
            if c in '12345678':
                board_list += [None] * int(c)
        board_lists.append(board_list)
        board_for_display = sum(reversed(board_lists), [])
        if ep == '-':
            ep = None
        else:
            ep = (int(ep[1]) - 1) * 8 + 'abcdefgh'.index(ep[0])
        return board_for_display, cr, ep

    def _uci_move_to_display(self, uci_move):
        if uci_move is None:
            return None
        start_file, start_rank, end_file, end_rank = uci_move[:4]
        start_rank = int(start_rank) - 1
        start_file = 'abcdefgh'.index(start_file)
        end_rank = int(end_rank) - 1
        end_file = 'abcdefgh'.index(end_file)
        return (start_rank * 8 + start_file), (end_rank * 8 + end_file)

    def update(self, board, previous_move=None, current_move=None, best_move=None, avoid_move=None):
        if not self.active:
            return
        if board.fen() == self.board.fen() and \
           previous_move == self.previous_move and \
           current_move == self.current_move and \
           best_move == self.best_move and \
           avoid_move == self.avoid_move:
            return

        self.board = board
        self.previous_move = previous_move
        self.current_move = current_move
        self.best_move = best_move
        self.avoid_move = avoid_move

        formatted_moves = map(self._uci_move_to_display, [previous_move, current_move, best_move, avoid_move])
        reset_cursor()
        display_board(*self._fen_to_display(board.fen()), *formatted_moves)

    def info_update(self, current_move=None):
        self.update(self.board, self.previous_move, current_move, self.best_move, self.avoid_move)

def lch_to_luv(triple):
    l, c, h = triple
    rad = h * math.pi / 180.0
    u = math.cos(rad) * c
    v = math.sin(rad) * c
    return (l, u, v)

KAPPA = 903.2962962
REF_U = 0.19783000664283
REF_V = 0.46831999493879

def luv_to_xyz(triple):
    l, u, v = triple
    if l == 0:
        return (0.0, 0.0, 0.0)
    var_y = ((l + 16.0) / 116.0)**3.0 if l > 8 else l / KAPPA
    var_u = u / (13.0 * l) + REF_U
    var_v = v / (13.0 * l) + REF_V
    y = var_y
    x = -(9.0 * y * var_u) / ((var_u - 4.0) * var_v - var_u * var_v)
    z = (9.0 * y - (15.0 * var_v * y) - (var_v * x)) / (3.0 * var_v)
    return (x, y, z)

M = [
    ( 3.240969941904521, -1.537383177570093, -0.498610760293   ),
    (-0.96924363628087 ,  1.87596750150772 ,  0.041555057407175),
    ( 0.055630079696993, -0.20397695888897 ,  1.056971514242878),
]

def dot_product(a, b):
    return sum(i*j for i,j in zip(a, b))

def from_linear(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055

def xyz_to_rgb(triple):
    xyz = (dot_product(i, triple) for i in M)
    return tuple(from_linear(i) for i in xyz)

def lch_to_rgb(triple):
    return xyz_to_rgb(luv_to_xyz(lch_to_luv(triple)))


# ANSI ESCAPE CODES ############################################################################


all_reset = "\x1B[0m"
fg_reset  = "\x1B[39m"
bg_reset  = "\x1B[49m"


def fg_color(l, c, h):
    r, g, b = [round(x*255) for x in lch_to_rgb((l, c, h))]
    return f"\x1B[38;2;{r};{g};{b}m"


def bg_color(l, c, h):
    r, g, b = [round(x*255) for x in lch_to_rgb((l, c, h))]
    return f"\x1B[48;2;{r};{g};{b}m"


# display_board() ##############################################################################
#
#   Draws a board along the left edge starting at the current line.
#
#   board             [piece, ..., ...]         where piece is None or a one-character string
#   rights            "KQkq"                    as in FEN
#   enpass            sq                        where sq in 0..63
#   previous_move     (from_sq, to_sq)          where from_sq and to_sq in 0..63
#   current_move      (from_sq, to_sq)            "       "       "       "
#   best_move         (from_sq, to_sq)            "       "       "       "
#   avoid_move        (from_sq, to_sq)            "       "       "       "


def write(*args, **kwargs):
    print(*args, **kwargs, end='')


def reset_cursor():
    write("\x1B[1;1H")  # move cursor to the upper left


def clear():
    write("\x1B[1;1H")  # move cursor to the upper left
    write("\x1B[2J")    # clear the entire screen


def display_board(board             ,
                  rights=""         ,
                  enpass=None       ,
                  previous_move=None,
                  current_move=None ,
                  best_move=None    ,
                  avoid_move=None   ):

    write("\r" + all_reset)
    for rank in reversed(range(8)):
        for file in range(8):
            square = rank*8 + file
            parity = (rank + file) % 2 == 0

            if parity:
                bg_light  = 60
                bg_chroma = 45
                bg_hue    = 43
            else:
                bg_light  = 78
                bg_chroma = 33
                bg_hue    = 61

            has_right = (square ==  0 and 'Q' in rights) \
                     or (square ==  7 and 'K' in rights) \
                     or (square == 56 and 'q' in rights) \
                     or (square == 63 and 'k' in rights)

            if has_right or square == enpass:
                bg_light = 69
                bg_chroma = 0
                bg_hue = 0

            if previous_move and square in previous_move:
                bg_light = 60 if parity else 78
                bg_chroma = 50 if parity else 55
                bg_hue = 75

            if current_move and square in current_move:
                bg_light = 51 if parity else 60
                bg_chroma = 100
                bg_hue = 270

            if best_move and square in best_move:
                bg_light = 60 if parity else 69
                bg_chroma = 75
                bg_hue = 135

            if avoid_move and square in avoid_move:
                bg_light = 51 if parity else 60
                bg_chroma = 100
                bg_hue = 15

            write(bg_color(bg_light, bg_chroma, bg_hue))

            piece = board[square]
            if piece is None:
                write("   ")
            elif piece.isupper():
                write(fg_color(100, 0, 0) + f" {piece} ")
            else:
                write(fg_color(0, 0, 0) + f" {piece.upper()} ")

        write(bg_reset + "\n")


# EXAMPLE ######################################################################################


board = ['R',  'N',  'B',  'Q',  'K',  'B',  'N',  'R',
         'P',  'P',  'P',  'P',  'P',  'P',  'P',  'P',
        None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None,
         'p',  'p',  'p',  'p',  'p',  'p',  'p',  'p',
         'r',  'n',  'b',  'q',  'k',  'b',  'n',  'r']

if __name__ == "__main__":
    clear()
    display_board(
        board, rights="KQkq", enpass=None,
        previous_move=(19, 27), current_move=(12, 20), best_move=(49, 41), avoid_move=(54, 46)
    )
