"""Emit SYNTHETIC bridge argv for official declaration-tree parsing, never run DWS."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from check_dws_recovery_once import conversation_info_arguments
from dingtalk_bridge.official_proxy import pinned_arguments,OFFICE_COMMANDS
profile='synthetic-corp:synthetic-user'
cases=[{'name':'query-group','args':conversation_info_arguments({'group':'synthetic-conversation','profile':profile})},
       {'name':'query-direct','args':conversation_info_arguments({'conversationType':'direct','peerOpenDingTalkId':'synthetic-peer','profile':profile})}]
cases.extend({'name':family,'args':pinned_arguments([family,'--help'],profile)} for family in OFFICE_COMMANDS)
print(json.dumps(cases,indent=2))
