"""Original, reproducible illustrated sunset-lake reference for artwork acceptance.
This is a visual complexity benchmark, not a ready-made painting to import as output.
No Krita sessions or tests are run by this generator.
"""
from PIL import Image, ImageDraw, ImageFilter
import random, math, sys
from pathlib import Path

W,H=1600,900
rnd=random.Random(20261107)
im=Image.new("RGB",(W,H))
pix=im.load()
stops=[(0,(100,82,142)),(160,(149,118,177)),(290,(233,131,153)),
       (390,(255,161,104)),(505,(249,195,134)),(540,(149,143,150))]
def interp(y,points):
    if y<=points[0][0]:return points[0][1]
    for (a,c),(b,d) in zip(points,points[1:]):
        if y<=b:
            t=(y-a)/(b-a)
            return tuple(int(c[k]*(1-t)+d[k]*t) for k in range(3))
    return points[-1][1]
for y in range(H):
    if y<550:base=interp(y,stops)
    else:base=interp(y,[(550,(91,119,146)),(680,(79,112,139)),(900,(58,89,115))])
    for x in range(W):
        noise=rnd.randrange(-3,4)
        pix[x,y]=tuple(max(0,min(255,v+noise)) for v in base)
d=ImageDraw.Draw(im,"RGBA")
# Sun and halo
halo=Image.new("RGBA",(W,H));h=ImageDraw.Draw(halo)
for r in range(230,48,-12):
    alpha=int(22*(1-r/260))
    h.ellipse((487-r,344-r,487+r,344+r),fill=(255,202,91,alpha))
halo=halo.filter(ImageFilter.GaussianBlur(36))
im=Image.alpha_composite(im.convert("RGBA"),halo)
d=ImageDraw.Draw(im,"RGBA")
d.ellipse((438,296,536,394),fill=(255,226,139,255))
d.ellipse((453,303,524,375),fill=(255,243,182,180))
# Clouds translucent sculpted ribbons
for k in range(115):
    cx=rnd.randrange(-130,1750);cy=rnd.randrange(55,410)
    size=rnd.randrange(25,125)
    tone=(252,157+rnd.randrange(0,45),139+rnd.randrange(0,50),rnd.randrange(30,115))
    d.ellipse((cx-size,cy-size*.24,cx+size*1.5,cy+size*.20),fill=tone)
    if k%3==0:d.ellipse((cx-size*.4,cy-size*.45,cx+size*.7,cy+size*.1),fill=(255,194,161,65))
# Mountains distant (light atmospheric silhouettes)
d.polygon([(0,501),(65,445),(132,483),(243,401),(327,449),(412,397),
 (520,484),(630,404),(733,458),(828,386),(920,452),(1042,400),
 (1160,470),(1283,412),(1398,472),(1540,400),(1600,447),(1600,590),(0,590)],
 fill=(130,115,154,255))
d.polygon([(0,528),(200,472),(314,495),(452,426),(552,488),(695,425),
(793,477),(929,388),(1028,470),(1152,368),(1235,405),(1350,305),
(1438,358),(1570,318),(1600,369),(1600,585),(0,585)],fill=(108,101,145,255))
# large snowy mountain and ridges
peaks=[(612,515),(796,389),(925,457),(1100,301),(1168,355),
(1235,238),(1301,294),(1363,249),(1440,317),(1548,294),(1600,343),
(1600,580),(550,580)]
d.polygon(peaks,fill=(90,95,126,255))
d.polygon([(796,389),(873,446),(829,425),(845,466),(775,449)],
 fill=(220,208,211,220))
d.polygon([(1100,301),(1148,360),(1113,344),(1080,399),(1050,357),(1010,416)],
 fill=(231,218,209,255))
d.polygon([(1235,238),(1320,361),(1271,310),(1260,340),(1213,304),
(1160,395),(1184,313)],fill=(246,235,233,255))
d.polygon([(1363,249),(1448,377),(1381,322),(1350,358),(1329,298)],
 fill=(242,231,230,255))
d.polygon([(1548,294),(1600,357),(1534,340),(1516,388),(1495,330)],
 fill=(228,220,224,225))
for i in range(140):
    x=rnd.randrange(650,1600);y=rnd.randrange(355,555)
    d.line((x,y,x+rnd.randrange(7,70),y-rnd.randrange(3,20)),
           fill=(181,163,177,rnd.randrange(15,72)),width=rnd.randrange(1,4))
# darker foothills
d.polygon([(0,505),(190,487),(320,510),(470,456),(630,516),(785,480),
(935,528),(1140,484),(1305,530),(1460,463),(1600,495),
(1600,632),(0,632)],fill=(63,79,101,255))
d.polygon([(0,548),(205,511),(370,550),(536,501),(702,556),
(878,513),(1010,563),(1260,499),(1465,526),(1600,512),
(1600,622),(0,622)],fill=(49,76,86,255))
# Forest along distant shoreline
for i in range(450):
    x=rnd.randrange(W);base_y=rnd.randrange(535,618)
    ht=rnd.randrange(12,76)
    green=rnd.choice([(27,68,65,235),(30,73,60,245),(43,79,63,250),
                      (40,71,71,246),(29,61,68,244)])
    d.polygon([(x,base_y-ht),(x-ht*.28,base_y),(x+ht*.28,base_y)],fill=green)
    if rnd.randrange(3)==0:
        d.line((x,base_y-ht,x,base_y+2),fill=(20,53,49,180),width=2)
# Shoreline and lake
d.polygon([(0,603),(200,592),(420,609),(600,598),(825,608),(1050,598),
 (1370,602),(1600,598),(1600,626),(0,626)],fill=(29,70,72,255))
# Water gradients and ripple
d.rectangle((0,625,W,H),fill=(45,91,123,40))
for i in range(1200):
    x=rnd.randrange(W);y=rnd.randrange(616,H)
    width=rnd.randrange(4,86)
    if abs(x-487)<300:
        t=(y-610)/(H-610)
        alpha=int((110+65*(1-t))*max(.12,1-abs(x-487)/(480*t+115)))
        color=(255,rnd.randrange(145,204),rnd.randrange(100,161),alpha)
    else:color=(159,171,187,rnd.randrange(8,45))
    d.line((x,y,x+width,y+rnd.randrange(-1,2)),fill=color,width=rnd.randrange(1,3))
for i in range(160):
    y=rnd.randrange(627,H)
    x=int(487+rnd.gauss(0,36+(y-627)*.32))
    w=rnd.randrange(15,160)
    d.line((x-w//2,y,x+w//2,y),fill=(255,190,112,rnd.randrange(40,180)),width=rnd.randrange(1,4))
# Right bank rocks and shrub shapes
d.polygon([(1260,605),(1350,570),(1470,559),(1600,562),(1600,676),(1450,643)],
fill=(92,108,96,255))
for i in range(60):
    x=rnd.randrange(1280,1660);y=rnd.randrange(545,642)
    r=rnd.randrange(3,24)
    d.ellipse((x-r,y-r*.6,x+r,y+r*.8),fill=(88+rnd.randrange(0,50),95+rnd.randrange(0,45),94+rnd.randrange(0,45),195))
# Large left foreground silhouette foliage and tree
d.polygon([(0,0),(48,0),(102,170),(87,450),(50,620),(0,680)],fill=(38,49,39,255))
for k in range(90):
    y=rnd.randrange(0,560);x=rnd.randrange(-80,370)
    if x>y*.55+90:continue
    r=rnd.randrange(12,56)
    c=rnd.choice([(21,50,39,245),(32,58,41,245),(43,68,42,245),(65,75,42,245)])
    d.ellipse((x-r,y-r//2,x+r,y+r//2),fill=c)
# Near shore
d.polygon([(0,730),(130,702),(230,748),(350,729),(500,783),
(640,814),(810,869),(930,900),(0,900)],fill=(70,90,57,255))
for i in range(165):
    x=rnd.randrange(0,780);y=rnd.randrange(700,915)
    if x>6*(y-690)+70:continue
    size=rnd.randrange(12,70)
    d.line((x,y,x+rnd.randrange(-12,13),y-size),fill=(112+rnd.randrange(0,75),119+rnd.randrange(0,80),49+rnd.randrange(0,40),rnd.randrange(140,240)),width=rnd.randrange(1,4))
# foreground boulders
for cx,cy,rx,ry in [(160,777,85,53),(405,829,124,61),(655,854,83,47),(915,892,95,43)]:
    d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=(83,84,87,255))
    d.polygon([(cx-rx*.82,cy-ry*.35),(cx-rx*.23,cy-ry*.87),
               (cx+rx*.36,cy-ry*.7),(cx+rx*.65,cy-ry*.1),(cx,cy+ry*.05)],
              fill=(147,141,133,200))
    for j in range(12):
        x=cx+rnd.randrange(-int(rx),int(rx));y=cy+rnd.randrange(-int(ry//2),int(ry//2))
        d.line((x,y,x+rnd.randrange(4,17),y+rnd.randrange(2,11)),fill=(47,56,60,80),width=2)
# wildflowers
for i in range(145):
    x=rnd.randrange(0,850);y=rnd.randrange(760,925)
    if x>4*(y-725)+170:continue
    fy=y-rnd.randrange(9,35)
    d.line((x,y,x+rnd.randrange(-7,8),fy),fill=(74,106,50,240),width=2)
    pet=rnd.choice([(214,144,217),(240,229,188),(153,152,213),(232,175,157)])
    for j in range(4):
        a=j*math.pi/2
        dx=math.cos(a)*4;dy=math.sin(a)*4
        d.ellipse((x+dx-3,fy+dy-3,x+dx+3,fy+dy+3),fill=(*pet,238))
    d.ellipse((x-2,fy-2,x+2,fy+2),fill=(249,215,104,255))
# Painterly soft finish
im=im.convert("RGB")
output=Path(sys.argv[1]) if len(sys.argv)>1 else Path("sunset_alpine_lake.jpg")
output.parent.mkdir(parents=True,exist_ok=True)
im.save(output,quality=88,optimize=True,subsampling=0)
print(str(output),output.stat().st_size,im.size)