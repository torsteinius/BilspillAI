"""Persistent, direction-specific practice starts discovered from real wall crashes."""
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import uuid
from weakref import WeakKeyDictionary


class PoseTrail:
    def __init__(self,distance):
        if distance<=0:raise ValueError('History distance must be positive')
        self.distance=distance;self.points=deque();self.travel=0.

    def append(self,car):
        pose={key:car[key] for key in ('x','y','z','heading','speed','speed_factor') if key in car}
        pose.setdefault('z',0.);pose.setdefault('speed_factor',1.)
        pose.setdefault('speed',3*pose['speed_factor'])
        if self.points:
            previous=self.points[-1][1]
            self.travel+=math.dist(tuple(previous[key] for key in ('x','y','z')),tuple(pose[key] for key in ('x','y','z')))
        self.points.append((self.travel,pose))
        target=self.travel-self.distance
        while len(self.points)>2 and self.points[1][0]<=target:self.points.popleft()

    def before_crash(self):
        target=self.travel-self.distance
        if target<0 or len(self.points)<2:return None
        a,old=self.points[0];b,new=self.points[1]
        if not a<=target<=b:return None
        t=(target-a)/(b-a) if b>a else 0.
        pose={key:old[key]+t*(new[key]-old[key]) for key in old}
        difference=math.atan2(math.sin(new['heading']-old['heading']),math.cos(new['heading']-old['heading']))
        pose['heading']=old['heading']+t*difference
        pose['speed_ratio']=pose.pop('speed')/(3*pose.pop('speed_factor'))
        return pose


class CrashSpawnBank:
    def __init__(self,path,limit=20):
        if limit<1:raise ValueError('Practice limit must be positive')
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limit=limit;self.geometries={};self.track_hashes=WeakKeyDictionary()
        self.db=sqlite3.connect(self.path,timeout=30)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS points (
              id INTEGER PRIMARY KEY, track TEXT NOT NULL, geometry TEXT NOT NULL,
              direction INTEGER NOT NULL CHECK(direction IN (-1,1)),
              x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL, along REAL NOT NULL,
              pose TEXT NOT NULL, wall TEXT NOT NULL, tests INTEGER NOT NULL DEFAULT 0,
              observations INTEGER NOT NULL DEFAULT 1, generation INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS location ON points(track,geometry,direction,x,y,z);
            CREATE TABLE IF NOT EXISTS reservations (
              token TEXT PRIMARY KEY, point_id INTEGER NOT NULL REFERENCES points(id));
            CREATE INDEX IF NOT EXISTS pending ON reservations(point_id);
        ''')

    def register_track(self,track):
        identity=hashlib.sha256(json.dumps(dict(points=track.points,width=track.half_width),separators=(',',':')).encode()).hexdigest()
        self.geometries[track.name]=identity;self.track_hashes[track]=identity
        return identity

    def geometry(self,track):
        identity=self.track_hashes.get(track) or self.register_track(track)
        self.geometries[track.name]=identity
        return identity

    def recover_pending(self):
        """Release unfinished drives only after the previous trainer has stopped."""
        with self.db:self.db.execute('DELETE FROM reservations')

    def add_crash(self,track,direction,pose,car,generation,car_length=14.):
        if pose is None:return None
        if track.clearance(pose['x'],pose['y'],pose['z'])<car_length/2+2:return None
        _,along,road_z,segment=track.locate(car['x'],car['y'],car.get('z',0.))
        t=(along-segment[5])/segment[8]
        center=(segment[0]+t*segment[2],segment[1]+t*segment[3])
        length=math.sqrt(segment[4]);nx,ny=-segment[3]/length,segment[2]/length
        side=1 if (car['x']-center[0])*nx+(car['y']-center[1])*ny>=0 else -1
        wall=dict(x=center[0]+side*track.half_width*nx,y=center[1]+side*track.half_width*ny,z=road_z)
        geometry=self.geometry(track);radius=2*car_length
        with self.db:
            candidates=self.db.execute('''SELECT id,x,y,z,along FROM points
                WHERE track=? AND geometry=? AND direction=?
                AND abs(x-?)<=? AND abs(y-?)<=? AND abs(z-?)<=?''',
                (track.name,geometry,direction,wall['x'],radius,wall['y'],radius,wall['z'],radius)).fetchall()
            for existing in candidates:
                delta=abs(existing['along']-along)
                if min(delta,track.perimeter-delta)<=radius and math.dist(
                    (existing['x'],existing['y'],existing['z']),tuple(wall.values()))<=radius:
                    self.db.execute('UPDATE points SET observations=observations+1 WHERE id=?',(existing['id'],))
                    return existing['id']
            cursor=self.db.execute('''INSERT INTO points
                (track,geometry,direction,x,y,z,along,pose,wall,generation) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (track.name,geometry,direction,wall['x'],wall['y'],wall['z'],along,
                 json.dumps(pose,allow_nan=False),json.dumps(wall),generation))
            return cursor.lastrowid

    def reserve(self,track,direction,rng,can_place):
        """Count unfinished reservations too, so parallel cars cannot exceed 20 tests."""
        geometry=self.geometry(track)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            rows=self.db.execute('''SELECT p.*,count(r.token) AS pending FROM points p
                LEFT JOIN reservations r ON r.point_id=p.id
                WHERE p.track=? AND p.geometry=? AND p.direction=? AND p.tests<?
                GROUP BY p.id HAVING p.tests+count(r.token)<? ORDER BY p.id''',
                (track.name,geometry,direction,self.limit,self.limit)).fetchall()
            rng.shuffle(rows)
            for row in rows:
                pose=json.loads(row['pose'])
                if not can_place(pose):continue
                token=uuid.uuid4().hex
                self.db.execute('INSERT INTO reservations VALUES (?,?)',(token,row['id']))
                self.db.commit()
                return dict(id=row['id'],token=token,pose=pose)
            self.db.commit();return None
        except BaseException:
            self.db.rollback();raise

    def complete(self,token):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT point_id FROM reservations WHERE token=?',(token,)).fetchone()
            if row is None:
                self.db.commit();return None
            self.db.execute('DELETE FROM reservations WHERE token=?',(token,))
            self.db.execute('UPDATE points SET tests=tests+1 WHERE id=? AND tests<?',(row['point_id'],self.limit))
            count=self.db.execute('SELECT tests FROM points WHERE id=?',(row['point_id'],)).fetchone()[0]
            self.db.commit();return dict(id=row['point_id'],tests=count,limit=self.limit)
        except BaseException:
            self.db.rollback();raise

    def markers(self,name):
        geometry=self.geometries.get(name)
        if geometry is None:return []
        rows=self.db.execute('''SELECT p.*,count(r.token) AS pending FROM points p
            LEFT JOIN reservations r ON r.point_id=p.id WHERE p.track=? AND p.geometry=?
            GROUP BY p.id ORDER BY (p.tests<?) DESC,p.id DESC LIMIT 128''',(name,geometry,self.limit)).fetchall()
        return [dict(id=row['id'],direction=row['direction'],spawn=json.loads(row['pose']),
                     wall=json.loads(row['wall']),tests=row['tests'],pending=row['pending'],
                     limit=self.limit,observations=row['observations']) for row in rows]

    def summary(self):
        result={}
        for name,geometry in self.geometries.items():
            row=self.db.execute('''SELECT count(*) AS points,sum(tests) AS tests,
                sum(CASE WHEN tests<? THEN 1 ELSE 0 END) AS active FROM points
                WHERE track=? AND geometry=?''',(self.limit,name,geometry)).fetchone()
            result[name]={key:row[key] or 0 for key in row.keys()}
        return result

    def export(self,path):
        data=dict(limit=self.limit,marker_limit=128,summary=self.summary(),points={name:self.markers(name) for name in self.geometries})
        path=Path(path);temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data,indent=2)+'\n');temporary.replace(path)
