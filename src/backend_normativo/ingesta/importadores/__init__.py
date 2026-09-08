"""Importadores de datasets públicos.

Un dataset no se recorre página por página: se descarga entero, se valida su
forma y se carga en bloque. Lo que estos módulos importan son metadatos, no
textos: el texto completo se prioriza por alcance funcional y por dependencias.
"""
