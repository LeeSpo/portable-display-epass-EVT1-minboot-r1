#!/usr/bin/env python3
"""Use KiCad's Python; only called on a disposable checked_project snapshot."""
import argparse
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('board',type=Path);a=p.parse_args()
    if a.board.parent.name!='checked_project':raise SystemExit('Refusing to refill the editable source PCB; use verify_evt1.py')
    import pcbnew
    board=pcbnew.LoadBoard(str(a.board))
    if board is None:raise RuntimeError('KiCad failed to load staged board')
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if not pcbnew.SaveBoard(str(a.board),board):raise RuntimeError('KiCad failed to save refilled board')
    print('Zone fill completed on isolated verification snapshot')
if __name__=='__main__':main()
