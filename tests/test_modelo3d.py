"""Regressoes da terceira vista espacial, sem placas CNC."""
from pathlib import Path
import re
import unittest

BASE=Path(__file__).resolve().parents[1]

class Modelo3DTest(unittest.TestCase):
    def test_3_vistas_e_controles(self):
        s=(BASE/'notebook/painel.html').read_text()
        for mode in ('2d','iso','3d'):
            self.assertIn(f'data-map="{mode}"',s)
        self.assertIn('id="model3dCanvas"',s)
        self.assertIn('src="/modelo3d.js',s)
        for action in ('reset','zoom-in','zoom-out'):
            self.assertIn(f'data-3d="{action}"',s)
        ids=re.findall(r'\bid="([^"]+)"',s)
        self.assertEqual(len(ids),len(set(ids)),'IDs HTML duplicados')

    def test_modelo_observa_estado_e_nao_controla_motores(self):
        js=(BASE/'notebook/modelo3d.js').read_text()
        self.assertIn("s?.arduino",js)
        self.assertIn("route.forEach",js)
        self.assertIn("pointermove",js)
        self.assertIn("wheel",js)
        self.assertNotIn("fetch(",js)
        self.assertNotIn("PHOTOACK",js)
        self.assertIn("cam.forward",js)

    def test_painel_integra_e_servidor_entrega_modelo(self):
        js=(BASE/'notebook/painel.js').read_text()
        py=(BASE/'notebook/controle.py').read_text()
        self.assertIn("if(mapMode==='3d')",js)
        self.assertIn("window.Atlas3D.render(state, route, maxPreview?'max':null)",js)
        self.assertIn("@app.get('/modelo3d.js')",py)

    def test_modelo_dimensional_do_tcc(self):
        js=(BASE/'notebook/modelo3d.js').read_text()
        for item in ('baseX:440','baseY:1060','canteiroX:300','canteiroY:830','pilarH:300','pvcD:20','carroCamComp:80','pvcX:390','pvcY:1000'):
            self.assertIn(item,js)
        self.assertIn('cylinderFaces',js)
        self.assertIn('Modelo do TCC',js)
        self.assertNotIn('fetch(',js)
