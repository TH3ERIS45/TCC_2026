"""Regressoes: confirmacoes, travas Arduino e UI reorganizada."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
A=(R/'arduino_cnc/arduino_cnc.ino').read_text(encoding='utf-8')
E=(R/'esp32cam/esp32cam.ino').read_text(encoding='utf-8')
J=(R/'notebook/painel.js').read_text(encoding='utf-8')
H=(R/'notebook/painel.html').read_text(encoding='utf-8')

class ConfirmacaoUARTTest(unittest.TestCase):
    def test_esp_retorna_sucesso_so_depois_pos_arduino(self):
        self.assertIn('telemetriaSeq++;',E)
        self.assertIn('esperarConfirmacaoUART(cmd,seqAntes)',E)
        self.assertIn('"Confirmado pelo Arduino: "+cmd',E)
        self.assertIn('Arduino nao confirmou',E)
        self.assertIn('telemetry_age_ms',E)
    def test_arduino_exige_home_drivers_jog_move(self):
        for cmd in ('JOG X ', 'JOG Y ', 'MOVE '):
            pos=A.index('if (cmd.startsWith("'+cmd+'"))')
            self.assertIn('!driversEnabled || !homedX || !homedY || isMoving()',A[pos:pos+350])
    def test_seguranca_stop_e_watchdog_photoack(self):
        self.assertIn('cmd == "STOP" || cmd == "JOGSTOP"',A)
        self.assertIn('JOG_WATCHDOG_MS = 1100UL',A)
        self.assertIn('if (photoPending)',A)
        self.assertIn('PHOTOACK',A)
        self.assertIn('server.on("/api/stop"',E)
    def test_painel_confirma_e_nao_duplicou(self):
        self.assertIn('confirmacaoNecessaria(cmd)',J)
        self.assertIn('await waitForState(confirmar',J)
        self.assertIn('HOME não confirmado pelo Arduino',J)
        self.assertEqual(H.count('data-action="auto-center"'),1)
        self.assertEqual(H.count('data-action="enable"'),1)
