import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7803'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
views = json.loads(sys.argv[1])
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 640, 'height': 480}); logs=[]
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7803/'); pg.wait_for_timeout(1500)
        pg.evaluate("()=>{DF.CFG.scale=1;DF.CFG.bots=0;DF.CFG.fish=0;window.dispatchEvent(new Event('resize'))}"); pg.click('#go'); pg.wait_for_timeout(1500)
        print('models', pg.evaluate('()=>Object.keys(DF.MODELS)'))
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0);document.getElementById('hud').style.opacity=0}")
        for i, v in enumerate(views):
            pg.evaluate('(v)=>{DF.DBG.view=v}', v); pg.wait_for_timeout(1300); pg.screenshot(path=f'/tmp/v_{i}.png')
        print('\n'.join(logs[:12])); b.close()
finally:
    srv.kill()
