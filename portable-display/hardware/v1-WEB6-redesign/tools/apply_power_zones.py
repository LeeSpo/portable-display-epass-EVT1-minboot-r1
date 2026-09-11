#!/usr/bin/env python3
"""Apply generated In2 polygons with native KiCad, refill and save the board."""
import argparse,json
import pcbnew as p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('polygons');o=ap.parse_args()
    b=p.LoadBoard(o.board);nets=b.GetNetsByName()
    # The existing In2 GND pour remains as priority-zero background.
    for z in b.Zones():
        if z.GetIsRuleArea():continue
        z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetPadConnection(p.ZONE_CONNECTION_THT_THERMAL)
    for rec in json.load(open(o.polygons))['zones']:
        z=p.ZONE(b);z.SetLayer(p.In2_Cu);z.SetNetCode(nets[rec['net']].GetNetCode())
        z.SetAssignedPriority(1);z.SetLocalClearance(p.FromMM(.18));z.SetMinThickness(p.FromMM(.15))
        z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
        outline=z.Outline();oi=outline.NewOutline()
        for x,y in rec['outer']:outline.Append(p.FromMM(x),p.FromMM(y),oi)
        for hole in rec['holes']:
            hi=outline.NewHole(oi)
            for x,y in hole:outline.Append(p.FromMM(x),p.FromMM(y),oi,hi)
        b.Add(z)
    critical={'XIN','XOUT','DSI_CKN','DSI_CKP','DSI_D0N','DSI_D0P','USB_DP','USB_DM','SD_CLK','LX_3V3','LX_CORE','LX_DRAM','EL_SWP','EL_SWN'}
    for t in b.GetTracks():
        if t.GetNetname() in critical:t.SetLocked(True)
    b.SetLayerName(p.In1_Cu,'In1.Cu');b.SetLayerName(p.In2_Cu,'In2.Cu')
    p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(o.board,b)

if __name__=='__main__':main()
