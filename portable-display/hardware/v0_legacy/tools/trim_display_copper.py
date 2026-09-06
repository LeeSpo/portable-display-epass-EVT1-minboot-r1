#!/usr/bin/env python3
"""Trim native-reported dangling tails without deleting their connected branches.

Writes a candidate only. Report and filled board must come from the same native
check of input. Refill and native DRC are required after each pass.
"""
import argparse,json,math
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import nearest_points
from geometry_audit import board_items,connected_groups
from complete_minboot import filled_items
from kicad_sexpr import load,dump,val,setval,children

def trim(board,filled,report):
    items=board_items(board);zones=filled_items(filled);remove=set();result=[]
    flagged={i['uuid']:v['type'] for v in report['violations'] if v['type'] in {'track_dangling','via_dangling'} for i in v['items']}
    # Entire copper fragments with no pad or filled-plane connection are obsolete.
    for group in connected_groups(items+zones):
        if not any(i.kind in {'pad','zone'} for i in group):
            remove.update(id(i.node) for i in group if i.kind in {'track','via'})
    for it in items:
        uid=str(val(it.node,'uuid'))
        if uid not in flagged or id(it.node) in remove:continue
        if it.kind=='via':remove.add(id(it.node));continue
        if it.kind!='track':continue
        line=LineString(it.pos);positions=[]
        for other in items+zones:
            if other is it or id(other.node) in remove or other.net!=it.net or not(other.layers&it.layers):continue
            if it.geom.distance(other.geom)>1e-6:continue
            if other.kind=='track':
                ol=LineString(other.pos);cross=line.intersection(ol)
                if cross.is_empty:positions.append(line.project(nearest_points(line,ol)[0]))
                elif cross.geom_type=='Point':positions.append(line.project(cross))
                elif cross.geom_type=='MultiPoint':positions.extend(line.project(p) for p in cross.geoms)
                else:
                    for p in other.pos:positions.append(line.project(Point(p)))
            elif other.kind in {'pad','via'}:positions.append(line.project(Point(other.pos)))
            elif other.kind=='zone':
                cross=line.intersection(other.geom)
                if not cross.is_empty:
                    def coords(g):
                        if hasattr(g,'geoms'):
                            for p in g.geoms:yield from coords(p)
                        elif g.geom_type in {'Point','LineString'}:yield from g.coords
                    positions.extend(line.project(Point(p)) for p in coords(cross))
        if not positions or max(positions)-min(positions)<1e-5:remove.add(id(it.node));continue
        a=line.interpolate(min(positions));b=line.interpolate(max(positions))
        setval(it.node,'start',round(a.x,4),round(a.y,4));setval(it.node,'end',round(b.x,4),round(b.y,4))
        result.append({'uuid':uid,'action':'trim','from':it.pos,'to':[[a.x,a.y],[b.x,b.y]]})
    for it in items:
        if id(it.node) in remove:result.append({'uuid':str(val(it.node,'uuid')),'net':it.net,'action':'remove'})
    board[:]=[n for n in board if id(n) not in remove]
    for z in children(board,'zone'):z[:]=[x for x in z if not isinstance(x,list) or x[0] not in {'filled_polygon','fill_segments'}]
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['input','filled','report','output']:p.add_argument(name,type=Path)
    a=p.parse_args();b=load(a.input);result=trim(b,load(a.filled),json.loads(a.report.read_text()));dump(b,a.output)
    a.output.with_suffix('.trim.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
