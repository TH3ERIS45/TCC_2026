"""Revisao estatica da integracao JOG, sem movimento real de motores."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
ARD=(R/'arduino_cnc'/'arduino_cnc.ino').read_text()
ESP=(R/'esp32cam'/'esp32cam.ino').read_text()
JS=(R/'notebook'/'painel.js').read_text()
HTML=(R/'notebook'/'painel.html').read_text()
PYTHON=(R/'notebook'/'controle.py').read_text()

class JogContinuousTests(unittest.TestCase):
    def test_hold_uses_dedicated_ping_and_motor_watchdog(self):
        self.assertIn('JOG_WATCHDOG_MS = 1100UL', ARD)
        self.assertIn('if (cmd == "JOGPING")', ARD)
        self.assertIn('lastJogPingMillis = millis()', ARD)
        self.assertIn('stopMotion();\n    Serial.println(F("[ERRO] JOG watchdog:', ARD)
        self.assertIn('MIN_JOG_DELAY_US = 8000UL', ARD)
        self.assertIn('!homedX || !homedY || photoPending || scanInProgress', ARD)
    def test_wifi_gateway_and_browser_release_paths(self):
        self.assertIn('server.on("/api/jog-ping", HTTP_POST', ESP)
        self.assertIn('const unsigned long JOG_HTTP_WATCHDOG_MS', ESP)
        self.assertIn('if (jogHoldActive) return false', ESP)
        self.assertIn("('POST', '/api/jog-ping')", PYTHON)
        for event in ['pointerdown','pointerup','pointercancel','visibilitychange','blur']:
            self.assertIn("'"+event+"'", JS)
        self.assertIn("esp('/api/stop','POST','',2400)",JS)
        self.assertIn('jog_hold_supported',ESP)
        self.assertIn('jog_hold_supported',ESP)
        self.assertIn('setPointerCapture',JS)
        self.assertIn('id="holdJogMode"',HTML)
    def test_extended_step_options_and_existing_photoack(self):
        for n in [250,500,1000,2500,5000]:
            self.assertIn('data-step="'+str(n)+'"',HTML)
        self.assertIn('MAX_MANUAL_STEPS=5000',JS)
        self.assertIn('delta <= 5000',ESP)
        self.assertIn('PHOTOACK',ESP)
        self.assertIn('PHOTOACK',ARD)

if __name__=='__main__':unittest.main()
