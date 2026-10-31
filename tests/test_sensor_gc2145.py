"""Testes estaticos do caminho RGB565 -> JPEG; nao simulam a camera real."""
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parents[1]
ESP = (BASE / "esp32cam" / "esp32cam.ino").read_text(encoding="utf-8")

class GC2145Tests(unittest.TestCase):
    def test_usa_rgb565_com_um_so_buffer(self):
        self.assertIn("c.pixel_format=PIXFORMAT_RGB565", ESP)
        self.assertIn("c.fb_count=1", ESP)
        self.assertNotIn("c.pixel_format=PIXFORMAT_JPEG", ESP)
        self.assertIn("psramFound()", ESP)

    def test_foto_convertida_antes_de_enviar(self):
        a = ESP.index("bool capturarJpegFotografico(")
        b = ESP.index("bool autorizado()", a)
        bloco = ESP[a:b]
        for token in ("cameraMutex", "frame2jpg(fb, FOTO_QUALIDADE_JPEG",
                      "esp_camera_fb_return(fb)", "xSemaphoreGive(cameraMutex)",
                      'http.addHeader("Content-Type", "image/jpeg")',
                      'http.addHeader("X-Photo-X"', 'http.addHeader("X-Photo-Y"',
                      'http.sendRequest("POST", jpeg, jpegLen)',
                      'answer != "OK:" + String(id)', 'free(jpeg)'):
            self.assertIn(token, bloco)
        self.assertLess(bloco.index('frame2jpg('), bloco.index('http.sendRequest('))
        self.assertIn('if (!capturarJpegFotografico(jpeg, jpegLen))', bloco)
        self.assertIn('return false;', bloco)

    def test_stream_convertido_por_software(self):
        a = ESP.index('void tarefaVideo(')
        b = ESP.index('void initCamera()',a)
        bloco = ESP[a:b]
        self.assertIn('frame2jpg(fb, STREAM_QUALIDADE_JPEG', bloco)
        self.assertIn('client.write(jpeg, jpegLen)', bloco)
        self.assertIn('free(jpeg)', bloco)
        self.assertIn('streamPermitido()', bloco)
        self.assertIn('xSemaphoreGive(cameraMutex)', bloco)
        self.assertIn('streamFrameMode=FRAMESIZE_VGA;', ESP)
        self.assertIn('fotoFrameMode=FRAMESIZE_VGA;', ESP)
        self.assertIn('streamFrameMode == FRAMESIZE_VGA ? 640', ESP)

    def test_protocolo_photoack_intacto(self):
        for token in ('fotoConfirmada(', 'PHOTOACK_TIMEOUT_MS = 18000UL',
                      'server.on("/api/start"', 'server.on("/api/manual-photo"',
                      'server.on("/api/recover"',
                      'enviarArduino("PHOTOACK " + String(pendenteId))',
                      'if(fotografarEEnviar(pendenteId))'):
            self.assertIn(token, ESP)
        self.assertIn('"ESP32-4.2-GC2145-UARTACK-FIX1"',ESP)
        self.assertIn('cameraSensorPid',ESP)

if __name__ == '__main__': unittest.main()
