from playwright.sync_api import sync_playwright
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
    pg = b.new_page(viewport={'width': 1000, 'height': 560}); logs=[]
    pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in('error','warning') and 'ReadPixels' not in m.text else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
    pg.goto('file:///home/claude/deadframe/page/index.html'); pg.wait_for_timeout(4000)
    print('models', pg.evaluate('()=>Object.keys(DF.MODELS).sort()'))
    pg.evaluate("()=>{DF.CFG.bots=2}"); pg.click('#go'); pg.wait_for_timeout(2500)
    pg.evaluate("()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0);DF.me.w=1;setInterval(()=>{const b=DF.bots[0];if(b){b.alive=true;b.hp=1e9;b.tgt=null;b.path=[];b.think=9;b.look=9;b.pos=[-8.0,0,-10.9];b.yaw=b.tyaw=3.74;b.tpos=b.pos}},16)}")
    pg.wait_for_timeout(2500); pg.screenshot(path='/tmp/page.png'); print(logs[:8]); b.close()
