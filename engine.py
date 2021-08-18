import os
import subprocess

SUBPROCS = {}

class Engine:
    def __init__(self, fname, settings={}):
        self.path = fname
        self.e = subprocess.Popen([self.path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.pid = self.e.pid
        self.settings = settings
        self.info = {}
        self.name = None
        self.full_name = None
        self.printer = None

        # we use this to clean up any lingering subprocs
        # just to be safe and not leak engines
        SUBPROCS[self.pid] = self.e

        self.uci()
        if self.name is None:
            # for some reason this engine doesn't state its name
            # we'll just substitute the filename
            self.name = os.path.basename(fname)
            self.full_name = self.name
        self.load_settings()

    def restart(self):
        # completely fresh restart, aka kill the process
        self.e.terminate()
        del SUBPROCS[self.pid]

        self.e = subprocess.Popen([self.path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.pid = self.e.pid
        SUBPROCS[self.pid] = self.e

        self.uci()
        self.load_settings()

    def load_settings(self):
        for param, value in self.settings.items():
            self.send_uci(f"setoption {param} {value}")

    def send_uci(self, uci):
        self.e.stdin.write(bytes(f"{uci}\n", "utf-8"))
        self.e.stdin.flush()

    def give_history(self, moves):
        pos_str = "position startpos"
        if moves:
            pos_str += f" moves {' '.join(map(str, moves))}"
        self.send_uci(pos_str)

    def give_fen(self, fen):
        self.send_uci(f"position fen {fen}")

    def _is_move(self, s):
        s = s.lower()
        if len(s) not in (4, 5):
            return False
        if s[0] not in "abcdefghij" or s[2] not in "abcdefghij":
            return False
        if s[1] not in "12345678" or s[3] not in "12345678":
            return False
        if len(s) == 5 and s[4] not in "bnrq":
            return False
        return True

    def _load_pv(self, info, i):
        pv_moves = []
        while i < len(info) and self._is_move(info[i]):
            pv_moves.append(info[i])
            i += 1
        return pv_moves, i

    def _load_score(self, info, i):
        score = {}
        score["type"] = info[i]
        score["value"] = info[i+1]

        return score, i + 2

    def _load_generic(self, info, i):
        return info[i], i + 1

    def load_info(self, info_tokens):
        self.info = {}
        idx = 0
        while idx < len(info_tokens):
            token = info_tokens[idx]
            if token == "pv":
                self.info["pv"], idx = self._load_pv(info_tokens, idx + 1)
            elif token == "score":
                self.info["score"], idx = self._load_score(info_tokens, idx + 1)
            elif token == "currmove":
                self.info["currmove"], idx = self._load_generic(info_tokens, idx + 1)
            elif token == "depth":
                self.info["depth"], idx = self._load_generic(info_tokens, idx + 1)
            else:
                # TODO other token types
                idx += 1
        if self.printer is not None and self.info.get("pv") is not None and self.info["pv"]:
            self.printer.info_update(self.info["pv"][0])

    def _readline(self):
        return self.e.stdout.readline().decode("utf-8")[:-1].strip().split()

    def _recv_move(self):
        while True:
            resp = self._readline()
            if not resp: continue
            if resp[0] == "info":
                self.load_info(resp[1:])
            elif resp[0] == "bestmove":
                return resp[1]
            else:
                continue

    def go_w_clock(self, clocks, inc):
        wtime, btime = clocks
        cmd = f"go wtime {wtime} btime {btime} winc {inc} binc {inc}"
        self.send_uci(cmd)
        return self._recv_move()

    def go_w_movetime(self, movetime):
        cmd = f"go movetime {movetime}"
        self.send_uci(cmd)
        return self._recv_move()

    def go(self):
        cmd = f"go"
        self.send_uci(cmd)
        return self._recv_move()

    def uci(self):
        cmd = "uci"
        self.send_uci(cmd)
        while True:
            resp = self._readline()
            if not resp:
                continue
            if resp[:2] == ["id", "name"]:
                self.name = resp[2]
                self.full_name = '_'.join(resp[2:])
            if resp[0] == "uciok":
                return

    def set_printer(self, printer):
        self.printer = printer

    def __del__(self):
        if hasattr(self, 'e'):
            self.e.terminate()
            del SUBPROCS[self.pid]


def kill_all_engines():
    for proc in SUBPROCS.values():
        proc.kill()
