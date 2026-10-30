# -*- coding: utf-8 -*-
"""
Configuracao compartilhada do pytest.

Adiciona a raiz do projeto ao sys.path para que os testes importem
config.py e banco.py sem depender do diretorio de execucao.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))