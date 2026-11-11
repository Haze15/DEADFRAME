import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7806'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1000, 'height': 562}); logs=[]
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7806/'); pg.wait_for_timeout(1500)
        # fausse manette
        pg.evaluate("""()=>{window.__gp={connected:true,axes:[0,0,0,0],buttons:Array.from({length:17},()=>({pressed:false,value:0})),vibrationActuator:null};navigator.getGamepads=()=>[window.__gp];DF.CFG.scale=.6;DF.CFG.bots=0;window.dispatchEvent(new Event('resize'))}""")
        pg.wait_for_timeout(300)
        pg.evaluate("()=>{__gp.buttons[0]={pressed:true,value:1}}"); pg.wait_for_timeout(500); pg.evaluate("()=>{__gp.buttons[0]={pressed:false,value:0}}")
        pg.wait_for_timeout(800)
        print('entré via manette:', pg.evaluate("()=>[DF.me.alive,document.getElementById('menu').style.display,DF.pad.on]"))
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0)}")
        p0 = pg.evaluate("()=>[DF.me.pos.slice(),DF.me.yaw,DF.me.ammo[0]]")
        pg.evaluate("()=>{__gp.axes=[0,-1,0.8,0];__gp.buttons[7]={pressed:true,value:1}}"); pg.wait_for_timeout(2500); pg.evaluate("()=>{__gp.axes=[0,0,0,0];__gp.buttons[7]={pressed:false,value:0}}")
        p1 = pg.evaluate("()=>[DF.me.pos.slice(),DF.me.yaw,DF.me.ammo[0]]")
        print('manette: déplacement', [round(a-b_,2) for a,b_ in zip(p1[0],p0[0])], 'lacet', round(p1[1]-p0[1],2), 'munitions', p0[2], '->', p1[2])
        # drone : décollage au stick (mode 2), avance, puis mode ACRO
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0);__gp.buttons[12]={pressed:true,value:1}}"); pg.wait_for_timeout(400); pg.evaluate("()=>{__gp.buttons[12]={pressed:false,value:0}}")
        pg.evaluate("()=>{__gp.axes=[0,-0.8,0,0]}"); pg.wait_for_timeout(3000)
        d1 = pg.evaluate("()=>DF.me.drone&&({alt:DF.me.drone.pos[1],thr:DF.me.drone.thr,mode:DF.me.drone.mode,inD:DF.me.inDrone})")
        pg.evaluate("()=>{__gp.axes=[0,0,0,-1]}"); pg.wait_for_timeout(3000)
        d2 = pg.evaluate("()=>DF.me.drone&&({pos:DF.me.drone.pos.map(v=>+v.toFixed(1)),spd:Math.hypot(...DF.me.drone.vel).toFixed(1),up:DF.me.drone.q.map(v=>+v.toFixed(2))})")
        pg.screenshot(path='/tmp/drone_osd.png')
        pg.evaluate("()=>{__gp.axes=[0,0,0,0];__gp.buttons[3]={pressed:true,value:1}}"); pg.wait_for_timeout(400); pg.evaluate("()=>{__gp.buttons[3]={pressed:false,value:0}}"); pg.wait_for_timeout(300)
        d3 = pg.evaluate("()=>DF.me.drone&&[DF.me.drone.mode,DF.me.drone.armed]")
        pg.evaluate("()=>{__gp.axes=[0,-0.2,0,-0.6]}"); pg.wait_for_timeout(3000)
        d4 = pg.evaluate("()=>DF.me.drone&&({mode:DF.me.drone.mode,lever:+DF.me.drone.lever.toFixed(2),armed:DF.me.drone.armed,alt:+DF.me.drone.pos[1].toFixed(1),w:DF.me.drone.w.map(v=>+v.toFixed(1)),dmg:+DF.me.drone.dmg.toFixed(2)})")
        pg.screenshot(path='/tmp/drone_osd.png')
        pg.evaluate("()=>{__gp.axes=[0,0,0,0];__gp.buttons[12]={pressed:true,value:1}}"); pg.wait_for_timeout(400); pg.evaluate("()=>{__gp.buttons[12]={pressed:false,value:0}}"); pg.wait_for_timeout(1500)
        d5 = pg.evaluate("()=>({inDrone:DF.me.inDrone,drone:DF.me.drone&&{armed:DF.me.drone.armed,alt:+DF.me.drone.pos[1].toFixed(1)}})")
        # à pied : R maintenu -> compteur près de l'arme ; R bref -> rechargement
        pg.evaluate("()=>{DF.me.ammo[DF.me.w]=17}"); pg.keyboard.down('KeyR'); pg.wait_for_function('()=>DF.me.chk>.9',timeout=30000); chk=pg.evaluate("()=>[+DF.me.chk.toFixed(2),DF.me.reload]"); pg.screenshot(path='/tmp/chk.png'); pg.keyboard.up('KeyR'); pg.wait_for_timeout(300)
        r0=pg.evaluate("()=>DF.me.reload"); pg.keyboard.down('KeyR'); pg.wait_for_timeout(60); pg.keyboard.up('KeyR'); pg.wait_for_timeout(300); r1=pg.evaluate("()=>DF.me.reload>0")
        print('drone montée', d1); print('drone avance', d2); print('mode/armé après Y', d3); print('HORIZON gaz réels', d4); print('rendu la main (stationnaire)', d5); print('R maintenu [chk, reload]', chk, '| après relâche reload=', r0, '| R bref -> recharge:', r1)
        print('\n'.join(logs[:10])); b.close()
finally:
    srv.kill()
