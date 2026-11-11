import subprocess, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux', '-noopen', '-port', '7815'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.6)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        pg = b.new_page(viewport={'width': 1600, 'height': 900})
        pg.goto('http://localhost:7815/'); pg.wait_for_timeout(900); pg.screenshot(path='/tmp/hero_boot.png')
        pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=90000)
        pg.click('#maps button[data-i="1"]'); pg.wait_for_timeout(3500); pg.screenshot(path='/tmp/hero.png')
        b.close()
finally:
    srv.kill()
