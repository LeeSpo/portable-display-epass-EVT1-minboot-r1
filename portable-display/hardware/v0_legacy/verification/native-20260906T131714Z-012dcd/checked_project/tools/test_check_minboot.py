import copy,csv,json,tempfile,unittest
from pathlib import Path
from check_minboot import check_reports,erc_violations,check_netlist

def reports():
    common={'date':'2026-09-05T00:00:00','kicad_version':'9.0.6','source':'portable_display_epass'}
    return ({**common,'sheets':[{'path':'/','violations':[]}]},{**common,'violations':[],'unconnected_items':[],'schematic_parity':[]})

def opened(net):return {'severity':'error','description':'Unconnected','items':[{'description':f'Pad 1 [{net}]'},{'description':f'Pad 2 [{net}]'}]}

class ReleaseGateTests(unittest.TestCase):
    def test_empty_reports_fail_closed(self):self.assertTrue(check_reports({},{}))
    def test_well_formed_clean_reports(self):self.assertFalse(check_reports(*reports()))
    def test_nested_erc_is_not_silently_ignored(self):
        e,d=reports();e['sheets'][0]['violations']=[{'severity':'error','description':'power conflict'}]
        self.assertEqual(len(erc_violations(e)),1);self.assertTrue(check_reports(e,d))
    def test_erc_warning_blocks(self):
        e,d=reports();e['sheets'][0]['violations']=[{'severity':'warning','description':'bad pin'}];self.assertTrue(check_reports(e,d))
    def test_missing_erc_severity_blocks(self):
        e,d=reports();e['sheets'][0]['violations']=[{'description':'unknown'}];self.assertTrue(check_reports(e,d))
    def test_missing_metadata_blocks(self):
        e,d=reports();del e['date'];self.assertTrue(check_reports(e,d))
    def test_empty_sheets_blocks(self):
        e,d=reports();e['sheets']=[];self.assertTrue(check_reports(e,d))
    def test_nonshort_errors_block(self):
        e,d=reports();d['violations']=[{'severity':'error','description':'hole spacing'}];self.assertTrue(check_reports(e,d))
    def test_parity_warning_blocks(self):
        e,d=reports();d['schematic_parity']=[{'severity':'warning','description':'extra footprint'}];self.assertTrue(check_reports(e,d))
    def test_display_exception_is_limited(self):
        e,d=reports();d['unconnected_items']=[opened('DSI_D0P')];self.assertFalse(check_reports(e,d));self.assertTrue(check_reports(e,d,allow_display=False))
    def test_non_display_opens_block(self):
        for n in ('GND','USB_DM','NAND_MOSI','SOC_LDO_1V8'):
            with self.subTest(n=n):
                e,d=reports();d['unconnected_items']=[opened(n)];self.assertTrue(check_reports(e,d))
    def test_unknown_endpoint_blocks(self):
        e,d=reports();v=opened('DSI_D0P');v['items'][1]['description']='unknown';d['unconnected_items']=[v];self.assertTrue(check_reports(e,d))
    def test_multiple_display_net_names_block(self):
        e,d=reports();v=opened('DSI_D0P');v['items'][1]['description']='Pad [DSI_D0N]';d['unconnected_items']=[v];self.assertTrue(check_reports(e,d))
    def test_malformed_drc_arrays_block(self):
        e,d=reports();d['violations']={};self.assertTrue(check_reports(e,d))
    def test_missing_parity_section_blocks(self):
        e,d=reports();del d['schematic_parity'];self.assertTrue(check_reports(e,d))

class NetlistTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.pin=self.root/'pins.csv';self.xml=self.root/'net.xml'
        self.pin.write_text('Reference,Pin,Pin Name,Net\nU1,1,VDD,3V3\nU1,2,NC,NC\n')
    def tearDown(self):self.tmp.cleanup()
    def check(self,body):
        self.xml.write_text(body);return check_netlist(self.xml,self.pin)
    def test_complete(self):
        self.assertFalse(self.check('<export><components><comp ref="U1"/></components><nets><net name="3V3"><node ref="U1" pin="1"/></net></nets></export>'))
    def test_missing_component(self):self.assertTrue(self.check('<export><components/><nets/></export>'))
    def test_duplicate_pin(self):
        self.assertTrue(self.check('<export><components><comp ref="U1"/></components><nets><net name="3V3"><node ref="U1" pin="1"/><node ref="U1" pin="1"/></net></nets></export>'))
    def test_nc_connected(self):
        self.assertTrue(self.check('<export><components><comp ref="U1"/></components><nets><net name="3V3"><node ref="U1" pin="1"/><node ref="U1" pin="2"/></net></nets></export>'))
    def test_wrong_net(self):
        self.assertTrue(self.check('<export><components><comp ref="U1"/></components><nets><net name="GND"><node ref="U1" pin="1"/></net></nets></export>'))
    def test_dtd_rejected(self):
        with self.assertRaises(ValueError):self.check('<!DOCTYPE export><export/>')
    def test_unknown_pin(self):
        self.assertTrue(self.check('<export><components><comp ref="U1"/></components><nets><net name="3V3"><node ref="U1" pin="1"/><node ref="U1" pin="99"/></net></nets></export>'))
if __name__=='__main__':unittest.main()
