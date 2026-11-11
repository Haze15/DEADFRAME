import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7802'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        logs = []
        pages = []
        for i in range(2):
            pg = b.new_page(viewport={'width': 800, 'height': 450})
            pg.on('console', lambda m, i=i: logs.append(f'{i} {m.type}: {m.text}') if m.type == 'error' else None)
            pg.on('pageerror', lambda e, i=i: logs.append(f'{i} PAGEERROR: {e}'))
            pg.goto('http://localhost:7802/')
            pg.evaluate("()=>{DF.CFG.scale=.6;DF.CFG.bots=2;document.getElementById('iname').value='P%d'}" % i)
            pg.wait_for_timeout(800)
            pg.click('#go')
            pages.append(pg)
        A, B = pages
        A.wait_for_timeout(2500)
        print('A', A.evaluate('()=>({on:DF.online,host:DF.host,players:Object.values(DF.players).map(p=>[p.name,p.alive]),bots:DF.bots.length})'))
        print('B', B.evaluate('()=>({on:DF.online,host:DF.host,players:Object.values(DF.players).map(p=>[p.name,p.alive]),bots:DF.bots.map(b=>[b.alive,Math.round(b.pos[0]),Math.round(b.pos[2])])})'))
        # place A face à B dans une zone dégagée ; bots éloignés gelés via hp
        A.evaluate('()=>{DF.me.pos=[30,0,36];DF.me.vel=[0,0,0];DF.setLook(Math.PI/2,0)}')   # regarde vers -x
        B.evaluate('()=>{DF.me.pos=[36,0,39.5];DF.me.vel=[0,0,0]}')
        A.wait_for_timeout(1500)
        B.evaluate('()=>{DF.me.pos=[22,0,39.5];DF.me.vel=[0,0,0];DF.setLook(-Math.PI/2,0)}')
        A.evaluate('()=>{DF.me.pos=[30,0,39.5];DF.me.vel=[0,0,0];DF.setLook(Math.PI/2,-0.03)}')
        A.wait_for_timeout(1500)
        A.screenshot(path='/tmp/mp_A.png')
        hp0 = B.evaluate('()=>DF.me.hp')
        A.evaluate('()=>{DF.me.ads=1;DF.gunRef.yaw=DF.me.yaw;DF.gunRef.pitch=DF.me.pitch;}')
        for _ in range(6):
            A.evaluate('()=>{DF.me.cool=0;DF.me.ads=1;DF.me.spd=0;DF.gunRef.yaw=Math.PI/2;DF.gunRef.pitch=-0.03;DF.fire()}')
            A.wait_for_timeout(250)
        B.wait_for_timeout(800)
        print('B hp', hp0, '->', B.evaluate('()=>[DF.me.hp,DF.me.alive,DF.me.deaths]'), 'A kills', A.evaluate('()=>DF.me.kills'))
        B.screenshot(path='/tmp/mp_B.png')
        # hôte quitte -> B devient hôte et reprend les bots
        hostA = A.evaluate('()=>DF.host')
        (A if hostA else B).close()
        other = B if hostA else A
        other.wait_for_timeout(6000)
        print('after leave', other.evaluate('()=>({host:DF.host,players:Object.keys(DF.players).length,bots:DF.bots.map(b=>[b.alive,Math.round(b.pos[0]),Math.round(b.pos[2]),b.path.length])})'))
        print('\n'.join(logs[:20]))
        b.close()
finally:
    srv.kill(); print(srv.stdout.read().decode()[-600:])
