"""Regressoes do gerador local de rotas. Node executa logica JS sem navegador/motores."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'notebook'/'planejador.js'
HTML=(ROOT/'notebook'/'painel.html').read_text(encoding='utf-8')
PANEL=(ROOT/'notebook'/'painel.js').read_text(encoding='utf-8')
SERVER=(ROOT/'notebook'/'controle.py').read_text(encoding='utf-8')

@unittest.skipUnless(shutil.which('node'), 'Node.js indisponivel')
class PlannerTests(unittest.TestCase):
    def run_js(self, script):
        p=subprocess.run(['node','-e', "const pl=require("+json.dumps(str(JS))+');'+script],capture_output=True,text=True,timeout=8)
        self.assertEqual(p.returncode,0,p.stderr)
        return json.loads(p.stdout)

    def config(self):
        return dict(limitX=1640,limitY=4550,x0=0,x1=1640,y0=0,y1=4550,footprintX=600,footprintY=1500,overlap=25)

    def test_seis_metodos_cobrem_grade_sem_repetir(self):
        data=self.run_js('''const base='''+json.dumps(self.config())+''';
        const all={};for(const mode of Object.keys(pl.MODES)){const r=pl.build({...base,mode});all[mode]=r.points;}
        process.stdout.write(JSON.stringify(all));''')
        for mode,points in data.items():
            self.assertTrue(1<=len(points)<=48,mode)
            self.assertEqual(len({(p['x'],p['y']) for p in points}),len(points),mode)
            self.assertTrue(all(0<=p['x']<=1640 and 0<=p['y']<=4550 and p['p'] for p in points),mode)
            if mode=='perimeter':
                self.assertEqual(len(points),18)
                self.assertTrue(all(p['x'] in (0,1640) or p['y'] in (0,4550) for p in points))
            else:
                self.assertEqual(len(points),30)
                self.assertEqual({(p['x'],p['y']) for p in points},{(p['x'],p['y']) for p in data['snakeRows']})

    def test_limite_48_protege_antes_do_envio(self):
        data=self.run_js('''try{pl.build({...'''+json.dumps(self.config())+''',mode:'snakeRows',footprintX:10,footprintY:10});
          process.stdout.write(JSON.stringify({failed:false}));}catch(e){process.stdout.write(JSON.stringify({failed:/48/.test(e.message)}));}''')
        self.assertTrue(data['failed'])

    def test_validacao_dos_limites(self):
        data=self.run_js('''const c='''+json.dumps(self.config())+''';const bad=[{x0:-1},{x1:1641},{y1:4551},{overlap:71},{footprintX:0},{x0:400,x1:200}];
          process.stdout.write(JSON.stringify(bad.map(b=>{try{pl.build({...c,mode:'spiral',...b});return false;}catch(e){return true;}})));''')
        self.assertEqual(data,[True]*6)

    def test_inverte_canto_inicial(self):
        data=self.run_js('''const c='''+json.dumps(self.config())+'''; const r=pl.build({...c,mode:'snakeRows',flipX:true,flipY:true});
          process.stdout.write(JSON.stringify(r.points[0]));''')
        self.assertEqual((data['x'],data['y']),(1640,4550))

    def test_painel_integra_previa_sem_movimento(self):
        self.assertIn('src="/planejador.js"',HTML)
        self.assertIn('data-action="planner-preview"',HTML)
        self.assertIn('data-action="planner-apply"',HTML)
        self.assertIn('plannerDraft.points.map',PANEL)
        self.assertIn("@app.get('/planejador.js')",SERVER)
        self.assertNotIn('fetch(',JS.read_text())
        self.assertNotIn('SCANMOVE',JS.read_text())

if __name__=='__main__':unittest.main()
