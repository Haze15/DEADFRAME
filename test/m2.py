import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7807'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 900, 'height': 506}); logs=[]
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
        pg.goto('http://localhost:7807/'); pg.wait_for_timeout(2500)
        
        pg.click('#tabs button[data-t=op]'); 
        pg.click('#tabs button[data-t=arms]'); 
        pg.click('#tabs button[data-t=play]'); pg.click('.mapc[data-i="2"]'); pg.wait_for_timeout(1200)
        print('carte', pg.evaluate('()=>DF.map'))
        pg.evaluate("()=>{DF.CFG.bots=2}"); pg.click('#go'); pg.wait_for_timeout(2500)
        pg.evaluate("()=>{DF.me.pos=[6,0,0];DF.me.vel=[0,0,0];DF.setLook(1.3,0)}")
        pg.keyboard.press('Digit2'); pg.wait_for_timeout(2500)
        print('arme après changement', pg.evaluate('()=>[DF.me.w,DF.me.swT>0]'))
        pg.screenshot(path='/tmp/game1.png')
        print(pg.evaluate("()=>document.getElementById('cam').textContent.slice(-40)"))
        print('\n'.join(logs[:10])); b.close()
finally:
    srv.kill()
