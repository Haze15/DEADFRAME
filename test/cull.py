import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7830'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 960, 'height': 540}); logs=[]
        pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7830/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
        pg.evaluate("()=>{DF.CFG.bots=6;DF.CFG.scale=.8}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=120000)
        print('secteurs sur la carte Dépôt :', pg.evaluate('()=>DF.chunks'))
        # 1) même image avec et sans tri : aucun objet ne doit manquer
        pg.evaluate("()=>{DF.me.pos=[2,0,6];DF.me.vel=[0,0,0];DF.setLook(.3,-.05)}"); pg.wait_for_timeout(1500)
        pg.evaluate("()=>{DF.CULL.off=false}"); pg.wait_for_timeout(1200); pg.screenshot(path='/tmp/c_on.png')
        pg.evaluate("()=>{DF.CULL.off=true}"); pg.wait_for_timeout(1200); pg.screenshot(path='/tmp/c_off.png')
        pg.evaluate("()=>{DF.CULL.off=false}")
        # 3) mesure : part de la carte dessinée et temps d'image, selon la direction du regard
        for yaw,label in [(0,'vers le nord'),(1.57,"vers l'ouest"),(3.14,'vers le sud'),(-1.57,"vers l'est")]:
            pg.evaluate(f"()=>{{DF.me.pos=[0,0,0];DF.setLook({yaw},-.05)}}"); pg.wait_for_timeout(600)
            on=pg.evaluate("()=>{DF.CULL.off=false;DF.bench(1);return [DF.bench(6),DF.CULL.drawn/DF.CULL.total,DF.CULL.objIn,DF.CULL.objOut]}")
            off=pg.evaluate("()=>{DF.CULL.off=true;DF.bench(1);const r=DF.bench(6);DF.CULL.off=false;return r}")
            print(f'regard {label:13s}: carte dessinée {on[1]*100:4.0f} % · objets dessinés {on[2]} / ignorés {on[3]} · image {on[0]:6.1f} ms avec tri, {off:6.1f} ms sans')
        # 2) preuve visuelle : champ de vision figé, vue du dessus
        pg.evaluate("()=>{DF.me.pos=[-4,0,4];DF.setLook(.9,0)}"); pg.wait_for_timeout(800)
        pg.evaluate("()=>{DF.CULL.freeze=true;document.getElementById('hud').style.display='none';DF.DBG.cam={p:[-4,95,4],y:.9,pi:-1.5707}}"); pg.wait_for_timeout(2500); pg.screenshot(path='/tmp/c_top.png')
        b.close(); print('\n'.join(logs[:6]))
finally:
    srv.kill()
