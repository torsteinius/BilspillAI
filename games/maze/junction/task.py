"""Ground truth is used for rewards and evaluation, never detector observations."""
from ..memory import MemoryEpisode
from ..world import DIRECTIONS


def landmark_kind(maze,x,y):
    if maze.cell(x,y) != '.':
        return 'utgang'
    directions=[(dx,dy) for dx,dy in DIRECTIONS if maze.cell(x+dx,y+dy) in '.E']
    if len(directions)>=3:return 'forgrening'
    if len(directions)==2:
        a,b=directions
        if (a[0]+b[0],a[1]+b[1]) != (0,0):return 'hjørne'
        return 'rett korridor'
    return 'blindvei'


def is_landmark(kind):
    return kind in ('forgrening','hjørne')


def stop_reward(stop,kind):
    return (1. if is_landmark(kind) else -1.) if stop else 0.


def walk(trainer,maze):
    """Exact legacy movement; the detector cannot modify its actions or state."""
    episode=MemoryEpisode(maze,trainer.config.rules)
    samples=[]
    while not episode.done:
        kind=landmark_kind(maze,episode.x,episode.y)
        sample=dict(x=episode.x,y=episode.y,heading=episode.heading,step=episode.steps,
                    rays=[min(v,10.)/10. for v in episode.sensors()],kind=kind)
        output=trainer.network.forward(episode.observations())
        episode.apply_outputs(output)
        sample['action']=episode.last_action
        samples.append(sample)
    return samples,episode
