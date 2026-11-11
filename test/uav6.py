import subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7827'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 960, 'height': 540})
        pg.goto('http://localhost:7827/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.9}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=90000)
        pg.evaluate("()=>{DF.me.pos=[12,0,12];DF.DBG.cam={p:[5.2,1.75,4.9],y:.785,pi:-.12};document.getElementById('hud').style.display='none';DF.UAVX.launchDrone();DF.UAVX.exitDrone();const d=DF.me.drone;d.state='hold';d.spin=.25;d.pos=[4.5,1.6,4.2];d.yaw=d.yawS=2.0;d.gim=d.gimS=-.4;d.pt=.12;d.rl=-.08}")
        pg.wait_for_timeout(3000); pg.screenshot(path='/tmp/m_close.png')
        pg.evaluate("()=>{const d=DF.me.drone;d.spin=.9}"); pg.wait_for_timeout(2500); pg.screenshot(path='/tmp/m_spin.png')
        pg.evaluate("()=>{DF.me.drone=null;DF.DBG.cam={p:[6.5,1.6,6.5],y:.785,pi:-.06};DF.UAVX.explode([-.5,0.5,-1.5],1)}")
        for adv,name in [(.1,'y1'),(.45,'y2')]:
            pg.evaluate(f"()=>{{let t={adv};while(t>0){{DF.UAVX.fxUpdate(Math.min(.05,t));t-=.05}}}}"); pg.wait_for_timeout(200); pg.screenshot(path=f'/tmp/{name}.png')
        b.close()
finally:
    srv.kill()
