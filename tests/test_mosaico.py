"""Testes offline da geração de mosaicos, sem Arduino ou ESP32."""
import csv
import importlib.util
import pathlib
import random
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

P = pathlib.Path(__file__).resolve().parents[1]
S = P / 'notebook' / 'mosaico.py'
spec = importlib.util.spec_from_file_location('mosaico_real', S)
mosaic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mosaic)


def criar(pasta, items):
    pasta=pathlib.Path(pasta)
    with (pasta/'manifesto.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['photo_id','filename','x_steps','y_steps','received_at'])
        for i,(x,y,color) in enumerate(items,1):
            name=f'foto_{i:09d}_X{x}_Y{y}.jpg'
            Image.new('RGB',(120,90),color).save(pasta/name,quality=95)
            w.writerow([i,name,x,y,'2026-10-21T14:30:00'])


class MosaicTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        self.config={**mosaic.DEFAULT_SETTINGS,'footprint_x':120,'footprint_y':90}

    def test_creates_positions_and_preserves_original(self):
        criar(self.root,[(60,45,(255,0,0)),(180,45,(0,255,0)),(60,135,(0,0,255)),(180,135,(255,255,0))])
        original=(self.root/'foto_000000001_X60_Y45.jpg').read_bytes()
        meta=mosaic.gerar_mosaico(self.root,self.config)
        self.assertEqual((meta['width'],meta['height']),(240,180))
        self.assertEqual(meta['photos'],4)
        with Image.open(self.root/'mosaicos'/meta['filename']) as out:
            pixels=[out.getpixel((60,45)),out.getpixel((180,45)),out.getpixel((60,135)),out.getpixel((180,135))]
        self.assertGreater(pixels[0][0],200)
        self.assertGreater(pixels[1][1],200)
        self.assertGreater(pixels[2][2],200)
        self.assertGreater(pixels[3][0],200)
        self.assertEqual((self.root/'foto_000000001_X60_Y45.jpg').read_bytes(),original)
        self.assertTrue((self.root/'mosaicos'/(meta['filename']+'.json')).exists())

    def test_offset_separates_sessions(self):
        criar(self.root,[(60,45,(255,0,0))])
        offset=(self.root/'manifesto.csv').stat().st_size
        with (self.root/'manifesto.csv').open('a',newline='') as f:
            csv.writer(f).writerow([2,'foto_000000002_X120_Y45.jpg',120,45,'now'])
        Image.new('RGB',(120,90),(0,255,0)).save(self.root/'foto_000000002_X120_Y45.jpg')
        meta=mosaic.gerar_mosaico(self.root,self.config,offset=offset)
        self.assertEqual(meta['photos'],1)
        self.assertEqual(meta['coordinates']['min_x'],120)

    def test_deduplicates_by_position_newest(self):
        criar(self.root,[(60,45,(255,0,0)),(60,45,(0,255,0))])
        meta=mosaic.gerar_mosaico(self.root,self.config)
        self.assertEqual(meta['photos'],1)
        with Image.open(self.root/'mosaicos'/meta['filename']) as img:
            self.assertGreater(img.getpixel((60,45))[1],220)

    def test_invalid_coverage_and_missing_photos(self):
        criar(self.root,[(60,45,(255,0,0))])
        for bad in (0,-1,50001,1.5):
            with self.assertRaises(ValueError):
                mosaic.gerar_mosaico(self.root,{**self.config,'footprint_x':bad})
        (self.root/'foto_000000001_X60_Y45.jpg').unlink()
        with self.assertRaises(ValueError):
            mosaic.gerar_mosaico(self.root,self.config)

    def test_cap_enforced_and_resize(self):
        criar(self.root,[(0,0,(255,0,0)),(8000,6000,(0,0,255))])
        meta=mosaic.gerar_mosaico(self.root,self.config)
        self.assertLessEqual(meta['width']*meta['height'],mosaic.MAX_PIXELS)

    def test_old_settings_remain_valid(self):
        cfg=self.config.copy()
        cfg.pop('encaixe_fino')
        self.assertTrue(mosaic.validar_config(cfg)['encaixe_fino'])
        with self.assertRaises(ValueError):
            mosaic.validar_config({**cfg,'encaixe_fino':'sim'})

    def test_alignment_fixes_small_offset_using_shared_details(self):
        # Duas fotos com 12 pixels de erro na posição X prevista.
        rng=random.Random(2)
        world=Image.new('RGB',(500,310),(97,78,47))
        dr=ImageDraw.Draw(world)
        for _ in range(1400):
            x=rng.randrange(500);y=rng.randrange(310);r=rng.randrange(2,8)
            color=(rng.randrange(10,80),rng.randrange(50,185),rng.randrange(15,85))
            dr.ellipse((x-r,y-r,x+r,y+r),fill=color)
        photos=[(120,world.crop((0,0,240,180))),(270,world.crop((138,0,378,180)))]
        with (self.root/'manifesto.csv').open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['photo_id','filename','x_steps','y_steps','received_at'])
            for i,(x,img) in enumerate(photos,1):
                name=f'foto_{i:09d}_X{x}_Y90.jpg'
                img.save(self.root/name,quality=95)
                writer.writerow([i,name,x,90,'now'])
        cfg={**self.config,'footprint_x':240,'footprint_y':180}
        try:
            import cv2
        except ImportError:
            self.skipTest('OpenCV não instalado no ambiente de testes')
        tuned=mosaic.gerar_mosaico(self.root,cfg)
        basic=mosaic.gerar_mosaico(self.root,{**cfg,'encaixe_fino':False})
        self.assertEqual(tuned['alignment']['adjusted'],1)
        self.assertEqual(tuned['width'],378)
        self.assertEqual(basic['width'],390)
        self.assertEqual(basic['alignment']['adjusted'],0)

    def test_no_feature_overlap_falls_back_to_coordinates(self):
        criar(self.root,[(60,45,(255,0,0)),(130,45,(0,255,0))])
        cfg={**self.config,'footprint_x':120,'footprint_y':90}
        meta=mosaic.gerar_mosaico(self.root,cfg)
        self.assertEqual(meta['alignment']['adjusted'],0)
        self.assertEqual(meta['alignment']['fallback_xy'],1)
        self.assertEqual(meta['width'],190)

    def test_mosaic_kit_in_panel(self):
        html=(P/'notebook'/'painel.html').read_text()
        js=(P/'notebook'/'painel.js').read_text()
        py=(P/'notebook'/'controle.py').read_text()
        for text in ('mosaicFootX','mosaicFootY','mosaicGenerate','mosaicPreview'):
            self.assertIn(text,html)
        self.assertIn("case 'mosaic-generate'",js)
        self.assertIn('start_mosaic_session()',py)
        self.assertIn("target == '/api/start'",py)
        self.assertIn('watch_mosaic_session',py)


if __name__=='__main__':unittest.main()
