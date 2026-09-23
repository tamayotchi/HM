"""Publish floor cards through MCP with a single safety snapshot, optimistic locking and read-back.
Use --images-only for visual revisions: no other card fields may change.
"""
import argparse,json,re
from pathlib import Path
from mcp_client import HomeAssistantMCP
from project_paths import ROOT, DASHBOARD, REPORTS
parser=argparse.ArgumentParser()
parser.add_argument('--snapshot',default='build/reports/before-publish.json',help='Single overwritten pre-write safety record; not created by a dry run')
parser.add_argument('--record',default='build/reports/deployment.json')
parser.add_argument('--images-only',action='store_true')
parser.add_argument('--allow-add-view',action='append',default=[],help='Explicit view paths permitted to be added; existing views are never removed')
parser.add_argument('--preserve-view',action='append',default=[],help='Abort if a protected view differs from the generated version')
parser.add_argument('--dry-run',action='store_true',help='Read/compare only; never publish or replace local generated config')
args=parser.parse_args()
mcp=HomeAssistantMCP();local=json.loads((DASHBOARD/'dashboard.json').read_text())
current=mcp.call('ha_config_get_dashboard',{'url_path':'house-3d','force_reload':True});assert current['success']
expected=json.loads(json.dumps(current['config']));patch=[];changed=[];added=[]
local_paths=[v['path'] for v in local['views']]
assert len(local_paths)==len(set(local_paths)),'Duplicate generated view paths'
assert all(path in local_paths for path in args.preserve_view),'Protected view absent from generated config'
for desired_view in local['views']:
    path=desired_view['path']
    matches=[i for i,v in enumerate(current['config']['views']) if v.get('path')==path]
    assert len(matches)<=1,'Ambiguous existing view path: '+path
    if not matches:
        assert path in args.allow_add_view and not args.images_only and path not in args.preserve_view,'View addition not explicitly authorized: '+path
        assert len(desired_view['cards'])==1
        assert desired_view['cards'][0]['type'] in ('custom:house-floorplan-card','custom:house-overview-card')
        patch.append({'op':'add','path':'/views/-','value':desired_view})
        expected['views'].append(desired_view);added.append(path);changed.append(path)
        continue
    index=matches[0]
    desired=desired_view['cards'][0]
    previous=current['config']['views'][index]['cards'][0]
    if path in args.preserve_view:
        assert desired==previous,'Protected card changed: '+path
        continue
    if desired['type']=='custom:house-overview-card':
        assert previous['type']==desired['type'] and path=='all-floors'
        def bindings(card):
            return [(f['navigation_path'], [l['entity'] for l in f['lights']],
                     [o['entity'] for o in f.get('openings',[])]) for f in card['floors']]
        assert bindings(previous)==bindings(desired),'Overview device bindings changed'
        if previous!=desired:
            if args.images_only:
                image_update=json.loads(json.dumps(previous))
                for old,new in zip(image_update['floors'],desired['floors']):
                    old['image']=new['image']
                    for a,b in zip(old['lights'],new['lights']):a['image']=b['image']
                assert image_update==desired,'Non-image overview changes found'
            patch.append({'op':'replace','path':f'/views/{index}/cards/0','value':desired})
            expected['views'][index]['cards'][0]=desired;changed.append(path)
        continue
    assert previous['type']==desired['type']=='custom:house-floorplan-card'
    assert [x['entity'] for x in desired['lights']]==[x['entity'] for x in previous['lights']],'Existing light IDs/order changed'
    assert [o['entity'] for o in desired.get('openings',[])]==[o['entity'] for o in previous.get('openings',[])],'Opening contact IDs changed'
    base=f'/views/{index}/cards/0'
    if args.images_only:
        image_update=json.loads(json.dumps(previous));image_update['image']=desired['image']
        for i,light in enumerate(desired['lights']):image_update['lights'][i]['image']=light['image']
        assert image_update==desired,'Non-image card changes found; inspect before publishing'
        if previous['image']!=desired['image']:patch.append({'op':'replace','path':base+'/image','value':desired['image']})
        for i,light in enumerate(desired['lights']):
            if previous['lights'][i]['image']!=light['image']:patch.append({'op':'replace','path':base+f'/lights/{i}/image','value':light['image']})
    elif previous!=desired:
        patch.append({'op':'replace','path':base,'value':desired})
    expected['views'][index]['cards'][0]=desired
    if previous!=desired:changed.append(path)
if args.dry_run:
    print(json.dumps({'dry_run':True,'config_hash':current['config_hash'],'changed_floor_cards':changed,'added_views':added,'patch':patch},indent=2));raise SystemExit(0)
REPORTS.mkdir(parents=True,exist_ok=True)
if patch:
    snapshot=ROOT/args.snapshot;snapshot.parent.mkdir(parents=True,exist_ok=True)
    snapshot.write_text(json.dumps(current,indent=2))
    guide=mcp.call('ha_get_skill_guide',{'skill':'home-assistant-best-practices','file':'SKILL.md'})['content']
    assert '**Core principle:** Use native Home Assistant constructs' in guide
    (REPORTS/'ha-best-practices-read-receipt.md').write_text(guide)
    key=re.search(r'Acknowledgment key: ([\w-]+)',guide).group(1)
    result=mcp.call('ha_config_set_dashboard',{'url_path':'house-3d','config_hash':current['config_hash'],'patch':patch,'MandatoryBPS':False,'BestPracticeKey':key})
    assert result.get('success'),result
else:result={'success':True,'no_changes':True}
remote=mcp.call('ha_config_get_dashboard',{'url_path':'house-3d','force_reload':True})
assert remote['config']==expected,'Unexpected dashboard difference on read-back'
(DASHBOARD/'dashboard.json').write_text(json.dumps(remote['config'],indent=2))
(REPORTS/'dashboard-current.json').write_text(json.dumps(remote,indent=2))
summary={'success':True,'config_hash':remote['config_hash'],'existing_light_entity_ids_preserved':True,'unchanged_opening_sensor_ids':True,'changed_floor_cards':changed,'added_views':added,'protected_views':args.preserve_view,'only_image_urls_changed':args.images_only,'unrelated_config_unchanged':True,'opening_indicators':'read-only binary sensors','write':result}
record=ROOT/args.record;record.parent.mkdir(parents=True,exist_ok=True);record.write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='write'},indent=2))
