import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7841'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 320, 'height': 180}); errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://localhost:7841/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
        pg.evaluate("()=>{DF.CFG.bots=0}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=120000)
        E=pg.evaluate
        S="()=>{const d=DF.me.drone;if(!d)return {detruit:true,delai:+DF.me.droneCd.toFixed(1),particules:DF.UAVX.FX.length,debris:DF.UAVX.DEB.length};return {st:d.state,pos:d.pos.map(v=>+v.toFixed(1)),v:+Math.hypot(...d.vel).toFixed(1),hp:Math.round(d.hp),msg:d.msgT>0?d.msg:''}}"
        sim=lambda sec,k=(): (E("(k)=>{for(const c of k)DF.keys[c]=true}",list(k)),E(f"()=>DF.__sim({int(sec*60)},1/60)"),E("(k)=>{for(const c of k)DF.keys[c]=false}",list(k)),E(S))[3]
        E("()=>{DF.me.pos=[0,0,12];DF.me.vel=[0,0,0];DF.setLook(0,0);DF.UAVX.launchDrone()}"); sim(2); sim(1.2,['Space']); sim(1); a=sim(1.5,['KeyW'])
        print('en vol, en mouvement ', a)
        E("()=>DF.UAVX.exitDrone()"); h1=sim(2); h2=sim(4); print('rend la main → stationnaire', h1, '→ 4 s plus tard', h2)
        E("()=>{DF.UAVX.launchDrone();DF.UAVX.uavRecall()}"); r=None
        for i in range(12):
            r=sim(1)
            if isinstance(r,str): break
        print('rappel automatique', r)
        # sur le dos au sol → X pour le retourner
        E("()=>{DF.me.droneCd=0;DF.UAVX.launchDrone()}"); sim(2)
        E("()=>{const d=DF.me.drone;d.pos=[2,.12,8];d.vel=[0,0,0];d.q=[0,0,1,0];d.w=[0,0,0];d.m=[0,0,0,0];d.state='fly';d.ts=-.6}"); t=sim(2.5); print('posé à l\'envers     ', t)
        E("()=>{window.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyX'}));window.dispatchEvent(new KeyboardEvent('keyup',{code:'KeyX'}))}"); print('après X             ', sim(2.5))
        # collision : plein gaz vers le mur de l'entrepôt
        E("()=>{const d=DF.me.drone;d.pos=[-4,3,-17];d.vel=[0,0,0];d.q=[0,Math.sin(Math.PI/4),0,Math.cos(Math.PI/4)];d.w=[0,0,0];d.state='fly';d.mode=0}")
        c=sim(.9,['KeyW']); print('dans le mur, vitesse modérée', c)
        E("()=>{const d=DF.me.drone;if(d){d.pos=[-4,3,-17];d.vel=[0,0,0];d.q=[0,Math.sin(Math.PI/4),0,Math.cos(Math.PI/4)];d.w=[0,0,0];d.state='fly'}}"); c=sim(1.4,['KeyW','ShiftLeft']); print('dans le mur, plein gaz', c)
        b.close(); print('erreurs:', errs[:5])
finally:
    srv.kill()
