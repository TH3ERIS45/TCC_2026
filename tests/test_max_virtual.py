from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'notebook/painel.html').read_text(encoding='utf-8')
JS=(ROOT/'notebook/painel.js').read_text(encoding='utf-8')
MODEL=(ROOT/'notebook/modelo3d.js').read_text(encoding='utf-8')

class MaxVirtualTest(unittest.TestCase):
    def test_botoes_em_visao_geral_e_movimentacao(self):
        for name in ('preview-max','preview-real','confirm-physical-max','auto-center'):
            self.assertIn(f'data-action="{name}"',HTML)
        self.assertIn('X máximo / Y máximo',HTML)
        self.assertIn('NÃO movimenta os eixos',HTML)

    def test_preview_nao_envia_telemetria_falsa(self):
        section=JS.split("case 'preview-max':{",1)[1].split("case 'preview-real':{",1)[0]
        self.assertIn('maxPreview=true',section)
        self.assertIn("navigate('dashboard')",section)
        self.assertNotIn("command(",section)
        self.assertNotIn("send(",section)
        self.assertNotIn("SETPOS",section)
        self.assertIn("maxPreview?'max':null",JS)
        self.assertIn("visualMax=preview==='max'",MODEL)
        self.assertIn('A máquina física não se moveu',MODEL)

    def test_referencia_so_por_setpos_e_home(self):
        section=JS.split("case 'confirm-physical-max':{",1)[1].split("case 'home':",1)[0]
        self.assertIn("!isIdle()",section)
        self.assertIn("if(before.enabled)",section)
        self.assertIn('confirm(`REFERÊNCIA MAX SEM SENSORES',section)
        self.assertIn('command(`SETPOS X ${mx} Y ${my}`)',section)
        self.assertIn("await command('HOME')",section)
        self.assertIn('waitForState(',section)
        self.assertNotIn("command('CENTER')",section)
        self.assertNotIn('command(`MOVE',section)

    def test_center_so_apos_confirmacao_manual(self):
        section=JS.split("case 'auto-center':{",1)[1].split("case 'home-x'",1)[0]
        self.assertIn('requireReady(true)',section)
        self.assertIn("await command('CENTER')",section)
        self.assertIn('A referência física escolhida',section)

    def test_firmware_incluido_preservado(self):
        ino=(ROOT/'arduino_cnc/arduino_cnc.ino').read_text(encoding='utf-8')
        esp=(ROOT/'esp32cam/esp32cam.ino').read_text(encoding='utf-8')
        self.assertIn('if (cmd.startsWith("SETPOS "))',ino)
        self.assertIn('if (cmd == "CENTER")',ino)
        self.assertIn('if (cmd.startsWith("SETPOS X "))',esp)
        self.assertIn('ESP32-2.7-PHOTOACK-DIAG',esp)

if __name__=='__main__':unittest.main()
