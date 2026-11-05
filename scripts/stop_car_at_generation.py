"""Stop an already running trainer after a fully saved generation."""
import argparse
import json
import os
from pathlib import Path
import signal
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--target',type=int,required=True)
    args=parser.parse_args()
    control=args.run/'stop-control.json'
    def status(state,**extra):
        control.write_text(json.dumps(dict(status=state,target_generation=args.target,training_pid=args.pid,watcher_pid=os.getpid(),**extra),indent=2))
    status('watching')
    with (args.run/'metrics.jsonl').open() as stream:
        while True:
            position=stream.tell();line=stream.readline()
            if not line.endswith('\n'):
                stream.seek(position)
                try:os.kill(args.pid,0)
                except ProcessLookupError:
                    status('trainer_exited_before_target');return
                time.sleep(.25);continue
            row=json.loads(line)
            if 'winner' not in row or row['generation']<args.target:continue
            if row['generation']>args.target:
                status('target_already_exceeded',observed_generation=row['generation']);return
            checkpoint=args.run/f'generation-{args.target}.json'
            model=json.loads(checkpoint.read_text())
            assert model['generation']==args.target
            os.kill(args.pid,signal.SIGTERM)
            settings=json.loads((args.run/'settings.json').read_text())
            model['experiment']=settings
            # Preserve exactly the winner's weights; update only the declared budget.
            temp=args.run/'stopped-model.json';temp.write_text(json.dumps(model,indent=2));temp.replace(args.run/'model.json')
            (args.run/'complete.json').write_text(json.dumps(dict(generations=args.target-settings['generation_offset'],last_generation=args.target,elapsed_seconds=row['elapsed_seconds'],stop_reason='requested_generation_budget')))
            status('completed',last_generation=args.target)
            return

if __name__=='__main__':main()
