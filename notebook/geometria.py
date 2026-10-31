"""Medidas observadas e centro do canteiro ensinado por coordenadas X/Y.
Nao define curso seguro nem altera a calibracao de passos do Arduino.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

# Valores de referência do controlador; os limites definitivos continuam no firmware.
MAX_STEPS_X = 1640
MAX_STEPS_Y = 4550

MEDIDAS = {
    "canteiro_x_mm": 300,
    "canteiro_y_mm": 830,
    "travessa_x_mm_aprox": 390,
    "guia_y_mm_aprox": 1000,
    "carrinho_x_mm_aprox": 80,
    "centro_canteiro_desde_borda_x_mm": 150,
    "centro_canteiro_desde_borda_y_mm": 415,
}


def validar_centro(data, xmax=MAX_STEPS_X, ymax=MAX_STEPS_Y):
    if not isinstance(data, dict):
        raise ValueError('Centro precisa ser um objeto JSON')
    x, y = data.get('x_steps'), data.get('y_steps')
    if type(x) is not int or type(y) is not int:
        raise ValueError('X/Y devem ser passos inteiros')
    if not 0 <= x <= xmax or not 0 <= y <= ymax:
        raise ValueError('Centro fora dos limites de passos do controlador')
    return {"x_steps": x, "y_steps": y}


def carregar(path: Path):
    if not path.is_file():
        return {"medidas": dict(MEDIDAS), "centro": None}
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        centro = validar_centro(value['centro'])
        return {"medidas": dict(MEDIDAS), "centro": centro}
    except (OSError, ValueError, KeyError, TypeError):
        return {"medidas": dict(MEDIDAS), "centro": None}


def salvar(path: Path, centro):
    validado = validar_centro(centro)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as out:
        json.dump({'centro':validado}, out, ensure_ascii=False, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)
    return {"medidas": dict(MEDIDAS), "centro": validado}
