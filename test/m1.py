import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7805'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
NAV='''()=>{const n=DF.nav,N=n.NG;const idx=(x,z)=>Math.round((z+40)/2)*N+Math.round((x+40)/2);const comp=new Int32Array(N*N).fill(-1);let nc=0,sizes=[];
 for(let i=0;i<N*N;i++){if(!n.adj[i]||!n.adj[i].length||comp[i]>=0)continue;const q=[i];comp[i]=nc;for(let h=0;h<q.length;h++)for(const j of n.adj[q[h]])if(comp[j]<0){comp[j]=nc;q.push(j)}sizes.push(q.length);nc++}
 const main=sizes.indexOf(Math.max(...sizes));const bad=DF.spawns.filter(s=>!DF.freeAt(s[0],s[1])||comp[idx(s[0],s[1])]!==main);
 return {map:DF.map,boxes:DF.boxes.length,comps:sizes.sort((a,b)=>b-a).slice(0,6),badSpawns:bad}}'''
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 900, 'height': 620}); logs=[]
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7805/'); pg.wait_for_timeout(1500)
        pg.evaluate("()=>{DF.CFG.scale=1;DF.CFG.bots=0;window.dispatchEvent(new Event('resize'))}"); pg.click('#go'); pg.wait_for_timeout(800)
        pg.evaluate("()=>{document.getElementById('hud').style.opacity=0}")
        for i in (1,2,3):
            pg.evaluate(f"()=>{{DF.loadMap({i});DF.DBG.cam={{p:[0,62,34],y:0,pi:-1.07}}}}"); pg.wait_for_timeout(900)
            print(json.dumps(pg.evaluate(NAV))); pg.screenshot(path=f'/tmp/map{i}_top.png')
        print('\n'.join(logs[:10])); b.close()
finally:
    srv.kill()
