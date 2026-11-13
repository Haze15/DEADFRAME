import subprocess, time, base64
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7831'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
JS = r"""(lab)=>{const S=540,cv=document.createElement('canvas');cv.width=S;cv.height=S+60;const g=cv.getContext('2d'),k=S/90,X=x=>(x+45)*k,Z=z=>(z+45)*k;
 g.fillStyle='#0b0c0b';g.fillRect(0,0,S,S+60);let a=0,t=0;
 for(const c of DF.__CH()){const inb=DF.__inBox(c.mn,c.mx);const big=(c.mx[0]-c.mn[0])>60;if(big&&c.mn[1]<0)continue;
  g.fillStyle=inb?'rgba(120,170,100,.55)':'rgba(120,120,120,.18)';g.strokeStyle=inb?'#9fd18a':'#555';g.lineWidth=1;
  g.fillRect(X(c.mn[0]),Z(c.mn[2]),(c.mx[0]-c.mn[0])*k,(c.mx[2]-c.mn[2])*k);g.strokeRect(X(c.mn[0])+.5,Z(c.mn[2])+.5,(c.mx[0]-c.mn[0])*k,(c.mx[2]-c.mn[2])*k);t+=c.count;if(inb)a+=c.count}
 const p=DF.me.pos,y=DF.camS.yaw,h=DF.camS.fov*(DF.__asp())/2*1.0,L=70;g.strokeStyle='#e9e6df';g.lineWidth=2.5;
 const hf=Math.atan(Math.tan(DF.camS.fov/2)*DF.__asp());
 for(const s of[-1,1]){const yy=y+s*hf;g.beginPath();g.moveTo(X(p[0]),Z(p[2]));g.lineTo(X(p[0]-Math.sin(yy)*L),Z(p[2]-Math.cos(yy)*L));g.stroke()}
 g.fillStyle='#e5291f';g.beginPath();g.arc(X(p[0]),Z(p[2]),6,0,7);g.fill();
 g.fillStyle='#e9e6df';g.font='14px monospace';g.fillText(lab+' — dessiné : '+Math.round(a/t*100)+' % de la carte',10,S+26);
 g.fillStyle='#9fd18a';g.fillText('■ secteur dessiné',10,S+48);g.fillStyle='#888';g.fillText('■ secteur ignoré (hors champ)',180,S+48);return cv.toDataURL('image/png')}"""
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 640, 'height': 360})
        pg.goto('http://localhost:7831/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
        pg.evaluate("()=>{DF.CFG.bots=0}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=120000)
        for i,(pos,yaw,lab) in enumerate([([-4,0,4],.9,'Dépôt, regard nord-ouest'),([10,0,-6],-2.4,'Dépôt, regard sud-est')]):
            pg.evaluate(f"()=>{{DF.me.pos={pos};DF.me.vel=[0,0,0];DF.setLook({yaw},0)}}"); pg.wait_for_timeout(1500)
            url=pg.evaluate(JS,lab); open(f'/tmp/cm{i}.png','wb').write(base64.b64decode(url.split(',')[1]))
        b.close()
finally:
    srv.kill()
