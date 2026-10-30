from pathlib import Path
import unittest
S=(Path(__file__).resolve().parents[1]/'esp32cam'/'esp32cam.ino').read_text()
class Diagnostico(unittest.TestCase):
    def test_versao_e_diagnosticos(self):
        for s in ('ESP32-2.7-PHOTOACK-DIAG','fw_version','photo_ack_tries','arduino_photo_state','pending_id','uart_last'):
            self.assertIn(s,S)
    def test_retransmissao_segura(self):
        for s in ('fotoLock && pidArduino == pendenteId','now-lastStatusMs<1800','fotoAckTentativas<6','PHOTOACK_TIMEOUT_MS = 18000UL','enviarArduino("STATUS")'):
            self.assertIn(s,S)
    def test_timeout_depois_do_upload_tem_relogio_atualizado(self):
        inicio=S.index('if(stage==TAKE_PHOTO)')
        fim=S.index('if(stage==WAIT_PHOTOACK && fotoAckEnviado)',inicio)
        trecho=S[inicio:fim]
        self.assertIn('now = millis();',trecho)
        self.assertLess(trecho.index('if(fotografarEEnviar(pendenteId))'),trecho.index('now = millis();'))
    def test_somente_apos_jpeg(self):
        a=S.index('if(stage==TAKE_PHOTO)'); b=S.index('if(stage==WAIT_PHOTOACK && fotoAckEnviado)',a)
        s=S[a:b];self.assertLess(s.index('if(fotografarEEnviar(pendenteId))'),s.index('enviarArduino("PHOTOACK "'))
if __name__=='__main__':unittest.main()
