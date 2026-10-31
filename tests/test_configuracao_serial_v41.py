"""V4.1: rede/chave em NVS e notebook local, sem alterar o protocolo CNC."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'notebook'))
import conexao

S = (ROOT / 'esp32cam' / 'esp32cam.ino').read_text(encoding='utf-8')


class ConfiguracaoSerialTests(unittest.TestCase):
    def test_nvs_e_prompt_serial(self):
        for t in ('prefs.getString("wssid"', 'prefs.getString("wpass"',
                  'prefs.getString("nbook"', 'prefs.getString("apikey"',
                  'prefs.putString("wssid"', 'prefs.putString("wpass"',
                  'prefs.putString("nbook"', 'prefs.putString("apikey"',
                  'configurarPeloSerial()', 'BOOT_CONFIG_WINDOW_MS',
                  'comando=="CONFIG"', 'Serial.begin(115200)'):
            self.assertIn(t, S)
        for insecure in ('WIFI_SSID =', 'WIFI_PASSWORD =', 'API_KEY =', 'NOTEBOOK_IP ='):
            self.assertNotIn(insecure, S)

    def test_caminho_critico_nao_alterado(self):
        for trecho in ('fotoConfirmada(', 'PHOTOACK_TIMEOUT_MS = 18000UL',
                       'server.on("/api/start"', 'server.on("/api/manual-photo"',
                       'server.on("/api/recover"', 'fotoAckEnviado=true;',
                       'http.addHeader("X-Photo-X"',
                       'http.addHeader("X-Photo-Y"', 'WiFiServer videoServer(81)'):
            self.assertIn(trecho, S)

    def test_config_persistente_e_permissao(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'rede.json'
            self.assertEqual(conexao.carregar_config(path), {})
            conexao.salvar_config('192.168.2.169', 'MinhaChaveTCC2026', path)
            self.assertEqual(conexao.carregar_config(path), {
                'esp': '192.168.2.169', 'chave': 'MinhaChaveTCC2026'})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            conexao.salvar_config('atlas-cnc.local', 'OutraChave_2026', path)
            self.assertEqual(conexao.carregar_config(path)['esp'], 'atlas-cnc.local')

    def test_validacao_de_alvo_e_chave(self):
        for alvo in ('', 'http://exemplo.com', '192.168.1.3/xx', 'ip:12345', 'x@z'):
            with self.assertRaises(ValueError):
                conexao.validar_alvo(alvo)
        for chave in ('curta', 'chave com espacos', 'senha\nErrada'):
            with self.assertRaises(ValueError):
                conexao.validar_chave(chave)
        self.assertEqual(conexao.validar_alvo('10.72.206.165'), '10.72.206.165')


if __name__ == '__main__':
    unittest.main()
