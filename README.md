# Endian: A Simple Utility for Running Simple Assessments for UCI-compatible Chess Engines

## Overview

Endian is a Python utility for doing simple tests on a UCI compatible engine like having it play games against other engines or solve puzzles.  It is not extensive or performant enough to use for things like masisvely parallel self-play, ELO estimation, or anything like that.

This is very much a WIP project and will likely have bugs.  There are many improvements, both in terms of bugfixes and new features, on the way.

## Code Dependencies

- Python 3.8+
- The `chess` package for Python

## Things You'll Need

- At least one UCI-compatible chess engine to test.
- [Optional] A Polyglot format opening book
- [Optional] Puzzles specified in an EPD file

## Usage Examples

For the moment this will be pretty sparse.  As the specific flag names and such become more permenant I'll add more detail here.

```
python endian.py --engine engines/mantissa --run-games --engine-dir engines --engine-names "expositor, admonitor, zahak" --clock-time 30000 --clock-inc 1000
```
Run the engine Mantissa against Expositor, Admonitor, and Zahak in matches with 30 seconds clock + 1 second increment

```
python endian.py --engine engines/mantissa --run-puzzles --puzzle-suite puzzles/bk.epd --puzzle-movetime 10000
```
Run the engine Mantissa against the BK set of puzzles, given 10 seconds per move.
