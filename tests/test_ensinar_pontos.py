"""Regressoes da UI de roteiro ensinado. Nao substitui teste no hardware."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
H=(ROOT/'notebook/painel.html').read_text(encoding='utf-8')
J=(ROOT/'notebook/painel.js').read_text(encoding='utf-8')

class EnsinarPontosTest(unittest.TestCase):
    def test_marca_sem_digitar_coordenadas(self):
        self.assertIn('id="teachMark"',H)
        self.assertIn('id="cameraTeachMark"',H)
        self.assertIn('case \'add-current\':await markCurrentPosition',J)
        self.assertIn('addPoint(v.x,v.y,photo)',J)
        self.assertIn('await settledPosition()',J)
        self.assertIn('route.some(p=>p.x===v.x && p.y===v.y)',J)
    def test_joystick_ensinar_e_camera(self):
        self.assertIn('id="teachDelta"',H)
        self.assertNotIn('id="cameraTeachDelta"',H)  # removido duplicado do painel
        self.assertGreaterEqual(H.count('data-jog="X:1"'),2)
        self.assertIn("await waitJogTarget(x,y",J)
        self.assertIn('teachMotionPending',J)
    def test_preserva_fluxo_e_firmware(self):
        self.assertIn('data-action="save-route"',H)
        self.assertIn('data-action="start"',H)
        self.assertIn('id="liveImage"',H)
        self.assertIn("routeCSV()",J)
        self.assertIn('data-action="stop"',H)

if __name__=='__main__':unittest.main()
