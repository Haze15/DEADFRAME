import sys, json, struct
for f in sys.argv[1:]:
    d=open(f,'rb'); magic,ver,total=struct.unpack('<4sII',d.read(12)); ln,typ=struct.unpack('<I4s',d.read(8)); j=json.loads(d.read(ln))
    print('=====',f.split('/')[-1],total//1024,'KB')
    print(' asset:',json.dumps(j.get('asset'),ensure_ascii=False)[:600])
    print(' ext used:',j.get('extensionsUsed'),'required:',j.get('extensionsRequired'))
    print(' nodes',len(j.get('nodes',[])),'meshes',len(j.get('meshes',[])),'prims',sum(len(m['primitives']) for m in j.get('meshes',[])),'mats',len(j.get('materials',[])),'tex',len(j.get('textures',[])),'images',[(i.get('mimeType'),j['bufferViews'][i['bufferView']]['byteLength']//1024 if 'bufferView' in i else i.get('uri','')[:30]) for i in j.get('images',[])][:12])
    print(' skins',[len(s['joints']) for s in j.get('skins',[])],'anims',[(a.get('name'),len(a['channels'])) for a in j.get('animations',[])])
    tri=0;mn=[1e9]*3;mx=[-1e9]*3
    for m in j.get('meshes',[]):
        for p in m['primitives']:
            a=j['accessors'][p['attributes']['POSITION']]; 
            if 'indices' in p: tri+=j['accessors'][p['indices']]['count']//3
            else: tri+=a['count']//3
            for k in range(3): mn[k]=min(mn[k],a['min'][k]); mx[k]=max(mx[k],a['max'][k])
    print(' tris',tri,'local bbox',[round(v,3) for v in mn],[round(v,3) for v in mx])
    print(' attrs',sorted(set(k for m in j['meshes'] for p in m['primitives'] for k in p['attributes'])), 'comp idx',set(j['accessors'][p['indices']]['componentType'] for m in j['meshes'] for p in m['primitives'] if 'indices' in p))
    print(' scene roots',[ (j['nodes'][n].get('name'), {k:v for k,v in j['nodes'][n].items() if k in('matrix','scale','rotation','translation')}) for n in j['scenes'][j.get('scene',0)]['nodes']][:4])
    print(' mats',[(m.get('name'), list(m.get('pbrMetallicRoughness',{}).keys()), m.get('alphaMode')) for m in j.get('materials',[])][:10])
