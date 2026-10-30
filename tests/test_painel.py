"""Regressoes estaticas para garantir que os controles tem endpoints reais.
Esses testes nao executam Javascript no navegador nem simulam placas reais.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / 'notebook' / 'painel.html'
JS = ROOT / 'notebook' / 'painel.js'
CSS = ROOT / 'notebook' / 'painel.css'
ESP = ROOT / 'esp32cam' / 'esp32cam.ino'
PYTHON = ROOT / 'notebook' / 'controle.py'

class PainelTest(unittest.TestCase):
    def test_assets_presentes(self):
        html = PANEL.read_text(encoding='utf-8')
        self.assertIn('href="/painel.css', html)
        self.assertIn('src="/painel.js', html)
        self.assertGreater(CSS.stat().st_size, 5000)
        server = PYTHON.read_text(encoding='utf-8')
        self.assertIn("@app.get('/painel.css')", server)
        self.assertIn("@app.get('/painel.js')", server)

    def test_secoes(self):
        html = PANEL.read_text(encoding='utf-8')
        for view in ('dashboard', 'movement', 'route', 'camera', 'diagnostics'):
            self.assertIn('id="view-'+view+'"', html)
        for name in ('manual-photo', 'retry', 'recover', 'start', 'stop',
                     'save-route', 'import-route', 'export-route',
                     'home', 'define-zero', 'auto-center', 'confirm-physical-max',
                     'enable', 'disable'):
            self.assertIn('data-action="'+name+'"', html)

    def test_comandos_com_suporte_firmware(self):
        esp=ESP.read_text(encoding='utf-8')
        server=PYTHON.read_text(encoding='utf-8')
        self.assertIn('server.on("/api/manual-photo",HTTP_POST',esp)
        self.assertIn('if (cmd=="CENTER")',esp)
        self.assertIn('cmd.startsWith("MOVE X ")',esp)
        self.assertIn("('POST', '/api/manual-photo')",server)
        self.assertIn('fotografarEEnviar(id)', esp)

    def test_sem_atalho_de_photoack_pelo_painel(self):
        js=JS.read_text(encoding='utf-8')
        self.assertNotIn('/api/photoack',js)
        self.assertIn("send('/api/manual-photo'",js)
        self.assertIn("await send('/api/recover')",js)

if __name__ == '__main__':
    unittest.main()
