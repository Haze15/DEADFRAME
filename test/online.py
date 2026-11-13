import subprocess, time, json, urllib.request
from playwright.sync_api import sync_playwright
env=dict(__import__('os').environ,PORT='7850')
srv = subprocess.Popen(['/home/claude/deadframe/test/deadframe-linux'], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
pages = subprocess.Popen(['python3','-m','http.server','7851','--bind','127.0.0.1'], cwd='/tmp/pages', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
r=urllib.request.urlopen('http://localhost:7850/info'); print('/info', r.read().decode().strip(), '| CORS:', r.headers.get('Access-Control-Allow-Origin'))
try: urllib.request.urlopen(urllib.request.Request('http://localhost:7850/quit',method='POST')); print('/quit ACCEPTÉ (problème)')
except Exception as e: print('/quit refusé en mode public :', e)
ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
try:
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=ARGS)
        out=[]
        for i,url in enumerate(['http://localhost:7851/','http://localhost:7851/','http://localhost:7850/']):
            pg=b.new_page(viewport={'width':320,'height':180}); pg.on('pageerror', lambda e,i=i: print(i,'PAGEERROR',e))
            if i<2: pg.add_init_script("try{localStorage.setItem('deadframe',JSON.stringify({server:'http://localhost:7850/'}))}catch(e){}")
            pg.goto(url); pg.wait_for_function("()=>document.getElementById('boot').classList.contains('done')",timeout=120000)
            pg.wait_for_function("()=>DF.online",timeout=60000); out.append(pg)
            print(f'client {i} ({url}) connecté :', pg.evaluate("()=>({online:DF.online,host:DF.host,net:document.getElementById('net').textContent.slice(0,90)})"))
        A,B,C=out
        A.evaluate("()=>{DF.CFG.bots=0}"); A.keyboard.press('Enter'); B.keyboard.press('Enter'); A.wait_for_timeout(4000)
        print('joueurs vus par B :', B.evaluate("()=>Object.values(DF.players).map(p=>p.name)"))
        # limite de débit : 1000 messages d'un coup depuis une connexion brute, comptés par une autre
        n=C.evaluate("""()=>new Promise(res=>{let got=0;const rx=new WebSocket('ws://localhost:7850/ws');rx.onmessage=e=>{if(e.data.includes('"t":"flood"'))got++};
           rx.onopen=()=>{const tx=new WebSocket('ws://localhost:7850/ws');tx.onopen=()=>{for(let i=0;i<1000;i++)tx.send('{"t":"flood","i":'+i+'}');setTimeout(()=>{res(got);tx.close();rx.close()},2500)}}})""")
        print('messages relayés sur 1000 envoyés en rafale :', n)
        b.close()
finally:
    srv.kill(); pages.kill(); print(srv.stdout.read().decode()[-300:])
