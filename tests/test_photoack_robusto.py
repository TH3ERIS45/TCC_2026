from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'esp32cam'/'esp32cam.ino').read_text(encoding='utf-8')

class ConfirmacaoRobusta(unittest.TestCase):
    def test_confirmacao_textual_e_telemetria(self):
        self.assertIn('fotoConfirmada(id, "resposta UART")', SRC)
        self.assertIn('fotoConfirmada(pendenteId, "telemetria")', SRC)
        for check in ['campo(line, "PROTO") == "2"', 'campo(line, "PHOTO") == "READY"', 'pidArduino == 0', 'eixoX == ultimaFotoX && eixoY == ultimaFotoY', 'homedX && homedY && enabled']:
            self.assertIn(check, SRC)

    def test_nao_avanca_antes_de_salvar_jpeg(self):
        start=SRC.index('if(stage==TAKE_PHOTO) {')
        end=SRC.index('if(stage==WAIT_PHOTOACK',start)
        section=SRC[start:end]
        self.assertIn('if(fotografarEEnviar(pendenteId))',section)
        self.assertIn('fotoAckEnviado=true;',section)
        self.assertIn('enviarArduino("PHOTOACK " + String(pendenteId))',section)
        self.assertLess(section.index('if(fotografarEEnviar(pendenteId))'), section.index('fotoAckEnviado=true;'))

    def test_foto_confirmada_valida_etapa_e_id(self):
        section=SRC[SRC.index('void fotoConfirmada('):SRC.index('void tratarLinha(')]
        self.assertIn('stage != WAIT_PHOTOACK || !fotoAckEnviado || id != pendenteId',section)
        self.assertIn('indice++;',section)
        self.assertIn('stage = IDLE;',section)

if __name__=='__main__': unittest.main()
