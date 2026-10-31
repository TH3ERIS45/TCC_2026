"""Testa rotas Flask e geração de mosaico, incluindo conclusão automática."""
import csv
import importlib.util
import io
import pathlib
import tempfile
import unittest
from unittest.mock import patch

try:
    from PIL import Image
    from flask import Flask
except ImportError:
    raise unittest.SkipTest('Dependências do painel não instaladas')

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('controle_mosaic_test',ROOT/'notebook'/'controle.py')
controle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(controle)


def jpeg():
    out=io.BytesIO()
    Image.new('RGB',(120,90),(54,155,65)).save(out,'JPEG',quality=85)
    return out.getvalue()


class MosaicAPITest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.orig=controle.FOTOS
        self.addCleanup(lambda: setattr(controle,'FOTOS',self.orig))
        controle.FOTOS=pathlib.Path(self.tmp.name)
        controle.TOKEN='chave-teste-segura'
        self.client=controle.app.test_client()

    def one_photo(self,pid=1,x=50,y=50):
        return self.client.post('/api/photos/receive',data=jpeg(),headers={
            'X-Photo-Token':controle.TOKEN,'X-Photo-Id':str(pid),'X-Photo-X':str(x),'X-Photo-Y':str(y)})

    def test_config_upload_generate_file_download(self):
        self.assertEqual(self.one_photo().status_code,200)
        cfg=self.client.get('/api/mosaico/config').json
        cfg['footprint_x']=100;cfg['footprint_y']=100
        self.assertEqual(self.client.post('/api/mosaico/config',json=cfg).status_code,200)
        bad={**cfg,'footprint_x':-1}
        self.assertEqual(self.client.post('/api/mosaico/config',json=bad).status_code,400)
        resp=self.client.post('/api/mosaico/gerar',json={'source':'recentes'})
        self.assertEqual(resp.status_code,200,resp.text)
        meta=resp.json
        self.assertEqual(meta['photos'],1)
        res=self.client.get('/mosaicos/'+meta['filename'])
        self.assertEqual(res.status_code,200)
        self.assertIn('image/jpeg',res.content_type)
        self.assertEqual(self.client.get('/mosaicos/../../etc/passwd').status_code,404)
        self.assertEqual(len(self.client.get('/api/mosaico/status').json['mosaics']),1)

    def test_auto_completion_only_after_all_points(self):
        self.assertEqual(self.one_photo().status_code,200)
        controle.save_session({'state':'running','offset':0,'result':None,'error':''})
        cfg=controle.mosaico.DEFAULT_SETTINGS.copy()
        cfg.update(footprint_x=100,footprint_y=100)
        controle.mosaico.salvar_json_atomico(controle.FOTOS/'mosaicos'/'config.json',cfg)
        class FakeResponse:
            status_code=200
            def json(self):return {'active':False,'moving':False,'stage':'PARADO','total':1,'point':1}
        with patch.object(controle.time,'sleep',lambda _:None),patch.object(controle.requests,'get',return_value=FakeResponse()):
            controle.watch_mosaic_session()
        ses=controle.mosaic_session()
        self.assertEqual(ses['state'],'completed')
        self.assertEqual(ses['result']['photos'],1)

    def test_generate_rejected_while_route_active(self):
        self.one_photo()
        controle.save_session({'state':'running','offset':0,'result':None,'error':''})
        r=self.client.post('/api/mosaico/gerar',json={'source':'recentes'})
        self.assertEqual(r.status_code,422)
        self.assertIn('Aguarde',r.json['error'])

if __name__=='__main__':unittest.main()
