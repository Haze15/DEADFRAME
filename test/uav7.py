import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7828'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
J=lambda x: json.dumps(x,ensure_ascii=False)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pages=[]
        for i in range(2):
            pg=b.new_page(viewport={'width':480,'height':270});pg.on('pageerror', lambda e,i=i: print(i,'PAGEERROR',e))
            pg.goto('http://localhost:7828/');pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
            pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.5;document.getElementById('iname').value='P%d'}"%i);pg.keyboard.press('Enter');pg.wait_for_function('()=>DF.me.alive&&DF.online',timeout=120000);pages.append(pg)
        A,B=pages
        A.evaluate("()=>{DF.me.pos=[0,0,10];DF.me.vel=[0,0,0];DF.setLook(0,0)}");A.keyboard.press('KeyG');A.wait_for_function("()=>DF.me.drone&&DF.me.drone.state==='fly'",timeout=180000)
        A.keyboard.press('KeyG');A.evaluate("()=>{const d=DF.me.drone;d.pos=[0,3,0];d.vel=[0,0,0];d.state='hold'}")
        B.wait_for_function("()=>Object.values(DF.players).some(p=>p.drone&&Math.abs(p.drone[1]-3)<.5)",timeout=120000)
        print('B voit le drone de A :', B.evaluate("()=>Object.values(DF.players).map(p=>p.drone)"))
        # B tire sur le drone de A
        B.evaluate("""()=>{DF.me.pos=[0,0,-8];DF.me.vel=[0,0,0];const e=[0,1.55,-8],t=[0,3,0],d=[t[0]-e[0],t[1]-e[1],t[2]-e[2]];DF.setLook(Math.atan2(-d[0],-d[2]),Math.atan2(d[1],Math.hypot(d[0],d[2])));DF.camS.pos=e;
          DF.gunRef.yaw=DF.me.yaw;DF.gunRef.pitch=DF.me.pitch;DF.me.cool=0;DF.me.reload=0;DF.me.swT=0;DF.me.spd=0;DF.me.ads=1;DF.me.onG=true;DF.fire()}""")
        A.wait_for_function("()=>!DF.me.drone||DF.me.drone.hp<100",timeout=120000)
        print('A après le tir de B :', A.evaluate("()=>DF.me.drone?{hp:DF.me.drone.hp,st:DF.me.drone.state,msg:DF.me.drone.msg}:'détruit'"))
        A.evaluate("()=>DF.UAVX.droneDamage(500,1,'shot')")
        A.wait_for_function("()=>!DF.me.drone",timeout=240000)
        B.wait_for_function("()=>DF.UAVX.FX.length>20",timeout=120000)
        print('B voit l\'explosion :', B.evaluate("()=>({fx:DF.UAVX.FX.length,debris:DF.UAVX.DEB.length,feu:DF.UAVX.FIRES.length})"), '| A :', A.evaluate("()=>({cd:+DF.me.droneCd.toFixed(1),feed:document.getElementById('feed').textContent.slice(-40)})"))
        b.close()
finally:
    srv.kill()
