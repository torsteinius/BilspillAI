"""Deterministic, closed courses for varied road-following practice."""
import math

TRAINING_TRACKS=('training','figure_eight','rolling_hills','ridge_switchbacks',
                 'bridge_loops','triple_stack')
NEW_TRACKS=TRAINING_TRACKS[2:]


def smooth_course(anchors, spacing=3.):
    """Periodic Catmull-Rom in xy; bounded smooth ramps between deck heights."""
    result=[]
    for i,a in enumerate(anchors):
        previous=anchors[i-1];b=anchors[(i+1)%len(anchors)];following=anchors[(i+2)%len(anchors)]
        count=max(16,math.ceil(math.dist(a,b)/spacing))
        for step in range(count):
            t=step/count
            xy=[.5*((2*a[j])+(-previous[j]+b[j])*t
                    +(2*previous[j]-5*a[j]+4*b[j]-following[j])*t*t
                    +(-previous[j]+3*a[j]-3*b[j]+following[j])*t*t*t)
                for j in (0,1)]
            blend=t*t*t*(10+t*(-15+6*t))
            result.append((*xy,a[2]+(b[2]-a[2])*blend))
    return result


def crossing_course(levels, radius):
    """Diameters cross on distinct decks; outer arcs join them with ramps."""
    count=len(levels);anchors=[]
    angles=[i*math.pi/count for i in range(count)]
    for i,(angle,height) in enumerate(zip(angles,levels)):
        co,si=math.cos(angle),math.sin(angle)
        for distance in (-radius,-.8*radius,-300.,300.,.8*radius,radius):
            anchors.append((distance*co,distance*si,height))
        # First links go clockwise; last goes counter-clockwise around the outside.
        arc=-(math.pi-math.pi/count) if i<count-1 else math.pi/count
        steps=6 if count==3 else 5
        for step in range(1,steps):
            u=step/steps;theta=angle+arc*u
            z=height+(levels[(i+1)%count]-height)*u
            anchors.append((radius*math.cos(theta),radius*math.sin(theta),z))
    return smooth_course(anchors)


def course_points(name):
    if name=='rolling_hills':
        result=[]
        for i in range(2600):
            t=math.tau*i/2600
            r=1+.09*math.cos(4*t)+.035*math.sin(7*t)
            result.append((1400*r*math.cos(t),1000*r*math.sin(t),
                           47+35*math.sin(2*t)+12*math.sin(5*t)))
        return result
    if name=='ridge_switchbacks':
        return smooth_course([(-1200,-1200,50),(900,-1200,50),(1200,-900,50),
            (900,-600,50),(-900,-600,100),(-1200,-300,100),(-900,0,100),
            (900,0,20),(1200,300,20),(900,600,20),(-900,600,120),
            (-1500,900,120),(-2000,600,120),(-2000,-1500,50),(-1500,-1800,50)])
    if name=='bridge_loops':return crossing_course([0.,80.],1100.)
    if name=='triple_stack':return crossing_course([0.,80.,160.],1800.)
    raise ValueError(f'Unknown practice track: {name}')


# The user-defined curriculum; legacy courses remain loadable for old runs.
DEFINED_TRACKS=('bridge_straight','tight_turns','tight_turns_mirrored','normal_turns','figure_eight','training')
OPEN_TRACKS=('bridge_straight','tight_turns','tight_turns_mirrored','normal_turns')


def defined_course(name):
    if name=='tight_turns_mirrored':
        return [(x,-y,z) for x,y,z in defined_course('tight_turns')]
    if name=='normal_turns':
        # Three broad S-bends, with a full starting grid on each straight end.
        points=[]
        for i in range(1135):
            x=3.*i
            u=max(0.,min(2700.,x-350.))
            points.append((x,90*(1-math.cos(math.tau*u/900.)),0.))
        return points
    if name=='bridge_straight':
        # Same 40-unit deck and smooth ramp profile as the figure-eight bridge.
        points=[]
        for i in range(1201):
            x=3.*i
            # Three successive climbs/descents, all on a straight centreline.
            local=x%1200.
            u=max(0.,min(1.,(local-150.)/350.,(1050.-local)/350.))
            points.append((x,0.,40.*u**3*(10.-15.*u+6.*u*u)))
        return points
    if name=='tight_turns':
        from .track import Track
        source=Track.generate('figure_eight').points
        turns=[]
        for i,p in enumerate(source):
            a=source[i-1];b=source[(i+1)%len(source)]
            cross=(p[0]-a[0])*(b[1]-p[1])-(p[1]-a[1])*(b[0]-p[0])
            turns.append(cross/(math.dist(a[:2],p[:2])*math.dist(p[:2],b[:2])*math.dist(a[:2],b[:2])))
        peak=max(range(len(turns)),key=lambda i:abs(turns[i]))
        sign=1 if turns[peak]>0 else -1
        lo=hi=peak
        while turns[(lo-1)%len(turns)]*sign>0:lo-=1
        while turns[(hi+1)%len(turns)]*sign>0:hi+=1
        bend=[source[i%len(source)] for i in range(lo,hi+2)]
        start=bend[0];angle=math.atan2(bend[1][1]-start[1],bend[1][0]-start[0])
        local=[((p[0]-start[0])*math.cos(angle)+(p[1]-start[1])*math.sin(angle),
                -(p[0]-start[0])*math.sin(angle)+(p[1]-start[1])*math.cos(angle)) for p in bend]
        points=[(0.,0.,0.),(150.,0.,0.)];heading=0.
        for repeat in range(6):
            x,y,_=points[-1];flip=1 if repeat%2==0 else -1
            points.extend((x+a*math.cos(heading)-flip*b*math.sin(heading),
                           y+a*math.sin(heading)+flip*b*math.cos(heading),0.) for a,b in local[1:])
            a,b=points[-2:];heading=math.atan2(b[1]-a[1],b[0]-a[0])
            points.append((b[0]+100*math.cos(heading),b[1]+100*math.sin(heading),0.))
        return points
    raise ValueError(name)
