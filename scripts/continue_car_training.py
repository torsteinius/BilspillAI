"""Continue a completed hybrid run from its last checkpoint, preserving settings."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--target',type=int,required=True)
    parser.add_argument('--report',required=True)
    args=parser.parse_args()
    source=args.source.resolve();out=args.output.resolve()
    settings=json.loads((source/'settings.json').read_text())
    end=settings['generation_offset']+settings['generations']
    if args.target<=end or out.exists():parser.error('Target must extend the run; output must be new')
    parent_pid=json.loads((source/'process.json').read_text())['pid']
    control=source/'continuation.json'
    def status(state,**extra):
        data=dict(status=state,supervisor_pid=os.getpid(),source_pid=parent_pid,after_generation=end,target_generation=args.target,output=str(out),**extra)
        temp=control.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2));temp.replace(control)
    status('waiting_for_completion')
    while not (source/'complete.json').exists():
        try:os.kill(parent_pid,0)
        except ProcessLookupError:
            if (source/'complete.json').exists():break
            status('source_exited_before_completion');return
        time.sleep(5)
    complete=json.loads((source/'complete.json').read_text())
    if complete['last_generation']!=end:
        status('unexpected_completion',observed=complete);return
    checkpoint=source/f'generation-{end}.json'
    cmd=[sys.executable,'-u','-m','games.car.hybrid','--initial-model',str(checkpoint),
         '--traffic-model',str(source/'traffic-reference.json'),'--output',str(out),
         '--generations',str(args.target-end),'--generation-offset',str(end),
         '--learners',str(settings['learners']),'--rounds',str(settings['rounds']),'--test-rounds',str(settings['test_rounds']),
         '--steps',str(settings['steps']),'--seed',str(settings['seed']),
         '--history-stride',str(settings['history_stride']),'--collision-credit',settings['credit']]
    if settings.get('overtake_credit'):cmd += ['--overtake-credit',settings['overtake_credit']]
    if settings.get('overtake_reward'):cmd += ['--overtake-reward',str(settings['overtake_reward'])]
    if settings.get('wall_credit'):cmd += ['--wall-credit',settings['wall_credit']]
    if settings.get('random_scenarios'):cmd.append('--random-scenarios')
    else:cmd.extend(['--cone-count',str(settings['cone_count'])])
    if settings['rotating_networks']:cmd.append('--rotate')
    if settings['trained_candidates_only']:cmd.append('--trained-only')
    with out.with_suffix('.stdout.log').open('a') as log:
        child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(100):
        if child.poll() is not None:
            status('continuation_failed',exit_code=child.returncode);return
        if (out/'metrics.jsonl').exists():break
        time.sleep(.1)
    else:
        child.terminate();status('initialization_timeout');return
    assert json.loads((out/'initial.json').read_text())['weights']==json.loads(checkpoint.read_text())['weights']
    (out/'process.json').write_text(json.dumps(dict(pid=child.pid,command=cmd,source_generation=end,target_generation=args.target,weights_preserved=True,transient_state_reset=True),indent=2))
    report=[sys.executable,'-u','scripts/log_car_generation_progress.py','--run',str(out),'--output',args.report,'--watch','--training-pid',str(child.pid)]
    with (out/'reporter.log').open('a') as log:r=subprocess.Popen(report,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (out/'reporter-process.json').write_text(json.dumps(dict(pid=r.pid,command=report),indent=2))
    status('continuation_started',training_pid=child.pid)

if __name__=='__main__':main()
