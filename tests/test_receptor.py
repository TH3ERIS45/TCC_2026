"""Testes isolados sem placas. Simulam recepcao e persistencia de fotografias.

Nao substituem compilacao e ensaios com UART/motores.
"""
import importlib.util
import io
import pathlib
import sys
import tempfile
import types
import unittest

from PIL import Image

# Em ambiente de teste sem Flask, fornecer mini-dublê dos decorators de rota.
if importlib.util.find_spec('flask') is None:
    fake = types.ModuleType('flask')
    class FakeApp:
        def __init__(self, name): self.config = {}
        def post(self, *_args, **_kwargs): return lambda f:f
        def get(self, *_args, **_kwargs): return lambda f:f
        def route(self, *_args, **_kwargs): return lambda f:f
    class FakeResponse:
        def __init__(self, data='', status=200, mimetype='text/plain', content_type=None, headers=None):
            self.data = data.encode() if isinstance(data,str) else data
            self.status_code=status
            self.content_type=content_type or mimetype
            self.headers=headers or {}
    fake.stream_with_context=lambda iterable: iterable
    fake.Flask=FakeApp
    fake.Response=FakeResponse
    fake.request=None
    fake.send_from_directory=lambda *a, **k: None
    fake.jsonify=lambda x:x
    sys.modules['flask']=fake

path=pathlib.Path(__file__).resolve().parents[1]/'notebook'/'controle.py'
spec=importlib.util.spec_from_file_location('controle',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture_jpeg():
    buf=io.BytesIO()
    Image.new('RGB',(600,480),color=(45,90,135)).save(buf,format='JPEG',quality=85)
    return buf.getvalue()


class ReceptorTest(unittest.TestCase):
    def test_salva_jpeg_valido_e_manifesto(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=pathlib.Path(dirname)
            saved=mod.salvar_foto(fixture_jpeg(),'120','300','500',d)
            self.assertEqual(saved.read_bytes(),fixture_jpeg())
            self.assertIn('120', (d/'manifesto.csv').read_text())

    def test_retry_photoack_nao_duplica_manifesto(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=pathlib.Path(dirname)
            img=fixture_jpeg()
            first=mod.salvar_foto(img,'180','30','50',d)
            second=mod.salvar_foto(img,'180','30','50',d)
            self.assertEqual(first,second)
            self.assertEqual(len((d/'manifesto.csv').read_text().splitlines()),2)
            self.assertEqual(len(list(d.glob('foto_*.jpg'))),1)

    def test_mesmo_id_outras_coordenadas_recusado(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=pathlib.Path(dirname)
            mod.salvar_foto(fixture_jpeg(),'180','30','50',d)
            with self.assertRaises(ValueError):
                mod.salvar_foto(fixture_jpeg(),'180','31','50',d)
            self.assertEqual(len(list(d.glob('foto_*.jpg'))),1)

    def test_retry_recompoe_indice_sem_duplicar_jpeg(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=pathlib.Path(dirname)
            mod.salvar_foto(fixture_jpeg(),'180','30','50',d)
            (d/'manifesto.csv').unlink()
            mod.salvar_foto(fixture_jpeg(),'180','30','50',d)
            self.assertEqual(len((d/'manifesto.csv').read_text().splitlines()),2)
            self.assertEqual(len(list(d.glob('foto_*.jpg'))),1)

    def test_rejeita_jpeg_incompleto(self):
        with tempfile.TemporaryDirectory() as dirname:
            with self.assertRaises(ValueError):
                mod.salvar_foto(b'not-jpeg','1','1','2',pathlib.Path(dirname))

    def test_rejeita_id_invalido(self):
        with tempfile.TemporaryDirectory() as dirname:
            for ident in ('', '0', '../7', '1000000000', '-1'):
                with self.assertRaises(ValueError):
                    mod.salvar_foto(fixture_jpeg(),ident,'1','2',pathlib.Path(dirname))

    def test_nao_libera_sem_gravacao(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=pathlib.Path(dirname)
            with self.assertRaises(ValueError):
                mod.salvar_foto(fixture_jpeg()[:-5],'400','1','2',d)
            self.assertEqual(list(d.glob('foto_*.jpg')),[])

    def test_todas_rotas_wifi_restritas(self):
        self.assertNotIn(('POST','/api/photoack'),mod.ALLOWED)
        self.assertIn(('POST','/api/start'),mod.ALLOWED)
        self.assertIn(('POST','/api/stop'),mod.ALLOWED)
        self.assertIn(('POST','/api/manual-photo'),mod.ALLOWED)

if __name__=='__main__':unittest.main()
