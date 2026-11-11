#!/usr/bin/env python3
"""Authorized solo acceptance: 2 office attachments, 2 inline images, file quote,
calendar event in the past (free/no invitees), and an unsent mail draft.
Requires existing verified local config and fixtures. No other members involved.
"""
import argparse
import hashlib
import json
from pathlib import Path
from probe_support import ROOT, Probe, unwrap


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--execute',action='store_true')
    a.add_argument('--run-id',default='20261111-gaps')
    opt=a.parse_args()
    if not opt.execute:a.error('--execute is required for synthetic test writes')
    p=Probe(opt.run_id);g=p.config['group'];summary={}
    def put(key,value):
        summary[key]=value
        (p.dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
        print(key,json.dumps(value,ensure_ascii=False),flush=True)
    def send(label,params):
        d=unwrap(p.call(label,['chat','+messages-send','--as','user','--group',g,*params,
                              '--idempotency-key','DAB-'+opt.run_id+'-'+label,'--yes']))
        task=d.get('sendReceipt',{}).get('openTaskId') or d.get('result',{}).get('openTaskId')
        if not task:raise RuntimeError('Missing task; reconcile instead of resend')
        s=unwrap(p.call(label+'-status',['chat','+messages-query-send-status','--open-task-id',task]))
        assert s['result']['sendStatus']=='SUCCESS' and s['messageRef']['openConversationId']==g
        return s['messageRef']['openMessageId']
    def download(label,mid):
        return unwrap(p.call(label,['chat','+messages-mget','--msg-ids',mid,'--download-resources',
                                   '--output-dir',str((p.dir/(label+'-files')).relative_to(ROOT))]))
    file_id=None
    for ext in ['docx','xlsx']:
        fixture='fixtures/dab-office-001.'+ext
        mid=send(ext,['--msg-type','file','--file',fixture]);file_id=mid
        d=download(ext+'-download',mid);ds=d['resourceDownloads']['downloads']
        same=len(ds)==1 and (ROOT/ds[0]['localPath']).read_bytes()==(ROOT/fixture).read_bytes()
        assert same
        put(ext,{'delivered':True,'downloaded':1,'sha256Matches':same,'bytes':(ROOT/fixture).stat().st_size})
    md='[DAB-MULTI-001] Two inline images\n\n![A](./fixtures/dab-image-001.png)\n\n![B](./fixtures/dab-image-002.png)'
    mid=send('multi-image',['--markdown',md]);d=download('multi-image-download',mid)
    downloads=d['resourceDownloads']['downloads'];actual={hashlib.sha256((ROOT/x['localPath']).read_bytes()).hexdigest() for x in downloads}
    expected={hashlib.sha256((ROOT/('fixtures/dab-image-00'+n+'.png')).read_bytes()).hexdigest() for n in ['1','2']}
    assert expected==actual
    put('multiImage',{'downloaded':len(downloads),'bothHashesMatch':True,'resourceTypes':[r['type'] for m in d['messages'] for r in m.get('resourceRefs',[])]})
    q=p.call('file-quote',['chat','+messages-reply','--group',g,'--ref-msg-id',file_id,
        '--content','[DAB-FILE-QUOTE-001] 引用本轮 XLSX 测试附件。','--idempotency-key','DAB-'+opt.run_id+'-quote','--wait-delivery','--yes'])
    put('fileQuote',{'deliveryStatus':q.get('deliveryStatus')})
    # Explicitly past, free, no additional attendees/rooms; no one is invited.
    d=unwrap(p.call('calendar-create',['calendar','+create','--title','DAB-SOLO-20261111 日历接口验收',
        '--start','2026-11-11T00:00:00+08:00','--end','2026-11-11T00:05:00+08:00',
        '--timezone','Asia/Shanghai','--free-busy','free','--desc','仅本人接口测试；过去时段、不占忙闲、无受邀人。','--yes']))
    (p.dir/'calendar-normalized.json').write_text(json.dumps(d,ensure_ascii=False))
    event=unwrap(p.call('calendar-get',['calendar','+get','--event',d['eventId']]))['event']
    assert event['summary']=='DAB-SOLO-20261111 日历接口验收'
    assert event['freeBusy']=='FREE' and all(x.get('self') for x in event['attendees'])
    assert event['start']['dateTime']=='2026-11-11T00:00:00+08:00'
    put('calendarCreate',{'createdAndReadBack':True,'freeBusy':'FREE','otherAttendees':0,
        'pastEvent':True,'onlineMeetingInfoReturned':bool(event.get('onlineMeetingInfo')),
        'defaultReminderReturned':bool(event.get('reminders')),'meetingJoined':False})
    boxes=unwrap(p.call('mailboxes',['mail','mailbox','list']))['emailAccounts']
    if len(boxes)!=1:raise RuntimeError('Ambiguous mailbox; do not choose first')
    draft=unwrap(p.call('mail-draft',['mail','draft','create','--from',boxes[0]['email'],
        '--subject','DAB-SOLO-20261111 未发送测试草稿','--content','DAB-MAIL-DRAFT-001 本人接口验收，不发送。']))
    (p.dir/'draft-normalized.json').write_text(json.dumps(draft,ensure_ascii=False))
    mid=draft['result']['message']['id']
    message=unwrap(p.call('mail-read',['mail','+message','--email',boxes[0]['email'],'--id',mid]))['value']
    assert message['id']==mid and 'DAB-MAIL-DRAFT-001' in message['markdownBody']
    assert not message['toRecipients'] and not message['ccRecipients']
    put('mailDraftCreate',{'createdAndReadBack':True,'sent':False,'recipients':0,'bodyMarkerMatches':True})

if __name__=='__main__':main()
