import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7821'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
J=lambda x: json.dumps(x,ensure_ascii=False)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1120, 'height': 630}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7821/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.6}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=60000); pg.wait_for_timeout(1500)
        S=lambda: pg.evaluate("()=>{const d=DF.me.drone;return d?{st:d.state,pos:d.pos.map(v=>+v.toFixed(1)),hp:+d.hp.toFixed(0),inD:DF.me.inDrone,lock:!!document.pointerLockElement,resume:getComputedStyle(document.getElementById('resume')).display}:{none:true,cd:+DF.me.droneCd.toFixed(1),inD:DF.me.inDrone,lost:+DF.me.uavLost.toFixed(2)}}")
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(Math.PI,-.05)}"); pg.keyboard.press('KeyG'); pg.wait_for_function("()=>DF.me.drone&&DF.me.drone.state==='fly'",timeout=60000)
        print('vol', J(S()), 'pointer lock:', pg.evaluate("()=>!!document.pointerLockElement"))
        pg.keyboard.press('Escape'); pg.wait_for_timeout(500); print('après Échap', J(S()))
        if pg.evaluate("()=>getComputedStyle(document.getElementById('resume')).display")=='flex': pg.screenshot(path='/tmp/uav_resume.png'); pg.click('#resume'); pg.wait_for_timeout(300)
        # drone en stationnaire devant l'opérateur ; un bot le repère et l'abat
        pg.evaluate("()=>{const d=DF.me.drone;d.pos=[-6,3.2,-2];d.vel=[0,0,0];DF.setLook(0,.25);DF.CFG.bots=1}")
        pg.evaluate("()=>{DF.bots.length=0}")
        pg.evaluate("""()=>{const n=DF.bots;}""")
        hp0=pg.evaluate("()=>DF.me.drone.hp")
        pg.evaluate("""()=>{window.__bot=true}""")
        # ajout d'un bot hôte face au drone (il ne voit pas l'opérateur : demi-tour forcé)
        pg.evaluate("""()=>{const B=DF.bots;DF.CFG.bots=1;}""")
        b.close()
        print('\n'.join(logs[:8]))
finally:
    srv.kill()
