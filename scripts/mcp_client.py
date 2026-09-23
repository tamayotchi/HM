"""Client for the same local home-assistant MCP endpoint configured in this session."""
import json, requests
from pathlib import Path
class HomeAssistantMCP:
    def __init__(self):
        cfg=json.loads((Path(__file__).resolve().parents[1]/'.pi/mcp.json').read_text())
        self.url=cfg['mcpServers']['home-assistant']['url']
        self.session=requests.Session();self.session.headers.update({'Accept':'application/json, text/event-stream','Content-Type':'application/json'})
        self.counter=0
        self.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'ha-floorplan-build','version':'1.0'}})
        self.session.post(self.url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()
    def rpc(self,method,params):
        self.counter+=1
        r=self.session.post(self.url,json={'jsonrpc':'2.0','id':self.counter,'method':method,'params':params},timeout=120)
        r.raise_for_status()
        r.encoding='utf-8'  # SSE/JSON-RPC are UTF-8, even without a charset header.
        if r.headers.get('Mcp-Session-Id'):self.session.headers['Mcp-Session-Id']=r.headers['Mcp-Session-Id']
        if 'text/event-stream' in r.headers.get('Content-Type',''):
            events=[]
            for block in r.text.replace('\r\n','\n').split('\n\n'):
                payload='\n'.join(line[5:].lstrip(' ') for line in block.split('\n') if line.startswith('data:'))
                if payload:events.append(json.loads(payload))
            reply=next(e for e in events if e.get('id')==self.counter)
        else:reply=r.json()
        if 'error' in reply:raise RuntimeError(reply['error'])
        return reply.get('result',{})
    def call(self,name,args):
        result=self.rpc('tools/call',{'name':name,'arguments':args})
        if result.get('isError'):raise RuntimeError(result)
        if 'structuredContent' in result:return result['structuredContent']
        texts=[x['text'] for x in result.get('content',[]) if x.get('type')=='text']
        if len(texts)==1:
            try:return json.loads(texts[0])
            except json.JSONDecodeError:return {'text':texts[0]}
        return {'text':'\n'.join(texts)}
