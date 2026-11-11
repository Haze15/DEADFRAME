import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7822'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
J=lambda x: json.dumps(x,ensure_ascii=False)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1120, 'height': 630}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7822/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=1;DF.CFG.scale=.6}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive&&DF.bots.length',timeout=60000); pg.wait_for_timeout(800)
        pg.evaluate("()=>{DF.me.pos=[8,0,8];DF.me.vel=[0,0,0]}"); pg.keyboard.press('KeyG'); pg.wait_for_function("()=>DF.me.drone&&DF.me.drone.state==='fly'",timeout=60000)
        pg.keyboard.press('KeyG'); pg.wait_for_timeout(200)
        # opérateur à l'abri dans l'entrepôt, drone en stationnaire au-dessus de la cour, bot qui regarde le drone
        pg.evaluate("""()=>{DF.me.pos=[-28,0,-16];DF.me.vel=[0,0,0];const d=DF.me.drone;d.pos=[6,4,6];d.vel=[0,0,0];d.state='hold';
          const b=DF.bots[0];b.alive=true;b.hp=1e9;b.pos=[6,0,16];b.tpos=b.pos;b.yaw=b.tyaw=0;b.path=[];b.tgt=null;b.last=null;b.look=0;b.think=0}""")
        t0=time.time();hist=[]
        while time.time()-t0<200:
            s=pg.evaluate("()=>{const d=DF.me.drone,b=DF.bots[0];return {st:d?d.state:'none',hp:d?Math.round(d.hp):null,y:d?+d.pos[1].toFixed(1):null,tgtDrone:!!(b.tgt&&b.tgt.isDrone),fx:DF.UAVX.FX.length,deb:DF.UAVX.DEB.length,fires:DF.UAVX.FIRES.length,cd:+DF.me.droneCd.toFixed(1),feed:document.getElementById('feed').textContent.slice(-60)}}")
            hist.append(s)
            if len(hist)%5==1 or s["st"]!=hist[-2]["st"]: print(round(time.time()-t0), J(s), pg.evaluate("()=>{const b=DF.bots[0];return [b.alive,b.cool.toFixed(2),b.react.toFixed(2),(b.yaw).toFixed(2),(b.tyaw).toFixed(2),b.pos.map(v=>+v.toFixed(1))]}"))
            if s['st']=='none' and s['fx']>0: break
            pg.wait_for_timeout(400)
        b.close(); print('\n'.join(logs[:8]))
finally:
    srv.kill()
