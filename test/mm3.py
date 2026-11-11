import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7811'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1280, 'height': 720}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7811/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.click('#maps button[data-i="2"]'); pg.wait_for_timeout(2600); pg.screenshot(path='/tmp/st2.png')
        pg.click('#maps button[data-i="0"]'); pg.wait_for_timeout(1200)
        pg.click('#tabs button[data-t=quit]'); pg.wait_for_timeout(500); pg.screenshot(path='/tmp/mm_quit.png')
        # déploiement réel, puis menu en pause, quitter la partie
        pg.evaluate("()=>{DF.CFG.bots=2}"); pg.click('#tabs button[data-t=deploy]'); pg.wait_for_timeout(300)
        pg.keyboard.press('Enter'); pg.wait_for_timeout(250); pg.screenshot(path='/tmp/ins.png'); pg.wait_for_function('()=>DF.bots.length>0&&DF.me.alive',timeout=60000); pg.wait_for_timeout(1500)
        st=pg.evaluate("()=>({alive:DF.me.alive,w:DF.me.w,menuOff:document.getElementById('menu').classList.contains('off'),deploys:DF.PROF.deploys,bots:DF.bots.length})")
        pg.evaluate("()=>{const b=DF.bots[0];b.alive=true;b.hp=10;b.pos=[DF.me.pos[0],0,DF.me.pos[2]-6];b.tpos=b.pos;}")
        pg.evaluate("()=>{const b=DF.bots[0];window.__k=DF.me.kills;DF.PROF.kills;}")
        # tir à la tête simulé : on vise la tête du bot
        pg.evaluate("""()=>{const b=DF.bots[0],e=[DF.me.pos[0],DF.me.pos[1]+1.55-.55*DF.me.crouch,DF.me.pos[2]],h=[b.pos[0],b.pos[1]+1.63,b.pos[2]],d=[h[0]-e[0],h[1]-e[1],h[2]-e[2]];DF.setLook(Math.atan2(-d[0],-d[2]),Math.atan2(d[1],Math.hypot(d[0],d[2])));}""")
        pg.wait_for_timeout(500)
        pg.evaluate("()=>{DF.gunRef.yaw=DF.me.yaw;DF.gunRef.pitch=DF.me.pitch;DF.me.cool=0;DF.me.spd=0;DF.me.ads=1;DF.fire()}"); pg.wait_for_timeout(400)
        pr=pg.evaluate("()=>({kills:DF.PROF.kills,heads:DF.PROF.heads,xp:DF.PROF.xp,done:DF.PROF.done,feed:document.getElementById('feed').textContent})")
        pg.evaluate("()=>{document.exitPointerLock&&document.exitPointerLock()}")
        pg.evaluate("()=>{DF.leaveMatch()}"); pg.wait_for_timeout(600)
        lv=pg.evaluate("()=>({started:DF.me.alive,menu:!document.getElementById('menu').classList.contains('off'),bots:DF.bots.length,sec:document.querySelector('#tabs .on').dataset.t,op:document.getElementById('mmOp').textContent})")
        print('deploy',st); print('kill',pr); print('leave',lv); print(logs[:5]); b.close()
finally:
    srv.kill()
