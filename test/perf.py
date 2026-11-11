import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7823'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 960, 'height': 540})
        pg.goto('http://localhost:7823/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        def fps(label,ms=4000):
            n0=pg.evaluate("()=>{window.__n=0;window.__t=performance.now();(function f(){window.__n++;if(window.__run)requestAnimationFrame(f)})();window.__run=true;return 0}")
            pg.wait_for_timeout(ms); r=pg.evaluate("()=>{window.__run=false;return (window.__n/((performance.now()-window.__t)/1000)).toFixed(1)}"); print(label, r, 'i/s')
        fps('menu')
        pg.evaluate("()=>{DF.CFG.bots=0;DF.CFG.scale=.6}"); pg.keyboard.press('Enter'); pg.wait_for_function('()=>DF.me.alive',timeout=60000); pg.wait_for_timeout(500)
        fps('à pied')
        pg.keyboard.press('KeyG'); pg.wait_for_timeout(1500); fps('drone piloté')
        pg.keyboard.press('KeyG'); pg.wait_for_timeout(500); pg.evaluate("()=>{DF.setLook(Math.PI*0,0)}"); fps('drone vu de l\'extérieur')
        pg.evaluate("()=>{const d=DF.me.drone;DF.UAVX.explode([d.pos[0],1,d.pos[2]-3],1)}"); fps('explosion en cours',3000)
        b.close()
finally:
    srv.kill()
