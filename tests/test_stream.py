"""Verificacoes do stream sem hardware (nao equivalem a compilar ESP32)."""
from pathlib import Path
from unittest.mock import patch
import unittest

from test_receptor import mod

ROOT=Path(__file__).resolve().parents[1]

class FakeStreamResponse:
    def __init__(self,code=200,kind='multipart/x-mixed-replace; boundary=frame'):
        self.status_code=code
        self.headers={'content-type':kind}
        self.closed=False
    def iter_content(self,chunk_size):
        assert chunk_size==8192
        yield b'--frame\r\nContent-Type: image/jpeg\r\n'
        yield b'FAKEJPEG\r\n'
    def close(self):
        self.closed=True

class StreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.esp=(ROOT/'esp32cam/esp32cam.ino').read_text(encoding='utf-8')
        cls.js=(ROOT/'notebook/painel.js').read_text(encoding='utf-8')
        cls.html=(ROOT/'notebook/painel.html').read_text(encoding='utf-8')
        cls.arduino=(ROOT/'arduino_cnc/arduino_cnc.ino').read_bytes()

    def test_video_no_servidor_independente_e_autenticado(self):
        self.assertIn('WebServer server(80)',self.esp)
        self.assertIn('WiFiServer videoServer(81)',self.esp)
        self.assertIn('xTaskCreatePinnedToCore(tarefaVideo',self.esp)
        self.assertIn('X-Api-Key:',self.esp)
        self.assertIn('multipart/x-mixed-replace; boundary=frame',self.esp)

    def test_upload_preserva_fotos_e_priority(self):
        for signal in ('PHOTOACK ', 'fotografarEEnviar(pendenteId)',
                       'cameraUploadBusy', 'cameraMutex', '!executando',
                       'fotoFrameMode', 'currentFrameMode'):
            self.assertIn(signal,self.esp)
        self.assertIn('streamFrameMode=FRAMESIZE_VGA;', self.esp)
        self.assertIn('fotoFrameMode=FRAMESIZE_VGA;', self.esp)
        self.assertIn('FRAMESIZE_VGA',self.esp)
        self.assertIn('frame2jpg(',self.esp)
        self.assertIn('FRAMESIZE_VGA',self.esp)

    def test_interface_stream_e_grade(self):
        for element in ('id="liveImage"', 'id="liveGrid"',
                        'data-action="live-start"','data-action="live-stop"'):
            self.assertIn(element,self.html)
        for line in ("img.src='/api/camera/stream", "case 'live-start':",
                     "case 'live-stop':", "if(liveOn)stopLive('Pausado para fotografar')",
                     "if(liveOn)stopLive('Pausado para o roteiro')"):
            self.assertIn(line,self.js)
        self.assertNotIn('X-Api-Key',self.js)  # nenhuma chave visivel ao navegador

    def test_proxy_envia_chave_no_cabecalho_e_fecha_upstream(self):
        old_url,old_token=mod.ESP_URL,mod.TOKEN
        mod.ESP_URL='http://192.168.2.169'
        mod.TOKEN='minha-chave-123456'
        upstream=FakeStreamResponse()
        try:
            with patch.object(mod.requests,'get',return_value=upstream) as get:
                response=mod.mjpeg_stream()
                self.assertEqual(response.status_code,200)
                self.assertIn('boundary=frame',response.content_type)
                self.assertIn(b'FAKEJPEG',b''.join(response.data))
                self.assertTrue(upstream.closed)
                get.assert_called_once()
                kwargs=get.call_args.kwargs
                self.assertEqual(get.call_args.args[0],'http://192.168.2.169:81/stream')
                self.assertEqual(kwargs['headers']['X-Api-Key'],'minha-chave-123456')
                self.assertTrue(kwargs['stream'])
        finally:
            mod.ESP_URL,mod.TOKEN=old_url,old_token

    def test_proxy_trata_busy_e_nao_expõe_credentials(self):
        upstream=FakeStreamResponse(code=409)
        with patch.object(mod.requests,'get',return_value=upstream):
            response=mod.mjpeg_stream()
        self.assertEqual(response.status_code,409)
        self.assertTrue(upstream.closed)
        self.assertNotIn('minha-chave',str(response.data))

if __name__=='__main__':
    unittest.main()
