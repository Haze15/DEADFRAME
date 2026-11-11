import subprocess, time, sys, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7801'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1280, 'height': 720})
        logs = []
        pg.on('console', lambda m: logs.append(m.type + ': ' + m.text))
        pg.on('pageerror', lambda e: logs.append('PAGEERROR: ' + str(e)))
        pg.goto('http://localhost:7801/')
        pg.wait_for_timeout(2500)
        pg.screenshot(path='/tmp/s_menu.png')
        info = pg.evaluate('''()=>{const n=DF.nav;let ok=0,edges=0;for(let i=0;i<n.nodeOK.length;i++){if(n.nodeOK[i])ok++;edges+=n.adj[i].length}
          // connectivité
          const seen=new Uint8Array(n.nodeOK.length);let start=-1;for(let i=0;i<seen.length;i++)if(n.adj[i].length){start=i;break}
          const q=[start];seen[start]=1;for(let h=0;h<q.length;h++)for(const j of n.adj[q[h]])if(!seen[j]){seen[j]=1;q.push(j)}
          let iso=[];for(let i=0;i<seen.length;i++)if(n.nodeOK[i]&&!seen[i])iso.push([-40+2*(i%n.NG),-40+2*((i/n.NG)|0)]);
          const badSp=DF.spawns.filter(s=>!DF.freeAt(s[0],s[1]));
          return {ok,edges,reach:q.length,iso,badSp,online:DF.online,host:DF.host,boxes:DF.boxes.length}}''')
        print(json.dumps(info))
        pg.click('#go')
        pg.wait_for_timeout(1500)
        pg.screenshot(path='/tmp/s_spawn.png')
        # vues de test à des endroits précis
        shots = {'yard': ([-6, 0, -8], 0.6, 0), 'wh': ([-21, 0, -15], 0.2, 0.05), 'office': ([13, 0, -21], -1.2, 0), 'cont': ([-22, 0, 10], 1.57, 0)}
        for name, (pos, yaw, pitch) in shots.items():
            pg.evaluate(f'()=>{{DF.me.pos={pos};DF.me.vel=[0,0,0];DF.setLook({yaw},{pitch});DF.me.hp=100;DF.me.alive=true}}')
            pg.wait_for_timeout(900)
            pg.screenshot(path=f'/tmp/s_{name}.png')
        # tir + ADS
        pg.mouse.move(640, 360); pg.mouse.down(button='right'); pg.wait_for_timeout(600)
        pg.screenshot(path='/tmp/s_ads.png'); pg.mouse.down(); pg.wait_for_timeout(150); pg.screenshot(path='/tmp/s_fire.png'); pg.mouse.up(); pg.mouse.up(button='right')
        print('ammo', pg.evaluate('()=>DF.me.ammo'))
        pg.keyboard.press('KeyG'); pg.keyboard.down('Space'); pg.wait_for_timeout(2500); pg.keyboard.up('Space')
        pg.screenshot(path='/tmp/s_drone.png')
        st = pg.evaluate('()=>({bots:DF.bots.map(b=>[b.alive,Math.round(b.pos[0]),Math.round(b.pos[2]),b.path.length,!!b.tgt]),me:[DF.me.hp,DF.me.alive,DF.me.inDrone],fps:0})')
        print(json.dumps(st))
        print('\n'.join(logs[:30]))
        b.close()
finally:
    srv.kill()
