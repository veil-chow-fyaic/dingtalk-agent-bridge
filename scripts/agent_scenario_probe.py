#!/usr/bin/env python3
"""Explicit synthetic probes in the already authorized solo group; durable intent, no blind replay."""
import argparse,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.probe_support import Probe,unwrap
from dingtalk_bridge.routing import route_configs

CASES={
 'status':'/agent status',
 'slow':'/agent [DAB-SCENARIO-SLOW] 这是取消测试。请用Python在当前工作区先写入 started.txt，然后sleep 90秒，最后才写入 exports/should-not-exist.txt。不要做其他任务。',
 'cancel':'/agent cancel',
 'xlsx':'/agent [DAB-SCENARIO-XLSX] 请真实读取引用的XLSX所有非空单元格，输出 exports/cells.csv 和 exports/summary.txt 两个文件。CSV列为cell,value；summary说明单元格内容和数值之和。必须实际解析文件，不能猜测。',
 'new':'/agent new',
 'image':'/agent [DAB-SCENARIO-IMAGE] 请实际查看引用的图片，简短描述图中可见内容；另外用工具检查像素尺寸，回复准确宽高。不要只根据文件名猜测。'
}

def context():
 cfg=json.loads((ROOT/'local/agent-config.json').read_text())
 route=next(r for r,_ in route_configs(json.loads((ROOT/cfg['bridgeConfig']).read_text())) if r['accountId']==cfg['accountId'] and r['group']==cfg['conversationId'])
 scope=json.dumps([route['accountId'],route['profile'],route['group'],route.get('conversationType','group')])
 key=hashlib.sha256(scope.encode()).hexdigest()[:24]
 return ROOT/'local/agents'/key,key

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',choices=[*CASES,'inspect']);p.add_argument('--execute',action='store_true');a=p.parse_args()
 local,key=context();db=sqlite3.connect((local/'tasks.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 probe=Probe('20261111-agent-scenarios')
 if a.case=='inspect':
  summary=[]
  for name in CASES:
   path=probe.dir/(name+'.json')
   if not path.exists():continue
   data=unwrap(json.loads(path.read_text())['data']);mid=data['openMessageId']
   jid=hashlib.sha256((key+'\0'+mid).encode()).hexdigest()[:24]
   job=db.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
   summary.append({'case':name,'state':job['state'] if job else 'not_ingested','result':json.loads(job['result'])['response'] if job and job['result'] else None,
    'delivery':dict(db.execute('SELECT state,count(*) FROM outbox WHERE job_id=? GROUP BY state',(jid,)))})
  print(json.dumps(summary,ensure_ascii=False,indent=2));return
 if not a.execute:print(CASES[a.case]);return
 args=['chat','+messages-send','--group',probe.config['group'],'--text',CASES[a.case]]
 if a.case in {'xlsx','image'}:
  core=sqlite3.connect((ROOT/'local/runtime/bridge.sqlite3').as_uri()+'?mode=ro',uri=True)
  suffix='dab-office-001.xlsx' if a.case=='xlsx' else 'dab-image-001.png'
  matches=[json.loads(r[0]) for r in core.execute('SELECT body FROM events') if json.loads(r[0]).get('content','').startswith('[文件] '+suffix+' fileId:')]
  assert len(matches)==1
  args=['chat','+messages-reply','--group',probe.config['group'],'--ref-msg-id',matches[0]['message_id'],'--content',CASES[a.case]]
 args+=['--idempotency-key','DAB-SCENARIO-20261111-'+a.case,'--wait-delivery','--yes']
 probe.call(a.case,args);print(a.case+': submitted; private receipt preserved')

if __name__=='__main__':main()
