import sys
from playwright.sync_api import sync_playwright
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
shots = sys.argv[1].split(',')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
    pg = b.new_page(viewport={'width': 960, 'height': 540}); logs=[]
    pg.on('pageerror', lambda e: logs.append('PAGEERROR '+str(e)))
    pg.goto('file:///home/claude/deadframe/page/index.html'); pg.wait_for_timeout(5000)
    pg.evaluate("()=>{DF.CFG.bots=0}"); pg.click('#go'); pg.wait_for_timeout(2500)
    pg.evaluate("()=>{window.ST={w:0,ads:0,rl:-1,bolt:-1};setInterval(()=>{const m=DF.me;m.pos=[-6,0,-8];m.vel=[0,0,0];m.w=ST.w;m.swT=0;DF.DBG.ads=ST.ads;m.ads=ST.ads;if(ST.rl>=0)m.reload=DF.WPN[ST.w].rl*(1-ST.rl);if(ST.bolt>=0)m.bolt=1-ST.bolt;m.fl=0},5)}")
    pg.evaluate("()=>DF.setLook(.6,-.1)")
    for s in shots:
        w,ads,rl,bolt=(s.split(':')+['0','-1','-1'])[:4]
        pg.evaluate(f"()=>{{ST.w={w};ST.ads={ads};ST.rl={rl};ST.bolt={bolt}}}")
        pg.wait_for_timeout(3000); pg.screenshot(path=f'/tmp/ak/s_{s.replace(":","_")}.png')
    print(logs[:8]); b.close()
