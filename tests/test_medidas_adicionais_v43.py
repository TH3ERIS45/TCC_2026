"""Updated photographed dimensions must never change controller's movement limits."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class MedidasExtrasTest(unittest.TestCase):
    def test_scene_dimensions(self):
        scene=(ROOT/'notebook/modelo3d.js').read_text(encoding='utf-8')
        for item in ('baseX:740','baseY:1050','barraMovelX:580','canteiroX:300','canteiroY:830','carroCamComp:80'):
            self.assertIn(item,scene)
        self.assertIn('CAD.barraMovelX',scene)
        self.assertIn('NAO limites reais de firmware',scene)

    def test_panel_explains_limits_vs_structure(self):
        html=(ROOT/'notebook/painel.html').read_text(encoding='utf-8')
        self.assertIn('base 105 × 74 cm',html)
        self.assertIn('barra móvel 58 cm',html)
        self.assertIn('passos/mm',html)
        self.assertIn('geom-mark-center',html)
        self.assertIn('geom-go-center',html)

    def test_firmware_limits_not_redefined_by_geometry(self):
        ino=(ROOT/'arduino_cnc/arduino_cnc.ino').read_text(encoding='utf-8')
        self.assertIn('TRAVEL_X_MM = 328.0f',ino)
        self.assertIn('TRAVEL_Y_MM = 910.0f',ino)

if __name__=='__main__':unittest.main()
