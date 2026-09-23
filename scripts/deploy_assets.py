"""Upload PNGs with HA's supported image API; register the card via the session MCP."""
import os, json, hashlib
from pathlib import Path
import requests
from mcp_client import HomeAssistantMCP
from dashboard_config import build_dashboard
from project_paths import DASHBOARD, IMAGES, PREPARED, REPORTS, load_config, ensure_output_dirs
ensure_output_dirs()
URL=os.environ['PI_MCP_HOMEASSISTANT_URL'].rstrip('/')
TOKEN=os.environ['PI_MCP_HOMEASSISTANT_TOKEN']
session=requests.Session();session.headers['Authorization']='Bearer '+TOKEN
manifest_path=DASHBOARD/'upload-manifest.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'images':{},'server':URL}
assert manifest['server']==URL
config=json.loads(PREPARED.read_text())
def upload(name):
    p=IMAGES/name;digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if name in manifest['images'] and manifest['images'][name]['sha256']==digest:
        return manifest['images'][name]['url']
    with p.open('rb') as stream:
        r=session.post(URL+'/api/image/upload',files={'file':(name,stream,'image/png')},timeout=90)
    r.raise_for_status();item=r.json()
    url=f'/api/image/serve/{item["id"]}/original'
    check=session.get(URL+url,timeout=30);check.raise_for_status()
    assert hashlib.sha256(check.content).hexdigest()==digest
    manifest['images'][name]={'sha256':digest,'url':url,'id':item['id'],'bytes':p.stat().st_size}
    manifest_path.write_text(json.dumps(manifest,indent=2))
    print('Uploaded and verified',name,p.stat().st_size,flush=True)
    return url
source_layout=load_config()
dashboard=build_dashboard(config,source_layout,upload)
(DASHBOARD/'dashboard.json').write_text(json.dumps(dashboard,indent=2))
mcp=HomeAssistantMCP()
args={'content':(DASHBOARD/'house-floorplan-card.js').read_text(),'resource_type':'module'}
if manifest.get('resource_id'):args['resource_id']=manifest['resource_id']
result=mcp.call('ha_config_set_dashboard_resource',args)
(REPORTS/'resource-write.json').write_text(json.dumps(result,indent=2))
if not result.get('success'):raise RuntimeError('Resource registration failed: '+str(result))
print('Resource result keys',list(result))
# Keep only the ID in the manifest; the latest API result is in build/reports.
manifest['resource_id']=result.get('resource_id') or result.get('resource',{}).get('id') or result.get('id')
manifest_path.write_text(json.dumps(manifest,indent=2))
overview_args={'content':(DASHBOARD/'house-overview-card.js').read_text(),'resource_type':'module'}
if manifest.get('overview_resource_id'):overview_args['resource_id']=manifest['overview_resource_id']
overview_result=mcp.call('ha_config_set_dashboard_resource',overview_args)
assert overview_result.get('success'),overview_result
manifest['overview_resource_id']=overview_result.get('resource_id') or overview_result.get('resource',{}).get('id') or overview_result.get('id')
assert manifest['overview_resource_id'],'Missing overview resource ID'
manifest_path.write_text(json.dumps(manifest,indent=2))
(REPORTS/'overview-resource-write.json').write_text(json.dumps(overview_result,indent=2))
print('Assets deployed. Dashboard config:',DASHBOARD/'dashboard.json')
