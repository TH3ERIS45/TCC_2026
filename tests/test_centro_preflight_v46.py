from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARDUINO = (ROOT / "arduino_cnc/arduino_cnc.ino").read_text(encoding="utf-8")
ESP = (ROOT / "esp32cam/esp32cam.ino").read_text(encoding="utf-8")
PANEL = (ROOT / "notebook/painel.js").read_text(encoding="utf-8")
SERVER = (ROOT / "notebook/controle.py").read_text(encoding="utf-8")

class CenterAndPreflightV46(unittest.TestCase):
    def test_center_offset_only_changes_center_command(self):
        self.assertIn("CENTER_OFFSET_X_MM = 42.0f", ARDUINO)
        self.assertIn("CENTER_TARGET_X = (MAX_X / 2L) + CENTER_OFFSET_X_STEPS", ARDUINO)
        block = ARDUINO.split('if (cmd == "CENTER")', 1)[1].split('if (cmd.startsWith("MOVE "))', 1)[0]
        self.assertIn("targetX = CENTER_TARGET_X", block)
        self.assertIn("targetY = CENTER_TARGET_Y", block)
        self.assertIn("CENTER_TARGET_X > MAX_X", block)
        self.assertNotIn("CENTER_TARGET", ARDUINO.split('if (cmd.startsWith("SCANMOVE "))', 1)[1].split('if (cmd.startsWith("JOG X "))', 1)[0])

    def test_center_telemetry_reaches_panel(self):
        self.assertIn('F(",CENTERX=")', ARDUINO)
        self.assertIn('F(",CENTERY=")', ARDUINO)
        self.assertIn('center_x', ESP)
        self.assertIn('center_y', ESP)
        self.assertIn('state.center_x', PANEL)
        self.assertIn('state.center_y', PANEL)

    def test_autonomous_start_preflight_before_executing(self):
        start = ESP.split('server.on("/api/start",HTTP_POST',1)[1].split('server.on("/api/stop",HTTP_POST',1)[0]
        self.assertLess(start.index('verificarReceptorNotebook()'), start.index('executando=true'))
        for check in ('!cameraReady', 'WiFi.status() != WL_CONNECTED', 'verificarReceptorNotebook()'):
            self.assertIn(check, start)
        self.assertIn('/api/photos/ready', ESP)
        self.assertIn('bool roteiroTemFoto = false', start)
        self.assertIn('if (!roteiroTemFoto)', start)
        self.assertIn('route.some(point=>point.p)', PANEL)
        self.assertIn("@app.get('/api/photos/ready')", SERVER)

    def test_photo_receiver_preflight_requires_token_and_write_access(self):
        self.assertIn("request.headers.get('X-Photo-Token', '') != TOKEN", SERVER)
        self.assertIn('tempfile.NamedTemporaryFile', SERVER)
        self.assertIn("session_dir = FOTOS / 'mosaicos'", SERVER)
        self.assertIn("return Response('READY', status=200", SERVER)

if __name__ == '__main__':
    unittest.main()
