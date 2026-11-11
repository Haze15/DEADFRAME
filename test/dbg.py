import subprocess, time, json
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7813'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 390, 'height': 844})
        pg.goto('http://localhost:7813/'); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.evaluate("()=>DF.showSec('quit')"); pg.wait_for_timeout(800)
        print(pg.evaluate("""()=>{const r=document.getElementById('qQuit').getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,e=document.elementFromPoint(x,y);
          const h=document.querySelector('.mm-top').getBoundingClientRect();return {btn:[r.x,r.y,r.width,r.height],hit:e&&(e.id||e.className),top:[h.x,h.y,h.width,h.height],menuScroll:document.getElementById('menu').scrollTop}}"""))
        b.close()
finally:
    srv.kill()
