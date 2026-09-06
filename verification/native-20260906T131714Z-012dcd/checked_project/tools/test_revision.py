import csv,hashlib,json,math,subprocess,sys,tempfile,unittest
from pathlib import Path
import generate_evt1 as gen
from geometry_audit import rotation,board_items,connected_groups,issues
from kicad_sexpr import loads,dumps,load,children,child,val,values,props
from static_verify import run,snapshot,unique_uuids
from export_metadata import export
from verify_evt1 import validate_signoffs
ROOT=Path(__file__).resolve().parents[1]

class FormatAndTransformTests(unittest.TestCase):
    def test_quoted_atoms_roundtrip(self):
        text='(root (quoted "a \\"b\\" c") (bare yes) (number -1.25))';self.assertEqual(loads(dumps(loads(text))),loads(text))
    def test_unbalanced_rejected(self):
        with self.assertRaises(ValueError):loads('(root')
    def test_multiple_roots_rejected(self):
        with self.assertRaises(ValueError):loads('(a)(b)')
    def test_no_code_execution(self):self.assertEqual(loads('(x "__import__(\\"os\\")")')[0],'x')
    def test_positive90_y_down(self):
        x,y=rotation(1,0,90);self.assertAlmostEqual(x,0);self.assertAlmostEqual(y,-1)
    def test_positive270_y_down(self):
        x,y=rotation(1,0,270);self.assertAlmostEqual(x,0);self.assertAlmostEqual(y,1)
    def test_segment_uuids_unique(self):
        a=loads(gen._seg(0,0,0,1,.09,'F.Cu','GND',{'GND':1},'same'))
        b=loads(gen._seg(0,1,0,2,.09,'F.Cu','GND',{'GND':1},'same'))
        self.assertNotEqual(val(a,'uuid'),val(b,'uuid'))
    def test_duplicate_uuid_detected(self):self.assertTrue(unique_uuids(loads('(root (a (uuid "x")) (b (uuid "x")))')))
    def test_via_uuid_includes_net_and_position(self):
        vias=[loads(gen._via(x,2,net,{'A':1,'B':2},'reused-tag')) for x,net in [(1,'A'),(2,'A'),(1,'B')]]
        self.assertEqual(len({val(v,'uuid') for v in vias}),3)
    def test_molex_staggered_land_pattern(self):
        pads={p[1]:p for p in children(load(ROOT/'sameat.pretty/FPC45.kicad_mod'),'pad')}
        self.assertEqual(len(pads),47)
        self.assertAlmostEqual(float(val(pads['3'],'at'))-float(val(pads['1'],'at')),.6)
        self.assertAlmostEqual(float(values(pads['2'],'at')[1])-float(values(pads['1'],'at')[1]),-3.065)
        self.assertEqual([float(x) for x in values(pads['1'],'size')],[.3,.67])
        self.assertEqual([float(x) for x in values(pads['2'],'size')],[.3,.5])
    def test_ti_dpd_package_dimensions(self):
        pads={p[1]:p for p in children(load(ROOT/'sameat.pretty/WSON-12.kicad_mod'),'pad')}
        self.assertAlmostEqual(abs(float(values(pads['2'],'at')[1])-float(values(pads['1'],'at')[1])),.45)
        self.assertEqual([float(x) for x in values(pads['13'],'size')],[1.21,2.02])
        self.assertEqual(float(val(pads['13'],'solder_paste_margin_ratio')),-.15)
    def test_single_lane_and_legacy_backlight_removed(self):
        devs={d.ref:d for d in gen.devices()}
        for pin in ['82','83']:self.assertIsNone(devs['U2'].pins[pin][1])
        self.assertIsNone(devs['J4'].pins['13'][1])
        self.assertTrue(devs['R31'].dnp)
        self.assertFalse({'U7','L4','D4','R19','C27','C28'}&devs.keys())
    def test_whole_board_regeneration_disabled(self):
        with self.assertRaises(RuntimeError):gen.board(gen.devices())
    def test_old_bom_export_disabled(self):
        with self.assertRaises(RuntimeError):gen.write_bom(gen.devices())
    def test_tps22918_datasheet_pinmap(self):
        u=next(d for d in gen.devices() if d.ref=='U8');self.assertEqual(len(u.pins),6);self.assertEqual(u.footprint,'SOT23-6');self.assertEqual(u.pins['6'],('VOUT','LCD_3V3'));self.assertEqual(u.pins['4'],('CT',None));self.assertEqual(u.pins['5'],('QOD',None))
    def test_source_generation_no_default_writes(self):
        before=snapshot();r=subprocess.run([sys.executable,ROOT/'tools/generate_evt1.py'],capture_output=True,text=True);self.assertEqual(r.returncode,0);self.assertEqual(snapshot(),before)
    def test_unsigned_release_blocks(self):self.assertTrue(validate_signoffs(ROOT))

class DesignIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=run();cls.board=load(ROOT/'portable_display_epass.kicad_pcb')
    def test_static_checks_pass(self):self.assertEqual(self.report['problems'],[])
    def test_static_never_approves_fabrication(self):self.assertFalse(self.report['fabrication_released']);self.assertFalse(self.report['native_kicad_executed'])
    def test_54_pins_reach_via_or_another_intended_pad(self):self.assertEqual(self.report['counts']['u2_pins_with_via_or_peer_connection'],54)
    def test_direct_route_rule_rejects_an_isolated_soc_pin(self):
        # Removing XIN copper must fail even though other XIN pads still exist.
        import copy
        from unittest.mock import patch
        board=copy.deepcopy(self.board)
        remove={id(i.node) for i in board_items(board) if i.net=='XIN' and i.kind in {'track','via'}}
        board[:]=[x for x in board if id(x) not in remove]
        original_load=load
        def altered(path):
            return board if Path(path)==ROOT/'portable_display_epass.kicad_pcb' else original_load(path)
        with patch('static_verify.load',side_effect=altered):report=run()
        self.assertIn('Non-display U2 fanout incomplete',report['problems'])
        self.assertLess(report['counts']['u2_pins_with_via_or_peer_connection'],54)
    def test_zero_checked_spacing_issues(self):self.assertEqual(self.report['counts']['geometric_issues'],0)
    def test_source_pcb_schematic_component_count(self):self.assertEqual(self.report['counts']['schematic_components'],120);self.assertEqual(self.report['counts']['footprints'],124)
    def test_u9_chains_match_their_logical_pads(self):
        for group in connected_groups(board_items(self.board)):
            p=[x for x in group if x.ref=='U9']
            if p:self.assertTrue(all(x.net==p[0].net for x in group))
    def test_stale_zone_fill_removed(self):self.assertFalse(any(children(z,'filled_polygon') for z in children(self.board,'zone')))
    def test_unrouted_nets_are_reported(self):self.assertTrue(self.report['opens_excluding_zone_connectivity'])
    def test_coordinates_come_from_board(self):
        with tempfile.TemporaryDirectory() as t:
            manifest=export(output=t)
            with (Path(t)/'placement_PREVIEW_NOT_FOR_ASSEMBLY.csv').open() as f:rows={r['Reference']:r for r in csv.DictReader(f)}
            self.assertEqual(float(rows['C34']['Board_X_mm']),15.5);self.assertEqual(float(rows['C34']['Y_mm_up_from_origin']),49)
            self.assertEqual(float(rows['C39']['Board_X_mm']),18);self.assertEqual(float(rows['C39']['Y_mm_up_from_origin']),19)
            self.assertFalse(manifest['fabrication_released'])
if __name__=='__main__':unittest.main()
