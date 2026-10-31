"""Verificacoes de integracao do flash; hardware precisa teste separado."""
from pathlib import Path
import unittest
BASE=Path(__file__).resolve().parents[1]
FW=(BASE/'esp32cam/esp32cam.ino').read_text(encoding='utf-8')
PY=(BASE/'notebook/controle.py').read_text(encoding='utf-8')
JS=(BASE/'notebook/painel.js').read_text(encoding='utf-8')
HTML=(BASE/'notebook/painel.html').read_text(encoding='utf-8')
ARD=(BASE/'arduino_cnc/arduino_cnc.ino').read_bytes()
class FlashIntegration(unittest.TestCase):
 def test_api_cam_e_proxy(self):
  self.assertIn('server.on("/api/flash", HTTP_POST',FW)
  self.assertIn("('POST', '/api/flash')",PY)
  self.assertIn("esp('/api/flash','POST'",JS)
  self.assertIn('server.send(400,"text/plain","Use ON, OFF, AUTO ON ou AUTO OFF")',FW)
 def test_manual_watchdog(self):
  self.assertIn('#define FLASH_LED_GPIO 4',FW)
  self.assertIn('FLASH_MANUAL_TIMEOUT_MS = 60000UL',FW)
  self.assertIn('definirFlashManual(false);',FW)
  self.assertIn('pinMode(FLASH_LED_GPIO,OUTPUT)',FW)
  self.assertIn('flashManualDesdeMs',FW)
 def test_auto_opt_in_e_heuristica(self):
  self.assertIn('prefs.getBool("flashauto",false)',FW)
  self.assertIn('prefs.putBool("flashauto",true)',FW)
  self.assertIn('prefs.putBool("flashauto",false)',FW)
  self.assertIn('estimarBrilhoRGB565(fb)',FW)
  self.assertIn('flashUltimoBrilho<FLASH_AUTO_LIMIAR',FW)
  self.assertIn('definirFlashTemporario(true);',FW)
  self.assertIn('definirFlashTemporario(false);',FW)
  self.assertIn('if (fb) esp_camera_fb_return(fb);',FW)
  self.assertIn('frame2jpg(fb, FOTO_QUALIDADE_JPEG',FW)
 def test_painel_modo_simples_e_avancado(self):
  self.assertEqual(HTML.count('data-flash-auto'),2)
  self.assertEqual(HTML.count('data-action="flash-on"'),2)
  self.assertEqual(HTML.count('data-action="flash-off"'),2)
  self.assertIn('function updateFlashPanel()',JS)
  self.assertIn('function setFlash(option)',JS)
 def test_photoack_e_arduino_invariantes(self):
  self.assertIn('enviarArduino("PHOTOACK " + String(pendenteId))',FW)
  self.assertIn('if(fotografarEEnviar(pendenteId))',FW)
  self.assertIn('enviarArduino("JOGPING")',FW)
  # Um marcador do Arduino que existe no pacote anterior deve continuar igual;
  # o patch do flash nao altera o codigo do Arduino.
  self.assertGreater(len(ARD),20000)
if __name__ == '__main__':unittest.main()
