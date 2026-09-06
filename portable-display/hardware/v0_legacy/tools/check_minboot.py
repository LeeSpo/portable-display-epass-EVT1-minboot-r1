#!/usr/bin/env python3
"""Fail-closed validation of fresh native KiCad netlist/ERC/DRC outputs.

Standalone report inspection is not fabrication approval. verify_evt1.py owns
fresh-run provenance, source hashing, zone refill and release signoff checks.
"""
from __future__ import annotations
from pathlib import Path
import argparse,csv,json,re,xml.etree.ElementTree as ET
DISPLAY_NETS={'DSI_D0P','DSI_D0N','DSI_D1P','DSI_D1N','DSI_CKP','DSI_CKN','LCD_RST','LCD_PWM','LCD_EN','LCD_3V3','LEDA','LEDK','BL_SW'}
FLAGS={f'#FLG{i+1}':n for i,n in enumerate(('GND','VBUS','VBAT','3V3','CORE_0V93','DRAM_1V5'))}

def erc_violations(report):
    if not isinstance(report,dict):raise ValueError('ERC report must be an object')
    found=[]
    if 'violations' in report:
        if not isinstance(report['violations'],list):raise ValueError('ERC violations must be an array')
        found.extend(report['violations'])
    if 'sheets' in report:
        sheets=report['sheets']
        if not isinstance(sheets,list) or not sheets:raise ValueError('ERC sheets must be a non-empty array')
        for sheet in sheets:
            if not isinstance(sheet,dict) or not isinstance(sheet.get('violations'),list):raise ValueError('Malformed ERC sheet')
            found.extend(sheet['violations'])
    elif 'violations' not in report:raise ValueError('Missing ERC violations/sheets')
    if any(not isinstance(v,dict) for v in found):raise ValueError('Malformed ERC violation')
    return found

def report_schema(report,kind):
    if not isinstance(report,dict):return [kind+': report is not an object']
    errors=[]
    for key in ('date','kicad_version','source'):
        if not isinstance(report.get(key),str) or not report[key]:errors.append(f'{kind}: missing {key}')
    if kind=='DRC':
        for key in ('violations','unconnected_items','schematic_parity'):
            if not isinstance(report.get(key),list):errors.append(f'DRC: missing/malformed {key}')
    return errors

def check_reports(erc,drc,*,allow_display=True):
    problems=report_schema(erc,'ERC')+report_schema(drc,'DRC')
    try:ev=erc_violations(erc)
    except (ValueError,TypeError) as e:problems.append(str(e));ev=[]
    # Do not silently accept warnings/exclusions or missing severities.
    for v in ev:problems.append('ERC '+str(v.get('severity','unknown'))+': '+str(v.get('description','missing description')))
    if not isinstance(drc,dict):return problems
    for key in ('violations','schematic_parity'):
        entries=drc.get(key,[])
        if not isinstance(entries,list):continue
        for v in entries:
            if not isinstance(v,dict):problems.append('Malformed DRC '+key);continue
            problems.append('DRC '+key+' '+str(v.get('severity','unknown'))+': '+str(v.get('description','missing description')))
    entries=drc.get('unconnected_items',[])
    if not isinstance(entries,list):return problems
    for v in entries:
        if not isinstance(v,dict):problems.append('Malformed unconnected item');continue
        items=v.get('items')
        if not isinstance(items,list) or not items:problems.append('Unconnected item has no identifiable endpoints');continue
        all_nets=[];ambiguous=False
        for item in items:
            desc=item.get('description') if isinstance(item,dict) else None
            names=re.findall(r'\[([^\]]+)\]',desc) if isinstance(desc,str) else []
            if len(names)!=1:ambiguous=True
            all_nets.extend(names)
        names=set(all_nets)
        if not allow_display or ambiguous or len(names)!=1 or not names.issubset(DISPLAY_NETS):
            problems.append('Unconnected non-exempt or ambiguous net: '+str(sorted(names)))
    return problems

def check_netlist(xml_file,pin_file):
    data=Path(xml_file).read_bytes()
    if b'<!DOCTYPE' in data or b'<!ENTITY' in data:raise ValueError('DTD/entity declarations are not allowed')
    root=ET.fromstring(data)
    if root.tag!='export':return ['Expected a KiCad XML export root']
    with Path(pin_file).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not {'Reference','Pin','Net'}.issubset(reader.fieldnames or []):return ['Malformed expected pin CSV']
        rows=list(reader)
    if not rows:return ['Empty expected pin contract']
    expected={};problems=[]
    for r in rows:
        key=r['Reference'],r['Pin']
        if key in expected:problems.append('Duplicate expected pin '+str(key))
        expected[key]=r['Net']
    refs=[c.attrib.get('ref','') for c in root.findall('./components/comp')]
    expected_refs={r[0] for r in expected}
    if len(set(refs))!=len(refs):problems.append('Duplicate native netlist reference')
    actual_refs=set(refs)-set(FLAGS)
    if actual_refs!=expected_refs:problems.append(f'Loaded component set differs: missing={sorted(expected_refs-actual_refs)}, extra={sorted(actual_refs-expected_refs)}')
    actual={};nets=root.findall('./nets/net')
    if not nets:problems.append('Native netlist has no nets')
    names=[n.attrib.get('name','') for n in nets]
    if len(names)!=len(set(names)) or '' in names:problems.append('Missing or duplicate native net name')
    for net in nets:
        name=net.attrib.get('name','')
        for node in net.findall('node'):
            key=node.attrib.get('ref',''),node.attrib.get('pin','')
            if key in actual:problems.append('Native pin appears on multiple/duplicate nets: '+str(key))
            actual[key]=name
            if key[0] in FLAGS:
                if key[1]!='1' or name!=FLAGS[key[0]]:problems.append('Supply flag on unexpected pin/net: '+str(key))
            elif key not in expected:problems.append('Unexpected native pin: '+str(key))
    for key,net in expected.items():
        found=actual.get(key)
        if net=='NC':
            if found is not None and not found.startswith('unconnected-'):problems.append(f'{key}: NC connected to {found}')
        elif found!=net:problems.append(f'{key}: expected {net}, found {found}')
    return problems

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--full-board',action='store_true');a=p.parse_args()
    try:
        erc=json.loads((a.directory/'erc.json').read_text());drc=json.loads((a.directory/'drc.json').read_text())
        problems=check_netlist(a.directory/'netlist.xml',a.directory/'net_pin_report.csv')+check_reports(erc,drc,allow_display=not a.full_board)
    except (OSError,ValueError,KeyError,ET.ParseError) as e:problems=[f'{type(e).__name__}: {e}']
    result={'passed':not problems,'fabrication_released':False,'provenance_verified':False,'scope':'full_board' if a.full_board else 'non_display','problems':problems}
    (a.directory/'minboot_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(bool(problems))
if __name__=='__main__':main()
