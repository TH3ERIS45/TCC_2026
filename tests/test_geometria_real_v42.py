"""Medidas físicas e ensino do centro sem alterar firmware ou escala de motores."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'notebook'
sys.path.insert(0, str(WEB))
import geometria

HTML = (WEB/'painel.html').read_text(encoding='utf-8')
JS = (WEB/'painel.js').read_text(encoding='utf-8')
MODEL = (WEB/'modelo3d.js').read_text(encoding='utf-8')
SERVER = (WEB/'controle.py').read_text(encoding='utf-8')

class MedidasReaisTest(unittest.TestCase):
    def test_actual_plot_dimensions(self):
        m=geometria.MEDIDAS
        self.assertEqual((m['canteiro_x_mm'],m['canteiro_y_mm']),(300,830))
        self.assertEqual((m['centro_canteiro_desde_borda_x_mm'],m['centro_canteiro_desde_borda_y_mm']),(150,415))
        self.assertEqual(m['travessa_x_mm_aprox'],390)
        self.assertEqual(m['guia_y_mm_aprox'],1000)
        self.assertEqual(m['carrinho_x_mm_aprox'],80)

    def test_persistent_center_preserves_real_mm(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'geometria_maquete.json'
            self.assertIsNone(geometria.carregar(path)['centro'])
            geometria.salvar(path,{'x_steps':540,'y_steps':2200})
            result=geometria.carregar(path)
            self.assertEqual(result['centro'],{'x_steps':540,'y_steps':2200})
            self.assertEqual(result['medidas']['canteiro_y_mm'],830)

    def test_reject_invalid_positions(self):
        for bad in [None,{'x_steps':1.0,'y_steps':2}, {'x_steps':-1,'y_steps':5},
                    {'x_steps':1641,'y_steps':5}, {'x_steps':1,'y_steps':4551},
                    {'x_steps':True,'y_steps':2}, {'x_steps':0,'y_steps':'2'}]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):geometria.validar_centro(bad)

    def test_interface_keeps_separate_center_buttons(self):
        self.assertIn('data-action="auto-center"',HTML)
        self.assertIn('data-action="geom-mark-center"',HTML)
        self.assertIn('data-action="geom-go-center"',HTML)
        self.assertIn('Centro mecânico',HTML)
        self.assertIn('Centro real das plantas',HTML)
        self.assertIn('geomReferenceCheck',HTML)

    def test_center_requires_homed_checked_fresh_state(self):
        start=JS.index('async function goPlotCenter(')
        stop=JS.index('function invalidateCenterCheck(',start)
        block=JS[start:stop]
        for fragment in ["requireReady(true)", "freshPosition()", "geomReferenceCheck", "fresh.xmax", "fresh.ymax", "fresh.home_x", "fresh.home_y", "fresh.enabled", "fresh.photo_lock", "fresh.stage", "command(`MOVE X ${x} Y ${y}`"]:
            self.assertIn(fragment,block)
        self.assertIn('async function settledPosition()',JS)

    def test_model_uses_real_bed_dimensions(self):
        for fragment in ['canteiroX:300,canteiroY:830','pvcY:1000,pvcX:390','carroCamComp:80','CAD.canteiroX,CAD.canteiroY']:
            self.assertIn(fragment,MODEL)
        self.assertIn("@app.route('/api/geometria'",SERVER)

if __name__=='__main__':unittest.main()
