import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7812'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 390, 'height': 844}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7812/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>{DF.CFG.bots=1;DF.CFG.loadout=1}"); pg.keyboard.press('Enter')
        print('fondu insertion actif:', pg.evaluate("()=>getComputedStyle(document.getElementById('ins')).display+' / '+document.getElementById('insName').textContent"))
        pg.wait_for_function('()=>DF.bots.length>0&&DF.me.alive',timeout=60000)
        print('arme au déploiement (loadout=1):', pg.evaluate('()=>DF.me.w'))
        res=pg.evaluate("""()=>{const b=DF.bots[0];b.alive=true;b.hp=10;b.think=99;b.look=99;b.path=[];b.tgt=null;b.last=null;
          DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];b.pos=[-6,0,-14];b.tpos=b.pos;b.crouch=0;
          const e=[DF.me.pos[0],DF.me.pos[1]+1.55,DF.me.pos[2]],h=[b.pos[0],b.pos[1]+1.63,b.pos[2]],d=[h[0]-e[0],h[1]-e[1],h[2]-e[2]];
          DF.setLook(Math.atan2(-d[0],-d[2]),Math.atan2(d[1],Math.hypot(d[0],d[2])));DF.camS.pos=e;
          DF.gunRef.yaw=DF.me.yaw;DF.gunRef.pitch=DF.me.pitch;DF.me.cool=0;DF.me.reload=0;DF.me.swT=0;DF.me.spd=0;DF.me.ads=1;DF.me.onG=true;DF.fire();
          return {alive:b.alive,P:{kills:DF.PROF.kills,heads:DF.PROF.heads,xp:DF.PROF.xp,done:DF.PROF.done},feed:document.getElementById('feed').textContent}}""")
        print('élimination:', json.dumps(res,ensure_ascii=False))
        pg.evaluate("()=>DF.leaveMatch()"); pg.evaluate("()=>DF.showSec('deploy')"); pg.wait_for_timeout(1200); pg.screenshot(path='/tmp/mob_dep.png',full_page=False)
        pg.evaluate("()=>DF.showSec('operators')"); pg.wait_for_timeout(900); pg.screenshot(path='/tmp/mm_op2.png')
        # quitter le jeu : arrêt réel du serveur
        pg.evaluate("()=>DF.showSec('quit')"); pg.wait_for_timeout(600); pg.screenshot(path='/tmp/mob_quit.png'); pg.evaluate("()=>document.getElementById('qQuit').click()"); pg.wait_for_timeout(2500)
        print('après QUIT:', pg.evaluate("()=>document.getElementById('qText').textContent"), '| serveur encore vivant:', srv.poll() is None)
        # mobile
        m = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
        print(logs[:5]); b.close()
finally:
    try: srv.kill()
    except: pass
    print(srv.stdout.read().decode()[-200:])
