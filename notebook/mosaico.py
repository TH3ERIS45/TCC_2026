"""Mosaico offline por coordenadas da CNC, sem interferir em PHOTOACK ou motores.

A imagem é um mapa esquemático das fotografias; não é ortofoto/georreferenciamento.
O campo de visão deve ser CALIBRADO em passos e a câmera precisa manter altura e ângulo.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

NAME = re.compile(r'^foto_\d{9}_X\d+_Y\d+\.jpg$')
MAX_PHOTOS = 48
MAX_PIXELS = 26_000_000
DEFAULT_SETTINGS = {
    'footprint_x': 600, 'footprint_y': 1500,
    'flip_x': False, 'flip_y': False, 'rotate': 0,
    'automatico': True, 'encaixe_fino': True,
}


def validar_config(cfg):
    if not isinstance(cfg, dict):
        raise ValueError('Configuração inválida')
    clean = {}
    for key in ('footprint_x', 'footprint_y'):
        val = cfg.get(key)
        if isinstance(val, bool) or not isinstance(val, int) or not 1 <= val <= 50000:
            raise ValueError(f'{key} deve ser um inteiro entre 1 e 50000 passos')
        clean[key] = val
    rot = cfg.get('rotate')
    if isinstance(rot, bool) or rot not in (0, 90, 180, 270):
        raise ValueError('Rotação deve ser 0, 90, 180 ou 270')
    clean['rotate'] = rot
    # Configurações antigas (v3.0) seguem aceitas após a atualização.
    cfg = {**DEFAULT_SETTINGS, **cfg}
    for key in ('flip_x', 'flip_y', 'automatico', 'encaixe_fino'):
        if not isinstance(cfg.get(key), bool):
            raise ValueError(f'{key} deve ser verdadeiro ou falso')
        clean[key] = cfg[key]
    return clean


def carregar_config(pasta):
    path = Path(pasta) / 'mosaicos' / 'config.json'
    if not path.exists():
        return DEFAULT_SETTINGS.copy()
    return validar_config(json.loads(path.read_text(encoding='utf-8')))


def salvar_json_atomico(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def ler_registros(pasta, offset=0):
    """Usa manifesto append-only; offset isola somente uma execução de percurso."""
    manifest = Path(pasta) / 'manifesto.csv'
    if not manifest.exists():
        return []
    result = []
    with manifest.open('rb') as f:
        if offset:
            if offset > manifest.stat().st_size:
                raise ValueError('Manifesto foi substituído após o início do percurso')
            f.seek(offset)
            raw = f.read().decode('utf-8-sig')
            rows = csv.reader(io.StringIO(raw))
            data = [dict(zip(('photo_id', 'filename', 'x_steps', 'y_steps', 'received_at'), row)) for row in rows]
        else:
            f.seek(0)
            content = f.read().decode('utf-8-sig')
            data = list(csv.DictReader(io.StringIO(content)))
    for row in data:
        try:
            name = row['filename']
            if not NAME.fullmatch(name):
                continue
            x = int(row['x_steps']); y = int(row['y_steps'])
            if x < 0 or y < 0 or x > 10_000_000 or y > 10_000_000:
                continue
            path = Path(pasta) / name
            if not path.is_file():
                continue
            result.append({'filename': name, 'x': x, 'y': y})
        except (KeyError, TypeError, ValueError):
            continue
    # Mesma coordenada fotografada várias vezes -> usar a foto mais recente.
    by_pos = {(r['x'], r['y']): r for r in result}
    return list(by_pos.values())


def _alinhar_vizinho(tile, pos, outros, max_x, max_y):
    """Refina apenas translação (sem deformar a planta) com ORB + consenso robusto.

    Só considera regiões sobrepostas previstas por X/Y; devolve None se o
    encaixe não é inequívoco. Não tenta fazer stitching livre de plantas repetidas.
    """
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Modo de encaixe fino requer opencv-python-headless; instale as dependências do projeto') from exc

    bx, by = pos
    tw, th = tile.size
    orb = cv2.ORB_create(nfeatures=1000, fastThreshold=12, edgeThreshold=12)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6))
    gray_b = clahe.apply(cv2.cvtColor(np.asarray(tile), cv2.COLOR_RGB2GRAY))
    results = []
    # Tenta somente os três vizinhos com maior região comum, nunca fotos distantes.
    neighbors = []
    for old, (ax, ay) in outros:
        x0, y0 = max(ax, bx), max(ay, by)
        x1, y1 = min(ax+tw,bx+tw), min(ay+th,by+th)
        w,h=x1-x0,y1-y0
        if w >= max(38, int(tw*.11)) and h >= max(38, int(th*.11)):
            neighbors.append((w*h, old, ax, ay, x0,y0,x1,y1))
    for _, old, ax, ay, x0,y0,x1,y1 in sorted(neighbors, key=lambda r:-r[0])[:3]:
        # A margem permite erros pequenos no posicionamento inicial por passos.
        m=min(max_x,max_y)
        x0=max(x0-m,ax,bx);y0=max(y0-m,ay,by)
        x1=min(x1+m,ax+tw,bx+tw);y1=min(y1+m,ay+th,by+th)
        a_x0,a_y0=x0-ax,y0-ay
        b_x0,b_y0=x0-bx,y0-by
        h=y1-y0;w=x1-x0
        if w<48 or h<48:continue
        a=old.crop((a_x0,a_y0,a_x0+w,a_y0+h))
        gray_a=clahe.apply(cv2.cvtColor(np.asarray(a),cv2.COLOR_RGB2GRAY))
        sub_b=gray_b[b_y0:b_y0+h,b_x0:b_x0+w]
        kp_a,des_a=orb.detectAndCompute(gray_a,None)
        kp_b,des_b=orb.detectAndCompute(sub_b,None)
        if des_a is None or des_b is None or len(kp_a)<10 or len(kp_b)<10:continue
        matches=[]
        for pair in matcher.knnMatch(des_a,des_b,k=2):
            if len(pair)!=2:continue
            best,second=pair
            if best.distance < .72*second.distance:
                pa=kp_a[best.queryIdx].pt
                pb=kp_b[best.trainIdx].pt
                # Delta da posição prevista para a posição sugerida por esse par.
                dx=(ax+a_x0+pa[0])-(bx+b_x0+pb[0])
                dy=(ay+a_y0+pa[1])-(by+b_y0+pb[1])
                if abs(dx)<=max_x and abs(dy)<=max_y:
                    matches.append((dx,dy,pa[0],pa[1]))
        if len(matches)<8:continue
        arr=np.asarray(matches,dtype=np.float32)
        # Desvio da maioria: não aceitar pareamento acidental de plantas repetidas.
        med=np.median(arr[:,:2],axis=0)
        d=np.linalg.norm(arr[:,:2]-med,axis=1)
        inliers=arr[d<=2.8]
        if len(inliers)<8 or len(inliers)/len(arr)<.60:continue
        spread=np.ptp(inliers[:,2:4],axis=0)
        if max(spread)<max(26,min(tw,th)*.11):continue
        dx,dy=np.median(inliers[:,:2],axis=0)
        results.append((len(inliers),float(dx),float(dy)))
    if not results:return None
    # Escolha pelo maior número de correspondências, sem acumular erros de ruído.
    _,dx,dy=max(results)
    return (bx+int(round(dx)),by+int(round(dy)))


def gerar_mosaico(pasta, settings, *, offset=0, recentes=False):
    """Cria um JPEG e um JSON em capturas/mosaicos, devolve metadados.

    Ajuste fino opcional com limites espaciais + suavização nas bordas.
    Em regiões sem dados a imagem permanece cinza-escuro.
    """
    settings = validar_config(settings)
    pasta = Path(pasta)
    registros = ler_registros(pasta, offset=0 if recentes else offset)
    if recentes:
        registros = registros[-MAX_PHOTOS:]
    if not registros:
        raise ValueError('Nenhuma foto da seleção foi encontrada no manifesto.csv')
    if len(registros) > MAX_PHOTOS:
        raise ValueError(f'A seleção possui {len(registros)} posições. Limite: {MAX_PHOTOS}; use uma sessão menor.')

    # Ler dimensões reais e rejeitar arquivo inválido sem interromper a aquisição da CNC.
    for row in registros:
        with Image.open(pasta / row['filename']) as img:
            img.verify()
        with Image.open(pasta / row['filename']) as img:
            row['size'] = img.size
    fw = settings['footprint_x']; fh = settings['footprint_y']
    minx = min(r['x'] - fw/2 for r in registros)
    maxx = max(r['x'] + fw/2 for r in registros)
    miny = min(r['y'] - fh/2 for r in registros)
    maxy = max(r['y'] + fh/2 for r in registros)
    extent_x, extent_y = maxx-minx, maxy-miny
    first_w, first_h = registros[0]['size']
    if settings['rotate'] in (90,270):
        first_w, first_h = first_h,first_w
    scale = min(first_w/fw, first_h/fh)
    width = max(1, math.ceil(extent_x * scale))
    height = max(1, math.ceil(extent_y * scale))
    if width * height > MAX_PIXELS:
        scale *= math.sqrt(MAX_PIXELS / (width*height))
        width = max(1, math.ceil(extent_x * scale))
        height = max(1, math.ceil(extent_y * scale))
    # Limite duplo para imagens extremamente panorâmicas.
    if max(width,height)>12000:
        scale *= 12000 / max(width,height)
        width=max(1, math.ceil(extent_x*scale));height=max(1, math.ceil(extent_y*scale))
    if width*height>MAX_PIXELS:
        scale *= math.sqrt(MAX_PIXELS/(width*height))*0.995
        width=max(1, math.ceil(extent_x*scale));height=max(1, math.ceil(extent_y*scale))
    if width*height>MAX_PIXELS:
        raise ValueError('Mosaico excede o limite de memória; reduza a área fotografada')
    tw=max(1,round(fw*scale)); th=max(1,round(fh*scale))
    if tw<8 or th<8:
        raise ValueError('Resolução insuficiente: calibre cobertura ou use fotos com maior resolução')

    # Preparar posições / imagens e alinhar sem tocar nos JPEGs originais.
    # Alinhamento usa as coordenadas como limite para evitar falsa correspondência.
    tiles=[]
    alinhadas=0
    rejeitadas=0
    requested=bool(settings['encaixe_fino'])
    if requested:
        try:
            import cv2  # noqa: F401
            import numpy  # noqa: F401
        except ImportError as exc:
            raise ValueError('Encaixe fino requer OpenCV: no venv execute python -m pip install -r requirements.txt') from exc
    max_corr_x=max(2,min(60,round(tw*.09)))
    max_corr_y=max(2,min(60,round(th*.09)))
    for row in registros:
        with Image.open(pasta/row['filename']) as img:
            tile=img.convert('RGB')
        rot=settings['rotate']
        if rot:tile=tile.rotate(rot,expand=True)
        if settings['flip_x']:tile=ImageOps.mirror(tile)
        if settings['flip_y']:tile=ImageOps.flip(tile)
        tile=tile.resize((tw,th),Image.Resampling.LANCZOS)
        px=round((row['x']-fw/2-minx)*scale)
        py=round((row['y']-fh/2-miny)*scale)
        if requested and tiles:
            refined=_alinhar_vizinho(tile,(px,py),tiles,max_corr_x,max_corr_y)
            if refined is not None:
                px,py=refined
                alinhadas+=1
            else:
                rejeitadas+=1
        tiles.append((tile,(px,py)))

    # O refinamento pode mudar os extremos em poucos pixels.
    min_px=min(pos[0] for _,pos in tiles)
    min_py=min(pos[1] for _,pos in tiles)
    max_px=max(pos[0]+tw for _,pos in tiles)
    max_py=max(pos[1]+th for _,pos in tiles)
    width=max_px-min_px;height=max_py-min_py
    if width*height>MAX_PIXELS or max(width,height)>12000:
        raise ValueError('Mosaico excedeu o limite após o encaixe fino; reduza a região')
    background=Image.new('RGB',(width,height),(29,37,47))
    covered=Image.new('L',(width,height),0)
    from PIL import ImageDraw
    blendwidth=max(1,min(45,tw//7,th//7))
    edge=Image.new('L',(tw,th),255)
    edraw=ImageDraw.Draw(edge)
    for i in range(blendwidth):
        val=max(15,round(255*(i+1)/blendwidth))
        edraw.rectangle((i,i,tw-i-1,th-i-1),outline=val)
    for tile,(px,py) in tiles:
        px-=min_px;py-=min_py
        left,top=max(px,0),max(py,0)
        right,bottom=min(px+tw,width),min(py+th,height)
        if right<=left or bottom<=top:continue
        local=(left-px,top-py,right-px,bottom-py)
        new=tile.crop(local)
        old=background.crop((left,top,right,bottom))
        seen=covered.crop((left,top,right,bottom))
        alpha=ImageChops.lighter(edge.crop(local),ImageOps.invert(seen))
        background.paste(Image.composite(new,old,alpha),(left,top))
        covered.paste(255,(left,top,right,bottom))

    target=pasta/'mosaicos'
    target.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename=f'mosaico_{stamp}.jpg'
    final=target/filename
    temp=target/(filename+'.part')
    try:
        with temp.open('wb') as f:
            background.save(f,'JPEG',quality=91,optimize=True)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,final)
    finally:
        if temp.exists():temp.unlink()
    meta={'filename':filename,'width':width,'height':height,
          'photos':len(registros),'settings':settings,
          'alignment':{'method':'pontos_comuns_limitados_por_XY' if requested else 'somente_coordenadas',
                       'adjusted':alinhadas,'fallback_xy':rejeitadas},
          'coordinates':{'min_x':min(r['x'] for r in registros),'max_x':max(r['x'] for r in registros),
                         'min_y':min(r['y'] for r in registros),'max_y':max(r['y'] for r in registros)},
          'created_at':datetime.now().isoformat(timespec='seconds'),
          'source':'ultimas_posicoes' if recentes else 'sessao',
          'note':'Reconstrução aproximada; o ajuste fino não garante costura perfeita ou mapa métrico.'}
    salvar_json_atomico(target/(filename+'.json'),meta)
    return meta
