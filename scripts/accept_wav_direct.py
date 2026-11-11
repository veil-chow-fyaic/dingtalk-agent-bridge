#!/usr/bin/env python3
"""Read-only audit of one liev->veil WAV file case; not the complete media matrix."""
import argparse
import json
import wave
from accept_office_files import ROOT, read, digest


def audit():
    folder=ROOT/'local/audio-video-ui-20261111'
    probe=read(ROOT/'local/probes/media-matrix-20261111/direct-wav.json')
    event=read(folder/'direct-wav-event.json')
    resources=read(folder/'direct-wav-resources.json').get('downloads',[])
    original=(ROOT/'fixtures/dab-audio-001.wav').read_bytes()
    client=folder/'direct-received.wav'
    with wave.open(str(client)) as sound:
        audio={'channels':sound.getnchannels(),'sampleRate':sound.getframerate(),
               'frames':sound.getnframes(),'durationSeconds':sound.getnframes()/sound.getframerate()}
    checks={'confirmed':probe['receipt']['state']=='confirmed',
            'exact_message':event['message_id']==probe['receipt']['message_id'],
            'exact_conversation':event['conversation_id']==probe['payload']['conversation_id'],
            'from_bound_self':event['from_self'] is True,
            'file_presentation':event['content'].startswith('[文件]'),
            'resource_original':len(resources)==1 and all((ROOT/r['localPath']).read_bytes()==original for r in resources),
            'client_original':client.read_bytes()==original,
            'one_second_mono':audio=={'channels':1,'sampleRate':16000,'frames':16000,'durationSeconds':1.0}}
    return {'date':'2026-11-11','case':'direct-wav-out','ok':all(checks.values()),'checks':checks,
            'bytes':len(original),'sha256':digest(original),'audio':audio,
            'ui':'File card downloaded through DingTalk UI; actual downloaded WAV opened in Finder Quick Look player, duration 0:01 and playback progress visible. No claim about acoustic output quality.',
            'nativeVoiceBubble':False,'matrixComplete':False,'completedCases':1,'requiredFileCases':8}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args();r=audit()
    if a.write_evidence:(ROOT/'evidence/2026-11-11/wav-direct-file-ledger.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['ok'] else 1)
