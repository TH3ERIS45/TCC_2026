"""Credenciais locais do painel ATLAS CNC.

Arquivo armazenado apenas no notebook Debian; nunca entregue ao navegador.
NÃO é criptografia em repouso: chmod 0600 limita outros usuários locais.
"""
from __future__ import annotations

import getpass
import ipaddress
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

CONFIG_FILE = Path(__file__).resolve().parent / 'atlas_conexao.json'


def validar_alvo(esp: str) -> str:
    esp = esp.strip()
    if not esp or any(ch.isspace() for ch in esp) or len(esp) > 255:
        raise ValueError('Endereço ESP32 vazio ou inválido')
    if '/' in esp or '@' in esp or '?' in esp or '#' in esp or '\\' in esp:
        raise ValueError('Informe apenas IP ou hostname, sem URL/caminho')
    parsed = urlparse('http://' + esp)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError('Porta da ESP32 inválida') from exc
    if not parsed.hostname or parsed.path or (port not in (None, 80)):
        raise ValueError('ESP32: use somente IP/hostname, opcionalmente :80')
    host = parsed.hostname
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?', host):
            raise ValueError('Hostname inválido')
    return esp


def validar_chave(chave: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_.-]{12,64}', chave):
        raise ValueError('Chave: 12 a 64 caracteres (letras, números, _ . -)')
    return chave


def carregar_config(caminho: Path = CONFIG_FILE) -> dict:
    try:
        # Para reduzir acesso indevido: não usar arquivos com links simbólicos.
        if caminho.is_symlink():
            raise ValueError('Configuração não pode ser um link simbólico')
        obj = json.loads(caminho.read_text(encoding='utf-8'))
        return {'esp': validar_alvo(obj['esp']),
                'chave': validar_chave(obj['chave'])}
    except FileNotFoundError:
        return {}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as ex:
        raise ValueError(f'Configuração local inválida: {ex}') from ex


def salvar_config(esp: str, chave: str, caminho: Path = CONFIG_FILE) -> None:
    obj = {'esp': validar_alvo(esp), 'chave': validar_chave(chave)}
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.is_symlink():
        raise ValueError('Não é permitido gravar configuração em link simbólico')
    fd, temp = tempfile.mkstemp(prefix='.atlas_', suffix='.tmp', dir=caminho.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, caminho)
        os.chmod(caminho, 0o600)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def configurar_interativo(caminho: Path = CONFIG_FILE) -> None:
    antigo = carregar_config(caminho)
    padrao_esp = antigo.get('esp', '')
    esp = input('IP/hostname da ESP32-CAM' + (f' [{padrao_esp}]' if padrao_esp else '') + ': ').strip()
    esp = esp or padrao_esp
    chave = getpass.getpass('Chave API da ESP32-CAM (Enter preserva a anterior): ')
    chave = chave or antigo.get('chave', '')
    salvar_config(esp, chave, caminho)
    print('Conexão salva apenas neste notebook. Chave não será exibida.')
    print('Inicie o painel com: python controle.py')
