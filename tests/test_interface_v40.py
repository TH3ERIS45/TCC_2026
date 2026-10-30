"""Verificacoes estaticas da organizacao UI v4.0, sem hardware conectado."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'notebook'
HTML=(WEB/'painel.html').read_text(encoding='utf-8')
JS=(WEB/'painel.js').read_text(encoding='utf-8')
CSS=(WEB/'painel.css').read_text(encoding='utf-8')

class InterfaceV40Test(unittest.TestCase):
 def test_two_modes_and_four_pages(self):
  for mode in ('simple','advanced'):
   self.assertIn('data-ui-switch="'+mode+'"',HTML)
  for view in ('dashboard','movement','route','camera'):
   self.assertIn('id="view-'+view+'"',HTML)
  self.assertIn('id="view-diagnostics"',HTML)
  self.assertIn('advanced-only',HTML)

 def test_live_camera_is_now_with_controls(self):
  m=re.search(r'<section[^>]+id="view-movement"(.*?)</section>\s*<section[^>]+id="view-route"',HTML,re.S)
  self.assertIsNotNone(m)
  self.assertIn('id="liveImage"',m.group(1))
  self.assertIn('data-jog="X:1"',m.group(1))
  self.assertIn('id="cameraTeachMark"',m.group(1))

 def test_results_preserve_mosaic(self):
  m=re.search(r'<section[^>]+id="view-camera"(.*?)</section>\s*<section[^>]+id="view-diagnostics"',HTML,re.S)
  self.assertIsNotNone(m)
  for id_ in ['mosaicGenerate','mosaicPreview','mosaicFine','photoGallery']:
   self.assertIn('id="'+id_+'"',m.group(1))

 def test_mode_only_changes_ui(self):
  start=JS.index('function setUiMode(')
  end=JS.index('function navigate(',start)
  block=JS[start:end]
  self.assertNotIn('await esp(',block)
  self.assertNotIn('await command(',block)
  self.assertIn('dataset.uiMode',block)
  self.assertIn('setPlannerExpanded(',block)
  self.assertIn('localStorage.setItem',block)

 def test_documentation_and_firmware(self):
  self.assertTrue((ROOT/'GUIA_RAPIDO_v4_0.md').is_file())
  self.assertTrue((ROOT/'arduino_cnc'/'arduino_cnc.ino').is_file())
  self.assertTrue((ROOT/'esp32cam'/'esp32cam.ino').is_file())
  self.assertIn('PHOTOACK', (ROOT/'esp32cam'/'esp32cam.ino').read_text())

 def test_route_save_and_stop_preserved(self):
  for action in ['save-route','start','stop','add-current','planner-preview','planner-apply','mosaic-generate']:
   self.assertIn('data-action="'+action+'"',HTML)
  self.assertIn('body[data-ui-mode="simple"] .advanced-only',CSS)

if __name__=='__main__':unittest.main()
