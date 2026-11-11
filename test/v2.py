import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7804'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
steps = json.loads(sys.argv[1]); W,H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv)>3 else (800,450)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': W, 'height': H}); logs=[]
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7804/'); pg.wait_for_timeout(1500)
        pg.evaluate("()=>{DF.CFG.scale=1;DF.CFG.bots=1;window.dispatchEvent(new Event('resize'))}"); pg.click('#go'); pg.wait_for_timeout(1500)
        pg.evaluate("()=>{DF.me.pos=[-6,0,-8];window.__hold=setInterval(()=>{if(window.__f)window.__f()},16)}")
        for i, st in enumerate(steps):
            pg.evaluate('(c)=>{window.__f=new Function(c);window.__f()}', st['js']); pg.wait_for_timeout(st.get('wait',900)); pg.screenshot(path=f'/tmp/w_{i}.png')
        print('\n'.join(logs[:12])); b.close()
finally:
    srv.kill()
