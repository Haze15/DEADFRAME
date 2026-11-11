import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7826'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 960, 'height': 540}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7826/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.8}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=90000)
        # caméra fixe : on regarde un drone en stationnaire, puis il explose au sol
        pg.evaluate("()=>{DF.me.pos=[12,0,12];DF.me.vel=[0,0,0];DF.DBG.cam={p:[6.5,1.6,6.5],y:.785,pi:-.06};document.getElementById('hud').style.display='none'}")
        pg.evaluate("()=>{DF.UAVX.launchDrone();DF.UAVX.exitDrone();const d=DF.me.drone;d.state='hold';d.spin=.6;d.pos=[3.6,1.45,3.4];d.yaw=d.yawS=2.2;d.gim=d.gimS=-.3}")
        pg.wait_for_timeout(2500); pg.screenshot(path='/tmp/x0.png')
        pg.evaluate("()=>{const d=DF.me.drone;d.pos=[4.4,1.7,4.1];d.spin=.9;d.pt=.25;d.rl=-.18}"); pg.wait_for_timeout(1500); pg.screenshot(path='/tmp/x_close.png')
        pg.evaluate("()=>{DF.me.drone=null;DF.UAVX.explode([-.5,0.5,-1.5],1)}")
        for i,(adv,name) in enumerate([(0,'x1'),(.18,'x2'),(.6,'x3'),(2.2,'x4')]):
            pg.evaluate(f"()=>{{let t={adv};while(t>0){{DF.UAVX.fxUpdate(Math.min(.05,t));t-=.05}}}}"); pg.wait_for_timeout(200); pg.screenshot(path=f'/tmp/{name}.png')
        b.close(); print('\n'.join(logs[:8]))
finally:
    srv.kill()
