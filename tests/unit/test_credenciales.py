"""La credencial dice quién es, qué puede y hasta cuándo (P-017 criterio 1)."""

from __future__ import annotations

import datetime as dt

import pytest

from backend_normativo.seguridad.credenciales import (
    DURACION_MAXIMA,
    IDENTIDAD_CREDENCIAL,
    ROL_PUBLICADOR,
    ROL_REVISOR,
    CredencialInvalida,
    emitir,
    verificar,
)

SECRETO = b"secreto-de-prueba-que-no-vive-en-produccion"


def _emitir(actor="curacion_juridica:persona", roles=None, dias=30, ahora=None):
    return emitir(
        actor,
        roles or {ROL_REVISOR},
        duracion=dt.timedelta(days=dias),
        secreto_bytes=SECRETO,
        ahora=ahora,
    )


def test_el_actor_sale_de_la_credencial_y_no_de_quien_llama() -> None:
    token, _ = _emitir()
    identidad = verificar(token, secreto_bytes=SECRETO)
    assert identidad.actor == "curacion_juridica:persona"
    assert identidad.procedencia == IDENTIDAD_CREDENCIAL
    assert identidad.verificada


def test_los_roles_vienen_adentro_y_limitan() -> None:
    token, _ = _emitir(roles={ROL_REVISOR})
    identidad = verificar(token, secreto_bytes=SECRETO)
    assert identidad.puede(ROL_REVISOR)
    assert not identidad.puede(ROL_PUBLICADOR), "revisar y publicar son decisiones distintas"


def test_una_credencial_alterada_no_verifica() -> None:
    """Cambiarle el actor al payload no sirve sin el secreto."""
    token, _ = _emitir()
    prefijo, cuerpo, firma = token.split(".")
    alterado = f"{prefijo}.{cuerpo[:-4]}AAAA.{firma}"
    with pytest.raises(CredencialInvalida, match=r"alterada|no se puede leer"):
        verificar(alterado, secreto_bytes=SECRETO)


def test_otra_firma_no_sirve() -> None:
    token, _ = _emitir()
    with pytest.raises(CredencialInvalida, match="firma no corresponde"):
        verificar(token, secreto_bytes=b"otro-secreto-distinto")


def test_una_credencial_vencida_no_sirve() -> None:
    ayer = dt.datetime.now(dt.UTC) - dt.timedelta(days=40)
    token, _ = _emitir(dias=30, ahora=ayer)
    with pytest.raises(CredencialInvalida, match="venció"):
        verificar(token, secreto_bytes=SECRETO)


def test_no_se_emiten_credenciales_eternas() -> None:
    with pytest.raises(CredencialInvalida, match="máximo"):
        _emitir(dias=DURACION_MAXIMA.days + 1)


def test_una_credencial_sin_roles_no_autoriza_nada() -> None:
    # Sin el ayudante: `roles or {...}` convertiría el conjunto vacío en el
    # valor por omisión y la prueba pasaría sin probar nada.
    with pytest.raises(CredencialInvalida, match="sin roles"):
        emitir("alguien", set(), duracion=dt.timedelta(days=1), secreto_bytes=SECRETO)


def test_una_credencial_sin_actor_no_identifica_a_nadie() -> None:
    with pytest.raises(CredencialInvalida, match="sin actor"):
        _emitir(actor="   ")


def test_sin_secreto_configurado_no_se_verifica_nada(monkeypatch) -> None:
    """Un secreto por omisión haría que una credencial de cualquier máquina valga acá."""
    monkeypatch.delenv("BN_CREDENCIAL_SECRETO", raising=False)
    with pytest.raises(CredencialInvalida, match="BN_CREDENCIAL_SECRETO"):
        verificar("bn1.abc.def")


def test_cada_credencial_tiene_su_identificador() -> None:
    uno, ident_uno = _emitir()
    otro, ident_otro = _emitir()
    assert uno != otro
    assert ident_uno.jti != ident_otro.jti, "sin id propio no se puede revocar una sola"
