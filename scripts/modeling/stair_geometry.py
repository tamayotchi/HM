"""Open timber switchback stairs on central steel spines, from the user's photo."""
import bpy
from mathutils import Vector

def build_stairs(scene, point, prefix, bounds, timber, steel, rise=2.8, descending=False):
    x0,x1,y0,y1=bounds;mid=(x0+x1)/2;gap=.065;width=(x1-x0-gap)/2
    left=x0+width/2;right=x1-width/2;turn=(x1-x0)*.37;run=(y1-y0-turn)/7;yt=y0+7*run;step=rise/17
    made=[]
    def mesh(name,verts,faces,material,bevel=.005):
        m=bpy.data.meshes.new(prefix+' '+name);m.from_pydata([point(v) for v in verts],[],faces);m.update()
        o=bpy.data.objects.new(prefix+' · '+name,m);scene.collection.objects.link(o);o.data.materials.append(material)
        if bevel:
            b=o.modifiers.new('Rounded edges','BEVEL');b.width=bevel;b.segments=2
            o.modifiers.new('Face normals','WEIGHTED_NORMAL')
        o['stair_part']=True;made.append(o);return o
    def slab(name,poly,z,depth,material):
        n=len(poly);verts=[(*p,z-depth) for p in poly]+[(*p,z) for p in poly]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        return mesh(name,verts,faces,material)
    def box(name,center,size,material):
        x,y,z=center;a,b,c=[v/2 for v in size]
        return slab(name,[(x-a,y-b),(x+a,y-b),(x+a,y+b),(x-a,y+b)],z+c,2*c,material)
    def beam(name,a,b,thickness=.15,depth=.19):
        a=point(a);b=point(b);delta=b-a;centre=(a+b)/2
        verts=[(-thickness/2,-depth/2,-delta.length/2),(thickness/2,-depth/2,-delta.length/2),(thickness/2,depth/2,-delta.length/2),(-thickness/2,depth/2,-delta.length/2),(-thickness/2,-depth/2,delta.length/2),(thickness/2,-depth/2,delta.length/2),(thickness/2,depth/2,delta.length/2),(-thickness/2,depth/2,delta.length/2)]
        m=bpy.data.meshes.new(name);m.from_pydata(verts,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);m.update()
        o=bpy.data.objects.new(prefix+' · '+name,m);scene.collection.objects.link(o);o.location=centre;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();o.data.materials.append(steel);o['stair_part']=True;made.append(o)
        b=o.modifiers.new('Steel edge','BEVEL');b.width=.006;b.segments=2
    for side,x in [('Lower right',right),('Upper left',left)]:
        for i in range(7):
            y=y0+(i+.5)*run if side.startswith('Lower') else yt-(i+.5)*run
            h=step*(i+1) if side.startswith('Lower') else step*(11+i)
            box(side+' wood tread',(x,y,h-.0275),(width,run+.012,.055),timber)
            box(side+' support plate',(x,y,h-.07),(width*.55,.16,.025),steel)
            box(side+' support saddle',(x,y,h-.157),(.15,.12,.18),steel)
        first=(x,y0+run*.5,step-.30) if side.startswith('Lower') else (x,yt-run*.5,11*step-.30)
        last=(x,yt-run*.5,7*step-.30) if side.startswith('Lower') else (x,y0+run*.5,rise-.30)
        beam(side+' central steel spine',first,last)
    polygons=[[(mid,yt),(x1,yt),(x1,y1)],[(mid,yt),(x1,y1),(x0,y1)],[(x0,yt),(mid,yt),(x0,y1)]]
    centres=[]
    for i,poly in enumerate(polygons):
        h=(8+i)*step;slab('Turning timber winder',poly,h,.055,timber)
        x=sum(p[0] for p in poly)/3;y=sum(p[1] for p in poly)/3;centres.append((x,y,h-.30))
        box('Winder steel bracket',(x,y,h-.078),(.4,.22,.045),steel)
        box('Winder support saddle',(x,y,h-.16),(.16,.14,.19),steel)
    spine=[(right,yt-run*.5,7*step-.30),*centres,(left,yt-run*.5,11*step-.30)]
    for a,b in zip(spine,spine[1:]):beam('Turning steel spine',a,b)
    if descending:
        # A complete lower-storey switchback, not a short flight ending on a
        # fake floor. Both flights and winders remain open below the landing.
        def below(xyz):return point((xyz[0],xyz[1],xyz[2]-rise))
        made.extend(build_stairs(scene,below,prefix+' · To floor below',bounds,
                                 timber,steel,rise=rise,descending=False))
    return made
