from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HomeSemSensoresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'notebook/painel.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'notebook/painel.js').read_text(encoding='utf-8')
        cls.arduino = (ROOT / 'arduino_cnc/arduino_cnc.ino').read_text(encoding='utf-8')
        cls.esp = (ROOT / 'esp32cam/esp32cam.ino').read_text(encoding='utf-8')

    def test_ambas_opcoes_presentes(self):
        self.assertIn('data-action="home"', self.html)
        self.assertIn('data-action="auto-center"', self.html)
        self.assertIn('data-action="define-zero"', self.html)
        self.assertIn('data-jog="X:1"', self.html)

    def test_sem_falso_home_automatico(self):
        self.assertIn('não detecta a posição física ao ligar', self.html)
        self.assertIn('SEM SENSORES', self.js)
        self.assertIn("case 'auto-center':", self.js)
        self.assertIn('requireReady(true)', self.js)

    def test_calibracao_e_limites_existentes(self):
        self.assertIn('TRAVEL_X_MM = 328.0f', self.arduino)
        self.assertIn('TRAVEL_Y_MM = 910.0f', self.arduino)
        self.assertIn('if (cmd == "CENTER")', self.arduino)
        self.assertIn('if (cmd=="CENTER")', self.esp)
        self.assertIn('cmd.startsWith("SETPOS X ")', self.esp)
