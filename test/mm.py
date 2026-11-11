import subprocess, time, json, sys
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7810'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
W,H=(int(sys.argv[1]),int(sys.argv[2])) if len(sys.argv)>2 else (1440,810)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': W, 'height': H}); logs=[]
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7810/'); pg.wait_for_timeout(700); pg.screenshot(path='/tmp/mm_boot.png')
        pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=60000); pg.wait_for_timeout(2500)
        pg.screenshot(path='/tmp/mm_deploy.png')
        for sec in ['loadout','operators','missions','settings','quit']:
            pg.click(f'#tabs button[data-t={sec}]'); pg.wait_for_timeout(1500); pg.screenshot(path=f'/tmp/mm_{sec}.png')
        print(json.dumps(pg.evaluate("()=>({sec:document.querySelector('#tabs .on').dataset.t,prof:DF.PROF,boot:[...document.querySelectorAll('#bootLog li')].map(l=>l.textContent)})"),ensure_ascii=False)[:900])
        print('\n'.join(logs[:12])); b.close()
finally:
    srv.kill()
