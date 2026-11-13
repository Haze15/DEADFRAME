import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7840'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 320, 'height': 180}); errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://localhost:7840/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
        pg.evaluate("()=>{DF.CFG.bots=0}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=120000)
        pg.evaluate("()=>{window.__f=window.requestAnimationFrame;}")
        E=pg.evaluate
        # isole la simulation : on met le jeu en pause logique (plus de rendu requis) et on avance le drone à la main
        E("()=>{DF.me.pos=[0,0,12];DF.me.vel=[0,0,0];DF.setLook(0,0);DF.UAVX.launchDrone()}")
        S="()=>{const d=DF.me.drone;if(!d)return null;const up=[2*(d.q[0]*d.q[1]-d.q[2]*d.q[3]),1-2*(d.q[0]*d.q[0]+d.q[2]*d.q[2]),2*(d.q[1]*d.q[2]+d.q[0]*d.q[3])];return {st:d.state,mode:d.mode,y:+d.pos[1].toFixed(2),pos:d.pos.map(v=>+v.toFixed(1)),v:+Math.hypot(...d.vel).toFixed(1),vh:+Math.hypot(d.vel[0],d.vel[2]).toFixed(1),tilt:+(Math.acos(Math.min(1,up[1]))*57.3).toFixed(0),m:d.m.map(v=>+v.toFixed(2)),flips:d.flips,hp:Math.round(d.hp),bat:+(d.bat*100).toFixed(1)}}"
        def sim(sec,keys=(),mouse=None):
            for k in keys: E(f"()=>{{DF.keys['{k}']=true}}")
            n=int(sec*60)
            if mouse: E(f"()=>{{for(let i=0;i<{n};i++){{DF.__setMouse({mouse[0]},{mouse[1]});DF.__sim(1,1/60)}}}}")
            else: E(f"()=>DF.__sim({n},1/60)")
            for k in keys: E(f"()=>{{DF.keys['{k}']=false}}")
            return E(S)
        print('décollage (2 s)     ', sim(2))
        a=sim(5); print('stationnaire 5 s    ', a)
        c=sim(2.5,['Space']); c=sim(1.5); print('montée à ~12 m      ', c)
        f=sim(2.0,['KeyW']); print('ANGLE avant 2 s     ', f, E('()=>DF.me.drone&&DF.me.drone.msg'))
        g=sim(1.5); print('relâché 1,5 s       ', g, '→ se remet à plat')
        y0=E(S)['y']; t=sim(2,['KeyD','KeyE','KeyW']); print('virage serré 2 s    ', t, f'altitude {y0} → {t["y"]} (perte en virage)')
        sim(1.5); sim(2,['Space']); print('montée gaz 2 s      ', E(S))
        r=E("()=>{DF.keys.KeyD=true;DF.__sim(3,1/60);const m=DF.me.drone.m.map(v=>+v.toFixed(2));DF.keys.KeyD=false;return m}"); print('moteurs pendant un roulis à droite (AVD, AVG, ARD, ARG):', r)
        # ACRO : salto avant, plein gaz bref puis rotation tangage
        E("()=>{DF.keys.KeyT=true}"); E("()=>{DF.UAVX.__mode&&0}")
        E("()=>{document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyT'}))}")
        E("()=>{if(DF.me.drone.mode!==1){window.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyT'}));window.dispatchEvent(new KeyboardEvent('keyup',{code:'KeyT'}))}}"); E("()=>{DF.keys.KeyT=false}")
        print('mode après T        ', E(S)['mode'])
        sim(1)
        sim(.6,['ShiftLeft']); fl=sim(.75,['KeyW']); print('ACRO salto avant    ', fl)
        rec=sim(.5,['KeyS']); rec=sim(1); print('après rattrapage    ', rec)
        tn=sim(.55,['KeyD']); sim(1); print('ACRO tonneau        ', E(S))
        b.close(); print('erreurs:', errs[:5])
finally:
    srv.kill()
