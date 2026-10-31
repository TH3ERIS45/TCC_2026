"""Medidas da visualização e da estrutura não redefinem os limites do firmware."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MedidasMontagemTest(unittest.TestCase):
    def test_modelo_visual_usa_medidas_documentadas(self):
        scene = (ROOT / 'notebook/modelo3d.js').read_text(encoding='utf-8')
        for item in (
            'baseX:440', 'baseY:1060', 'canteiroX:300',
            'canteiroY:830', 'pilarH:300', 'pvcD:20',
            'carroCamComp:80', 'pvcX:390', 'pvcY:1000',
        ):
            self.assertIn(item, scene)
        self.assertIn('CAD.cursoX', scene)
        self.assertIn('NAO limites reais de firmware', scene)

    def test_painel_distingue_medida_e_calibracao(self):
        html = (ROOT / 'notebook/painel.html').read_text(encoding='utf-8')
        self.assertIn('canteiro 30 × 83 cm', html)
        self.assertIn('5 passos/mm', html)
        self.assertIn('calibração física da lente', html)
        self.assertIn('geom-mark-center', html)
        self.assertIn('geom-go-center', html)

    def test_limites_reais_continuam_no_firmware(self):
        ino = (ROOT / 'arduino_cnc/arduino_cnc.ino').read_text(encoding='utf-8')
        self.assertIn('TRAVEL_X_MM = 328.0f', ino)
        self.assertIn('TRAVEL_Y_MM = 910.0f', ino)


if __name__ == '__main__':
    unittest.main()
