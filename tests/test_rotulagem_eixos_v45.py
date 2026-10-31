from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'notebook' / 'painel.html').read_text(encoding='utf-8')
JS = (ROOT / 'notebook' / 'painel.js').read_text(encoding='utf-8')
MODEL3D = (ROOT / 'notebook' / 'modelo3d.js').read_text(encoding='utf-8')
ARDUINO = (ROOT / 'arduino_cnc' / 'arduino_cnc.ino').read_text(encoding='utf-8')


class TestAxisDisplayLabelsV45(unittest.TestCase):
    def test_dashboard_labels_are_swapped_without_changing_data_bindings(self):
        self.assertIn('<b class="axis-letter y">Y</b><span>Transversal</span>', HTML)
        self.assertIn('<b class="axis-letter x">X</b><span>Longitudinal</span>', HTML)
        self.assertIn('id="dashX"', HTML)
        self.assertIn('id="dashY"', HTML)
        self.assertIn('setText(\'dashX\',arduino?state.x:', JS)
        self.assertIn('setText(\'dashY\',arduino?state.y:', JS)

    def test_jog_visible_text_swapped_but_controller_channels_unchanged(self):
        self.assertIn('data-jog="Y:1">X +', HTML)
        self.assertIn('data-jog="X:-1"><span>←</span> Y −', HTML)
        self.assertIn('data-jog="X:1">Y +', HTML)
        self.assertIn('data-jog="Y:-1">X −', HTML)
        self.assertIn('`JOGSTART ${axis} ${dir}`', JS)
        self.assertIn('`JOG ${axis} ${direction*delta}`', JS)

    def test_manual_home_labels_do_not_change_firmware_commands(self):
        self.assertIn('data-action="home-x">⌖ HOME Y', HTML)
        self.assertIn('data-action="home-y">⌖ HOME X', HTML)
        self.assertIn("await command('HOME X')", JS)
        self.assertIn("await command('HOME Y')", JS)

    def test_3d_axis_annotations_follow_the_new_display_names(self):
        self.assertIn('FUNDO · MAX X', MODEL3D)
        self.assertIn('FRENTE · HOME X=0', MODEL3D)
        self.assertIn("'Y +'", MODEL3D)
        self.assertIn("'X + (FUNDO)'", MODEL3D)

    def test_firmware_protocol_constants_remain(self):
        self.assertIn('const long MAX_X =', ARDUINO)
        self.assertIn('const long MAX_Y =', ARDUINO)
        self.assertIn('const uint8_t DIR_X_POS = HIGH;', ARDUINO)
        self.assertIn('const uint8_t DIR_Y_POS = LOW;', ARDUINO)


if __name__ == '__main__':
    unittest.main()
