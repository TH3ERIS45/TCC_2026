#!/usr/bin/env python3
"""Painel Wi-Fi no notebook; NAO utiliza USB nem comanda diretamente a UART.

A ESP32-CAM e a dona da sequencia MOVE -> DONE -> foto -> upload -> PHOTOACK.
O notebook: (1) apresenta estado e botoes por HTTP; (2) recebe e salva JPEG.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import threading
import time
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from PIL import Image, UnidentifiedImageError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mosaico
import conexao
import geometria

# Limites e portas compartilhados pelas rotas de aquisição e visualização.
MAX_PHOTO_BYTES = 5_000_000
STREAM_PORT = 81
STREAM_CHUNK_BYTES = 8192
MOSAIC_POLL_INTERVAL_SECONDS = 5
MOSAIC_HISTORY_LIMIT = 8
PHOTO_GALLERY_LIMIT = 80

BASE = Path(__file__).resolve().parent
FOTOS = BASE / 'capturas'
FOTOS.mkdir(exist_ok=True)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_PHOTO_BYTES
LOCK = threading.Lock()
MOSAIC_LOCK = threading.RLock()
ESP_URL = 'http://192.168.1.80'
TOKEN = ''


def foto_id_valido(value: str) -> bool:
    return bool(re.fullmatch(r'[1-9][0-9]{0,8}', value))


def validar_jpeg(data: bytes) -> None:
    if len(data) < 1024 or not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
        raise ValueError('JPEG incompleto ou invalido')
    with Image.open(io.BytesIO(data)) as im:
        if im.format != 'JPEG':
            raise ValueError('O arquivo nao e JPEG')
        im.verify()


def salvar_foto(data: bytes, photo_id: str, x: str, y: str, pasta: Path = FOTOS) -> Path:
    """So devolve sucesso apos validar, gravar e sincronizar o arquivo no disco."""
    if not foto_id_valido(photo_id):
        raise ValueError('ID invalido')
    for value in (x, y):
        if not re.fullmatch(r'[0-9]{1,7}', value):
            raise ValueError('Coordenada invalida')
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError('JPEG maior que 5 MB')
    validar_jpeg(data)
    pasta.mkdir(parents=True, exist_ok=True)
    path = pasta / f'foto_{int(photo_id):09d}_X{x}_Y{y}.jpg'
    temp = path.with_suffix('.part')
    with LOCK:
        csv_file = pasta / 'manifesto.csv'
        manifestado = False
        if csv_file.exists() and csv_file.stat().st_size:
            with open(csv_file, newline='', encoding='utf-8') as fh:
                for registro in csv.DictReader(fh):
                    if registro.get('photo_id') == photo_id:
                        if registro.get('filename') != path.name:
                            raise ValueError('ID de foto ja registrado com outra coordenada')
                        manifestado = True
        # Retransmissoes do MESMO ID e das MESMAS coordenadas nao sobrescrevem
        # JPEGs nem duplicam linhas; um manifesto perdido e reparado no retry.
        if path.exists():
            validar_jpeg(path.read_bytes())
        else:
            with open(temp, 'wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, path)
        if not manifestado:
            new_file = not csv_file.exists() or csv_file.stat().st_size == 0
            with open(csv_file, 'a', newline='', encoding='utf-8') as fh:
                writer = csv.writer(fh)
                if new_file:
                    writer.writerow(('photo_id', 'filename', 'x_steps', 'y_steps', 'received_at'))
                writer.writerow((photo_id, path.name, x, y, datetime.now().isoformat(timespec='seconds')))
                fh.flush()
                os.fsync(fh.fileno())
    return path


@app.post('/api/photos/receive')
def receive_photo():
    if request.headers.get('X-Photo-Token', '') != TOKEN:
        return Response('Chave de upload incorreta', status=403)
    pid = request.headers.get('X-Photo-Id', '')
    x, y = request.headers.get('X-Photo-X', ''), request.headers.get('X-Photo-Y', '')
    try:
        if request.content_length is not None and request.content_length > MAX_PHOTO_BYTES:
            return Response('JPEG excede 5 MB', status=413)
        salvar_foto(request.get_data(), pid, x, y)
    except (ValueError, OSError, UnidentifiedImageError) as err:
        return Response(f'Falha ao salvar JPEG: {err}', status=422)
    return Response(f'OK:{pid}', mimetype='text/plain')


@app.get('/painel.css')
def sheet():
    return send_from_directory(BASE, 'painel.css', mimetype='text/css')


@app.get('/painel.js')
def javascript():
    return send_from_directory(BASE, 'painel.js', mimetype='application/javascript')


@app.get('/planejador.js')
def planejador():
    return send_from_directory(BASE, 'planejador.js', mimetype='application/javascript')


@app.get('/modelo3d.js')
def modelo3d():
    return send_from_directory(BASE, 'modelo3d.js', mimetype='application/javascript')


@app.get('/')
def home():
    return send_from_directory(BASE, 'painel.html')


@app.get('/api/camera/stream')
def mjpeg_stream():
    """Proxy do MJPEG da ESP32: o token nunca aparece no HTML/URL.

    O WebServer de controle continua na porta 80, independente do video:81.
    A desconexao do browser fecha a conexao upstream em vez de deixá-la presa.
    """
    # Usar apenas o host; --esp aceita opcionalmente :80 para a API principal.
    stream_host = urlparse(ESP_URL).hostname
    if not stream_host:
        return Response('IP da ESP32-CAM invalido', status=503)
    stream_url = f'http://{stream_host}:{STREAM_PORT}/stream'
    try:
        upstream = requests.get(
            stream_url,
            headers={'X-Api-Key': TOKEN, 'Cache-Control': 'no-cache'},
            stream=True,
            timeout=(3, 10),
        )
    except requests.RequestException as err:
        return Response('Stream ESP32 indisponivel: ' + str(err), status=503)
    if upstream.status_code != 200:
        status = upstream.status_code
        upstream.close()
        return Response(
            'Stream indisponivel. Verifique se a camera esta livre e se o firmware foi atualizado.',
            status=409 if status == 409 else 502,
        )
    content_type = upstream.headers.get('content-type', '')
    if not content_type.lower().startswith('multipart/x-mixed-replace'):
        upstream.close()
        return Response('Resposta de stream invalida', status=502)

    def frames():
        try:
            for piece in upstream.iter_content(chunk_size=STREAM_CHUNK_BYTES):
                if piece:
                    yield piece
        except requests.RequestException:
            # Uma desconexao de rede encerra a imagem sem afetar outras rotas.
            pass
        finally:
            upstream.close()

    return Response(
        stream_with_context(frames()),
        content_type='multipart/x-mixed-replace; boundary=frame',
        headers={'Cache-Control': 'no-store, no-cache, must-revalidate',
                 'X-Accel-Buffering': 'no'},
    )


def mosaic_session_file() -> Path:
    return FOTOS / 'mosaicos' / 'sessao_atual.json'


def mosaic_session():
    path = mosaic_session_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def save_session(state):
    mosaico.salvar_json_atomico(mosaic_session_file(), state)


def start_mosaic_session():
    """Marcar offset ANTES das novas fotos, nunca apagar os JPEGs anteriores."""
    manifest = FOTOS / 'manifesto.csv'
    with MOSAIC_LOCK:
        session = {'state':'running', 'offset':manifest.stat().st_size if manifest.exists() else 0,
                   'started_at':datetime.now().isoformat(timespec='seconds'), 'result':None, 'error':''}
        save_session(session)
    thread = threading.Thread(target=watch_mosaic_session, daemon=True, name='watch-cnc-mosaic')
    thread.start()


def watch_mosaic_session():
    """Observa finalizacao SEM tocar nos motores nem no protocolo das fotos."""
    while True:
        time.sleep(MOSAIC_POLL_INTERVAL_SECONDS)
        with MOSAIC_LOCK:
            ses = mosaic_session()
            if not ses or ses.get('state') != 'running':
                return
        try:
            resp = requests.get(ESP_URL + '/api/status', headers={'X-Api-Key':TOKEN}, timeout=3)
            if resp.status_code != 200:
                continue
            status=resp.json()
        except (requests.RequestException, ValueError):
            continue
        if status.get('stage') == 'ERRO':
            # Não fabricar conclusão quando a sequência travou: operador pode recuperar.
            continue
        if (not status.get('active') and not status.get('moving') and
                status.get('stage') == 'PARADO' and
                isinstance(status.get('total'),int) and status['total'] > 0 and
                status.get('point',-1) >= status['total']):
            with MOSAIC_LOCK:
                ses = mosaic_session()
                if not ses or ses.get('state') != 'running':
                    return
                ses['state']='processing';save_session(ses)
            try:
                cfg=mosaico.carregar_config(FOTOS)
                if cfg['automatico']:
                    meta=mosaico.gerar_mosaico(FOTOS,cfg,offset=ses['offset'])
                    ses['result']=meta
                    ses['state']='completed'
                else:
                    ses['state']='completed'
            except (OSError, ValueError, MemoryError) as exc:
                ses['state']='error';ses['error']=str(exc)
            with MOSAIC_LOCK:
                save_session(ses)
            return
        # Indisponibilidade ocasional de rede não deve cancelar o acompanhamento.


@app.route('/api/mosaico/config', methods=['GET','POST'])
def mosaic_config():
    if request.method == 'GET':
        return jsonify(mosaico.carregar_config(FOTOS))
    try:
        cfg=mosaico.validar_config(request.get_json(force=True))
        with MOSAIC_LOCK:
            mosaico.salvar_json_atomico(FOTOS / 'mosaicos' / 'config.json',cfg)
        return jsonify(cfg)
    except (ValueError, OSError, TypeError) as exc:
        return jsonify({'error':str(exc)}),400


@app.get('/api/mosaico/status')
def mosaic_status():
    target=FOTOS/'mosaicos'
    latest=[]
    if target.exists():
        for p in sorted(target.glob('mosaico_*.jpg'),reverse=True)[:MOSAIC_HISTORY_LIMIT]:
            meta_path=target/(p.name+'.json')
            if meta_path.exists():
                try:
                    latest.append(json.loads(meta_path.read_text(encoding='utf-8')))
                except (OSError, ValueError):
                    pass
    return jsonify({'session':mosaic_session(), 'mosaics':latest})


@app.post('/api/mosaico/gerar')
def mosaic_generate():
    """Geração manual independente do roteiro, apenas com fotos já confirmadas."""
    try:
        data=request.get_json(force=True)
        source=data.get('source') if isinstance(data,dict) else ''
        if source not in ('sessao','recentes'):
            raise ValueError('Escolha sessão atual ou últimas posições fotografadas')
        with MOSAIC_LOCK:
            ses=mosaic_session()
            if ses and ses.get('state') in ('running','processing'):
                raise ValueError('Aguarde o roteiro terminar antes de montar o mosaico')
            if source=='sessao' and not ses:
                raise ValueError('Ainda não existe sessão de percurso registrada neste notebook')
            cfg=mosaico.carregar_config(FOTOS)
            meta=mosaico.gerar_mosaico(FOTOS,cfg,offset=ses['offset'] if source=='sessao' else 0,
                                      recentes=source=='recentes')
        return jsonify(meta)
    except (ValueError, TypeError, OSError, MemoryError) as exc:
        return jsonify({'error':str(exc)}),422


@app.get('/mosaicos/<filename>')
def mosaic_file(filename):
    if not re.fullmatch(r'mosaico_\d{8}_\d{6}_\d{6}\.jpg',filename):
        return Response('Nome inválido',status=400)
    return send_from_directory(FOTOS / 'mosaicos',filename,mimetype='image/jpeg')




# Medidas observadas nas fotos da montagem real; nao substituem os limites do Arduino.
GEOMETRIA_FILE = BASE / 'geometria_maquete.json'


@app.route('/api/geometria', methods=['GET', 'POST'])
def geometria_canteiro():
    if request.method == 'GET':
        return jsonify(geometria.carregar(GEOMETRIA_FILE))
    try:
        cfg = request.get_json(force=True)
        # Configuracao nao comanda motores. Nunca salvar limite mecanico aqui.
        with LOCK:
            return jsonify(geometria.salvar(GEOMETRIA_FILE, cfg))
    except (ValueError, OSError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400

@app.get('/api/config')
def config():
    # Diagnostico local. Nunca retornar a API_KEY ao navegador.
    return jsonify({'esp_target': ESP_URL})


@app.get('/api/photos')
def photos():
    names = sorted((p.name for p in FOTOS.glob('foto_*.jpg')), reverse=True)[:PHOTO_GALLERY_LIMIT]
    return jsonify(names)


@app.get('/fotos/<path:filename>')
def photo_file(filename):
    if not re.fullmatch(r'foto_[0-9]{9}_X[0-9]+_Y[0-9]+\.jpg', filename):
        return Response('Nome invalido', status=400)
    return send_from_directory(FOTOS, filename, mimetype='image/jpeg')


ALLOWED = {
    ('GET', '/api/status'), ('GET', '/api/route'),
    ('POST', '/api/route'), ('POST', '/api/start'), ('POST', '/api/stop'),
    ('POST', '/api/command'), ('POST', '/api/jog-ping'), ('POST', '/api/retry'), ('POST', '/api/recover'),
    ('POST', '/api/manual-photo'), ('POST', '/api/flash'),
}


@app.route('/api/esp/<path:resource>', methods=['GET', 'POST'])
def proxy(resource):
    target = '/' + resource
    # O browser so fala com Flask e o Python so fala com endpoints fixos da ESP32.
    if (request.method, target) not in ALLOWED:
        return Response('Rota nao permitida', status=404)
    try:
        r = requests.request(
            request.method, ESP_URL + target,
            headers={'X-Api-Key': TOKEN, 'Content-Type': 'text/plain'},
            data=request.get_data() if request.method == 'POST' else None,
            timeout=15 if target == '/api/manual-photo' else 3.5,
        )
        # Só iniciar sessão se a ESP32 aceitou de fato /api/start.
        if r.status_code == 200 and target == '/api/start':
            start_mosaic_session()
        elif r.status_code == 200 and target == '/api/stop':
            with MOSAIC_LOCK:
                ses = mosaic_session()
                if ses and ses.get('state') == 'running':
                    ses['state'] = 'stopped'; save_session(ses)
        return Response(r.content, status=r.status_code,
                        mimetype=r.headers.get('content-type', 'text/plain').split(';')[0])
    except requests.RequestException as err:
        return Response('ESP32-CAM fora da rede: ' + str(err), status=503)


def main():
    global ESP_URL, TOKEN
    p = argparse.ArgumentParser(description='Painel Wi-Fi e receptor de fotos CNC')
    p.add_argument('--esp', help='IP/hostname da ESP32-CAM; sobrescreve configuração salva')
    p.add_argument('--chave', help='Chave configurada pela UART no ESP32; sobrescreve a salva')
    p.add_argument('--configurar', action='store_true', help='Salvar IP e chave neste notebook (sem exibir senha)')
    p.add_argument('--porta', type=int, default=8765)
    args = p.parse_args()
    if args.configurar:
        try:
            conexao.configurar_interativo()
        except (ValueError, OSError, EOFError, KeyboardInterrupt) as exc:
            p.error(str(exc))
        return
    try:
        salvo = conexao.carregar_config()
        esp = conexao.validar_alvo(args.esp or salvo.get('esp', ''))
        chave = conexao.validar_chave(args.chave or salvo.get('chave', ''))
    except ValueError as exc:
        p.error(str(exc) + '. Use python controle.py --configurar')
    ESP_URL = 'http://' + esp
    TOKEN = chave
    print('Painel: http://127.0.0.1:%d' % args.porta)
    print('Recebimento de fotos: porta %d na rede local (libere no firewall se necessario)' % args.porta)
    print('ESP32: ' + ESP_URL)
    # Se o notebook foi reiniciado durante o roteiro, retomar a observação.
    if (mosaic_session() or {}).get('state') == 'running':
        threading.Thread(target=watch_mosaic_session, daemon=True,
                         name='watch-cnc-mosaic').start()
    app.run(host='0.0.0.0', port=args.porta, threaded=True, debug=False)


if __name__ == '__main__':
    main()
