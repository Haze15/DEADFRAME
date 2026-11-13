import subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7842'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1120, 'height': 630}); errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://localhost:7842/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
        pg.evaluate("()=>{DF.CFG.bots=2;DF.CFG.scale=.7}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=120000)
        pg.evaluate("()=>{DF.me.pos=[0,0,14];DF.me.vel=[0,0,0];DF.setLook(0,0);DF.UAVX.launchDrone()}")
        pg.evaluate("()=>DF.__sim(150,1/60)")
        # vol en ACRO, incliné à droite en piqué, gaz moyens
        pg.evaluate("()=>{const d=DF.me.drone;d.mode=1;d.lever=.55;d.pos=[4,7,8];d.vel=[3,-1.5,-13];d.w=[0,0,0];const qa=(a,t)=>[a[0]*Math.sin(t/2),a[1]*Math.sin(t/2),a[2]*Math.sin(t/2),Math.cos(t/2)];const m=(a,b)=>[a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1],a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0],a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3],a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2]];d.q=m(m(qa([0,1,0],-.15),qa([1,0,0],-.5)),qa([0,0,1],-.55));d.flips=3;window.__hold=setInterval(()=>{DF.keys.KeyD=true;DF.keys.KeyW=true},5)}")
        pg.wait_for_timeout(2600); pg.screenshot(path='/tmp/fpv.png')
        b.close(); print('erreurs:', errs[:5])
finally:
    srv.kill()
