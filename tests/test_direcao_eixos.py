"""Regressao da convencao de sentido entre coordenadas logicas e maquete."""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1]


def test_polaridades_dir_alinham_sentido_logico_ao_modelo_3d():
    firmware = (BASE / "arduino_cnc/arduino_cnc.ino").read_text(encoding="utf-8")
    assert re.search(r"const uint8_t DIR_X_POS\s*=\s*HIGH\s*;", firmware)
    assert re.search(r"const uint8_t DIR_Y_POS\s*=\s*LOW\s*;", firmware)
    assert "const uint8_t DIR_X_NEG = (DIR_X_POS == HIGH) ? LOW : HIGH;" in firmware
    assert "const uint8_t DIR_Y_NEG = (DIR_Y_POS == HIGH) ? LOW : HIGH;" in firmware
    assert "X+ -> direita da máquina" in firmware
    assert "Y+ -> fundo da máquina (MAX Y)" in firmware
