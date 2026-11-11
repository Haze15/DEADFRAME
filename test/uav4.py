import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7825'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
J=lambda x: json.dumps(x,ensure_ascii=False)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 640, 'height': 360}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7825/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.6}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=90000)
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0)}"); pg.keyboard.press('KeyG'); pg.wait_for_function("()=>DF.me.drone&&DF.me.drone.state==='fly'",timeout=120000)
        # dégâts en vol piloté : structure, puis abattu → chute → explosion au sol → neige « SIGNAL PERDU » → retour au corps
        pg.evaluate("()=>{const d=DF.me.drone;d.pos=[-2,6,-14];d.vel=[0,0,0];DF.UAVX.droneDamage(35,'b0','shot')}"); pg.wait_for_timeout(300)
        print('touché', pg.evaluate("()=>({st:DF.me.drone.state,hp:DF.me.drone.hp,msg:DF.me.drone.msg})"))
        pg.screenshot(path='/tmp/uav_hit.png')
        pg.evaluate("()=>DF.UAVX.droneDamage(80,'b0','shot')")
        print('abattu', pg.evaluate("()=>({st:DF.me.drone.state,alive:DF.me.drone.alive,feed:document.getElementById('feed').textContent.slice(-40)})"))
        pg.wait_for_function("()=>!DF.me.drone",timeout=240000)
        print('après impact', pg.evaluate("()=>({drone:DF.me.drone,inD:DF.me.inDrone,lost:+DF.me.uavLost.toFixed(2),cd:+DF.me.droneCd.toFixed(1),fx:DF.UAVX.FX.length,deb:DF.UAVX.DEB.length,fires:DF.UAVX.FIRES.length,lights:DF.UAVX.FXL.length,flash:+DF.UAVX.flash.toFixed(2)})"))
        pg.screenshot(path='/tmp/uav_lost.png')
        pg.wait_for_function("()=>DF.me.uavLost<=0",timeout=120000)
        pg.keyboard.press('KeyG'); pg.wait_for_timeout(300); print('relance immédiate refusée :', pg.evaluate("()=>({drone:!!DF.me.drone,tip:document.getElementById('tip').textContent})"))
        b.close(); print('\n'.join(logs[:8]))
finally:
    srv.kill()
