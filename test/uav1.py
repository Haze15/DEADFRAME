import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7820'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
J=lambda x: json.dumps(x,ensure_ascii=False)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1280, 'height': 720}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e))); pg.on('console', lambda m: logs.append(m.text) if m.type=='error' and 'TUNNEL' not in m.text else None)
        pg.goto('http://localhost:7820/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.7}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=60000); pg.wait_for_timeout(1800)
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0)}"); pg.wait_for_timeout(300)
        S=lambda: pg.evaluate("()=>{const d=DF.me.drone;return d?{st:d.state,pos:d.pos.map(v=>+v.toFixed(2)),v:+Math.hypot(...d.vel).toFixed(2),pt:+d.pt.toFixed(2),rl:+d.rl.toFixed(2),spin:+d.spin.toFixed(2),bat:+(d.bat*100).toFixed(1),lq:+d.lq.toFixed(2),hp:d.hp,zoom:+d.zoom.toFixed(2),inD:DF.me.inDrone}:{none:true,cd:+DF.me.droneCd.toFixed(1),inD:DF.me.inDrone}}")
        pg.keyboard.press('KeyG'); pg.wait_for_timeout(300); print('lancement', J(S()))
        pg.wait_for_timeout(2600); print('après décollage', J(S()))
        pg.keyboard.down('KeyW'); pg.keyboard.down('ShiftLeft'); pg.wait_for_timeout(1200); print('avant + accélération', J(S())); pg.screenshot(path='/tmp/uav_fly.png')
        pg.keyboard.up('ShiftLeft'); pg.keyboard.up('KeyW'); pg.keyboard.down('Space'); pg.wait_for_timeout(1500); pg.keyboard.up('Space'); print('montée', J(S()))
        pg.keyboard.down('ControlLeft'); pg.wait_for_timeout(700); pg.keyboard.up('ControlLeft'); print('descente (Ctrl)', J(S()))
        pg.mouse.wheel(0,-300); pg.wait_for_timeout(200); pg.mouse.wheel(0,-300); pg.wait_for_timeout(1200); print('zoom molette', J(S()))
        pg.evaluate("()=>{const d=DF.me.drone;d.yaw=-2.2;d.gim=-.35}"); pg.wait_for_timeout(1500); pg.screenshot(path='/tmp/uav_zoom.png')
        pg.mouse.wheel(0,600); pg.wait_for_timeout(800)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(400); print('Échap', J(S()), 'menu ouvert:', pg.evaluate("()=>!document.getElementById('menu').classList.contains('off')"))
        # un bot repère le drone en stationnaire et lui tire dessus
        pg.evaluate("()=>{DF.CFG.bots=1;}")
        pg.evaluate("()=>{const d=DF.me.drone;d.pos=[-6,4,-16];d.vel=[0,0,0];DF.me.pos=[-6,0,-6]}")
        pg.wait_for_timeout(400)
        print('menu?', pg.evaluate("()=>!document.getElementById('menu').classList.contains('off')"))
        b.close()
        print('\n'.join(logs[:10]))
finally:
    srv.kill()
