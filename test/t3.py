import json
from playwright.sync_api import sync_playwright
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
    pg = b.new_page(viewport={'width': 1280, 'height': 720}); logs=[]
    pg.on('console', lambda m: logs.append(m.text) if m.type=='error' else None); pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
    pg.goto('file:///home/claude/deadframe/dist/index.html'); pg.wait_for_timeout(1000)
    pg.evaluate("()=>{DF.CFG.scale=.6}"); pg.click('#go'); pg.wait_for_function('()=>DF.bots.some(b=>b.alive)',timeout=30000)
    print('solo', pg.evaluate('()=>({on:DF.online,net:document.getElementById("net").textContent,bots:DF.bots.map(b=>b.alive)})'))
    # se placer 9 m devant un bot, face à lui
    pg.evaluate('''()=>{const b=DF.bots.find(b=>b.alive);b.path=[];b.pos=[0,0,-8];b.yaw=b.tyaw=0;DF.me.pos=[0,0,-17];DF.me.vel=[0,0,0];DF.setLook(Math.PI,0);for(const o of DF.bots)if(o!==b){o.alive=false;o.resp=99}}''')
    pg.wait_for_timeout(1200); pg.screenshot(path='/tmp/s_bot.png')
    pg.wait_for_timeout(14000)
    print('after bot contact', pg.evaluate('()=>({hp:DF.me.hp,alive:DF.me.alive,deaths:DF.me.deaths,bot:DF.bots.filter(b=>b.alive).map(b=>[!!b.tgt,b.k])})'))
    pg.screenshot(path='/tmp/s_hurt.png')
    pg.evaluate('()=>{DF.me.pos=[-6,0,-8];DF.me.vel=[0,0,0];DF.setLook(.6,0);DF.me.hp=100;DF.me.alive=true;DF.me.lastHurt=-99;for(const o of DF.bots){o.alive=false;o.resp=99}}')
    pg.wait_for_timeout(1500); pg.screenshot(path='/tmp/s_yard2.png')
    pg.evaluate('()=>{DF.me.pos=[13,0,-21];DF.setLook(-1.2,0)}'); pg.wait_for_timeout(1200); pg.screenshot(path='/tmp/s_off2.png')
    print(logs[:10]); b.close()
