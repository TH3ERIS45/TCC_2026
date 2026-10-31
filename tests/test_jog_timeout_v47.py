from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "notebook/painel.js").read_text(encoding="utf-8")

class JogTimeoutV47(unittest.TestCase):
    def test_timeout_uses_firmware_slowest_speed_not_ui_value(self):
        block = JS.split("function jogMotionTimeoutMs", 1)[1].split("async function jogTeach", 1)[0]
        self.assertIn("slowestFirmwarePps=10", block)
        self.assertIn("distanceSteps)/slowestFirmwarePps", block)
        self.assertNotIn("speedPps", block)

    def test_teaching_jog_uses_safe_timeout_helper(self):
        block = JS.split("async function jogTeach", 1)[1].split("// JOG por pressao", 1)[0]
        self.assertIn("jogMotionTimeoutMs(realDistance)", block)

    def test_failure_reports_expected_and_observed_coordinates(self):
        block = JS.split("async function waitJogTarget", 1)[1].split("function jogMotionTimeoutMs", 1)[0]
        self.assertIn("Destino: Y=${x}, X=${y}", block)
        self.assertIn("Última posição informada: Y=${last.x}, X=${last.y}", block)

if __name__ == "__main__":
    unittest.main()
