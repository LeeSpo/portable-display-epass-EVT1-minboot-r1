#!/usr/bin/env python3
"""Connect filled outer-layer GND islands to the two internal GND planes."""
import argparse,json,sys,math
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,Point
from shapely.ops import nearest_points
from finish_power_routes import Router,rb
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pcb_parser import parse,nodes,one,val

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);o=ap.parse_args()
    rb.BOARD=Path(o.board);r=Router(rb.load(o.board));tree=parse(Path(o.board).read_text());report=[]
    for z in nodes(tree,'zone'):
        if val(one(z,'net_name',one(z,'net',['net','""']))[-1])!='GND':continue
        for fp in nodes(z,'filled_polygon'):
            layer=val(one(fp,'layer')[1])
            if layer not in ['F.Cu','B.Cu','In2.Cu']:continue
            pts=[tuple(map(float,n[1:])) for n in nodes(one(fp,'pts'),'xy')]
            geom=shapely.make_valid(Polygon(pts))
            polys=[geom] if geom.geom_type=='Polygon' else [g for g in geom.geoms if g.geom_type=='Polygon']
            for poly in polys:
                through=[i for i in r.items if i.net=='GND' and (i.kind=='via' or i.kind=='pad' and 'B.Cu' in i.layers)]
                if any(poly.intersects(i.geom) for i in through):continue
                x0,y0,x1,y1=poly.bounds
                xx,yy=np.meshgrid(np.arange(x0,x1+.001,.20),np.arange(y0,y1+.001,.20))
                xx,yy=xx.ravel(),yy.ravel();inside=shapely.contains_xy(poly,xx,yy)
                pts=[(float(x),float(y)) for x,y in zip(xx[inside],yy[inside])]
                pts.sort(key=lambda p:poly.boundary.distance(Point(p)),reverse=True)
                success=False
                for x,y in pts[:2500]:
                    hole=Point(x,y).buffer(.15)
                    if any(i.kind=='pad' and i.geom.distance(hole)<.10 for i in r.items):continue
                    if r.add_via(x,y,'GND'):
                        report.append({'layer':layer,'area_mm2':poly.area,'via':[x,y]});success=True;break
                if not success and layer in ['F.Cu','B.Cu']:
                    # A narrow island may need a short neck to a via outside it.
                    candidates=[]
                    for x in np.arange(x0-1.5,x1+1.5,.2):
                        for y in np.arange(y0-1.5,y1+1.5,.2):
                            p=Point(float(x),float(y));distance=p.distance(poly)
                            if 0<distance<=1.5:candidates.append((distance,float(x),float(y)))
                    for _,x,y in sorted(candidates)[:3500]:
                        hole=Point(x,y).buffer(.15)
                        if any(i.kind=='pad' and i.geom.distance(hole)<.10 for i in r.items):continue
                        q=nearest_points(poly,Point(x,y))[0]
                        other='B.Cu' if layer=='F.Cu' else 'F.Cu'
                        if r.commit_xy([(q.x,q.y,layer),(x,y,layer),(x,y,other)],.18,'GND'):
                            report.append({'layer':layer,'area_mm2':poly.area,'via':[x,y],'neck_from':[q.x,q.y]});success=True;break
                if not success:report.append({'layer':layer,'area_mm2':poly.area,'bounds':list(poly.bounds),'unresolved':True})
    r.write();Path(o.report).write_text(json.dumps(report,indent=2));print('islands',len(report),'unresolved',sum(bool(x.get('unresolved')) for x in report))

if __name__=='__main__':main()
