#!/usr/bin/env python3
"""Run deterministic regression and record each test result; never invokes real DingTalk or models."""
import argparse,io,json,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
class Result(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.records=[]
    def addSuccess(self,test):super().addSuccess(test);self.records.append({'test':test.id(),'result':'passed'})
    def addError(self,test,err):super().addError(test,err);self.records.append({'test':test.id(),'result':'error'})
    def addFailure(self,test,err):super().addFailure(test,err);self.records.append({'test':test.id(),'result':'failed'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.records.append({'test':test.id(),'result':'skipped','reason':reason})
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-evidence',action='store_true');a=p.parse_args()
    stream=io.StringIO();start=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    report={'date':'2026-11-11','ok':result.wasSuccessful(),'tests':result.testsRun,'seconds':round(time.monotonic()-start,3),
        'scope':'local unit/integration and real subprocesses with synthetic provider events; no remote business calls',
        'results':result.records}
    if a.write_evidence:(ROOT/'evidence/2026-11-11/scenario-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False))
    if not result.wasSuccessful():print(stream.getvalue())
    raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
