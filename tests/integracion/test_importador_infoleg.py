"""HU-005: importación masiva del catálogo nacional como metadatos.

El dataset es la única fuente del corpus que se importa entera sin descargar los
textos. Estas pruebas fijan las tres decisiones que el manual obliga a tomar:
`S/N` no es un número, los contadores no son aristas, y una clave canónica
repetida no identifica.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from sqlalchemy import Connection, text

from backend_normativo.catalogo.carga import cargar_catalogo
from backend_normativo.ingesta.importadores import infoleg
from backend_normativo.ingesta.importadores.infoleg import (
    COLUMNAS_ESPERADAS,
    ArchivoInseguro,
    FormaInesperada,
    ImportadorInfoleg,
)

pytestmark = pytest.mark.integracion


@pytest.fixture(autouse=True)
def _jurisdicciones(conexion: Connection) -> None:
    """El catálogo aporta las jurisdicciones y organismos base; la importación
    masiva se apoya en ellos, no los inventa."""
    cargar_catalogo(conexion)


def _zip(filas: list[dict], columnas: tuple[str, ...] = COLUMNAS_ESPERADAS) -> bytes:
    import csv

    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=columnas)
    escritor.writeheader()
    for fila in filas:
        escritor.writerow({c: fila.get(c, "") for c in columnas})
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("base-infoleg-normativa-nacional.csv", texto.getvalue())
    return memoria.getvalue()


def _fila(**kwargs) -> dict:
    base = {
        "id_norma": "1",
        "tipo_norma": "Ley",
        "numero_norma": "24714",
        "clase_norma": "",
        "organismo_origen": "HONORABLE CONGRESO DE LA NACION ARGENTINA",
        "fecha_sancion": "1996-10-02",
        "numero_boletin": "",
        "fecha_boletin": "1996-10-18",
        "pagina_boletin": "",
        "titulo_resumido": "REGIMEN DE ASIGNACIONES FAMILIARES",
        "titulo_sumario": "SEGURIDAD SOCIAL",
        "texto_resumido": "",
        "observaciones": "",
        "texto_original": "http://servicios.infoleg.gob.ar/x/norma.htm",
        "texto_actualizado": "",
        "modificada_por": "0",
        "modifica_a": "0",
    }
    base.update(kwargs)
    return base


def test_forma_inesperada_detiene_la_importacion(conexion: Connection) -> None:
    """Un dataset con otras columnas no se importa a ciegas: se detiene."""
    contenido = _zip([], columnas=("id_norma", "tipo_norma"))
    with pytest.raises(FormaInesperada, match="cambió de forma"):
        ImportadorInfoleg(conexion).importar(contenido)


def test_sn_no_es_numero_y_la_norma_se_conserva(conexion: Connection) -> None:
    """`S/N` es ausencia de número, no el número «SN»: queda NULL y la norma
    igual entra, identificada por su id oficial."""
    resultado = ImportadorInfoleg(conexion).importar(
        _zip([_fila(id_norma="183290", numero_norma="S/N", fecha_sancion="1853-11-09")])
    )
    assert resultado.sin_numero == 1
    assert resultado.normas_creadas == 1
    fila = conexion.execute(text("SELECT numero, anio FROM normas")).one()
    assert fila.numero is None
    assert fila.anio == 1853
    assert (
        conexion.execute(
            text("SELECT valor FROM norma_identificadores WHERE namespace = 'infoleg'")
        ).scalar_one()
        == "183290"
    )


def test_metadata_only_se_conserva(conexion: Connection) -> None:
    """Una norma sin URL de texto se carga igual: que exista y no tengamos su
    texto es información, descartarla haría creer que no existe."""
    resultado = ImportadorInfoleg(conexion).importar(
        _zip([_fila(id_norma="7", texto_original="", texto_actualizado="")])
    )
    assert resultado.sin_texto == 1
    assert resultado.normas_creadas == 1
    assert (
        conexion.execute(text("SELECT url_oficial FROM norma_identificadores")).scalar_one() is None
    )


def test_tipo_numerado_por_organismo_queda_con_identidad_incierta(
    conexion: Connection,
) -> None:
    """«Resolución 1/2023» no identifica una norma: hay una por organismo."""
    filas = [
        _fila(
            id_norma=str(100 + i),
            tipo_norma="Resolución",
            numero_norma="1",
            fecha_sancion="2023-01-05",
            organismo_origen=f"ORGANISMO {i}",
        )
        for i in range(3)
    ]
    resultado = ImportadorInfoleg(conexion).importar(_zip(filas))
    assert resultado.normas_creadas == 3
    assert resultado.sin_clave_canonica == 3
    inciertas = conexion.execute(
        text("SELECT count(*) FROM normas WHERE identidad_incierta")
    ).scalar_one()
    assert inciertas == 3


def test_homonimas_del_catalogo_no_se_reparten_la_clave(conexion: Connection) -> None:
    """Cuatro decretos «1/2001»: ninguno tiene mejor derecho a la clave canónica
    que los otros, así que ninguno se la queda. La ley con clave única sí."""
    filas = [
        _fila(id_norma=f"20{i}", tipo_norma="Decreto", numero_norma="1", fecha_sancion="2001-03-01")
        for i in range(1, 5)
    ] + [_fila(id_norma="900")]
    resultado = ImportadorInfoleg(conexion).importar(_zip(filas))
    assert resultado.homonimas == 4
    ciertas = conexion.execute(
        text("SELECT numero, tipo FROM normas WHERE identidad_incierta = false")
    ).all()
    assert [(f.numero, f.tipo) for f in ciertas] == [("24714", "LEY")]


def test_dos_corridas_son_idempotentes(conexion: Connection) -> None:
    """La segunda corrida no crea nada: el identificador oficial es la clave."""
    contenido = _zip([_fila(id_norma="1"), _fila(id_norma="2", numero_norma="27541")])
    primera = ImportadorInfoleg(conexion).importar(contenido)
    segunda = ImportadorInfoleg(conexion).importar(contenido)
    assert primera.normas_creadas == 2
    assert segunda.normas_creadas == 0
    assert segunda.normas_existentes == 2
    assert conexion.execute(text("SELECT count(*) FROM normas")).scalar_one() == 2


def test_los_contadores_no_se_convierten_en_relaciones(conexion: Connection) -> None:
    """`modificada_por = 3` dice cuántas, no cuáles: no hay grafo que construir."""
    resultado = ImportadorInfoleg(conexion).importar(
        _zip([_fila(modificada_por="3", modifica_a="2")])
    )
    assert resultado.contadores_conservados == 1
    assert conexion.execute(text("SELECT count(*) FROM relaciones_normativas")).scalar_one() == 0
    assert any("contadores, no aristas" in a for a in resultado.avisos)


def test_norma_conjunta_es_una_norma_con_incidencia(conexion: Connection) -> None:
    """El catálogo trae una fila por organismo firmante. Dos filas con el mismo
    id oficial son una norma conjunta, no dos normas: se carga una y los demás
    firmantes quedan en revisión, porque el modelo admite un solo emisor."""
    filas = [
        _fila(
            id_norma="235326",
            tipo_norma="Resolución",
            numero_norma="17",
            organismo_origen="SECRETARIA DE COMERCIO",
        ),
        _fila(
            id_norma="235326",
            tipo_norma="Resolución",
            numero_norma="17",
            organismo_origen="SECRETARIA DE AGRICULTURA Y GANADERIA",
        ),
    ]
    resultado = ImportadorInfoleg(conexion).importar(_zip(filas))
    assert resultado.normas_creadas == 1
    assert resultado.coemitidas == 1
    assert conexion.execute(text("SELECT count(*) FROM normas")).scalar_one() == 1
    incidencia = conexion.execute(
        text(
            "SELECT tipo, source_id, candidatos FROM incidencias_revision "
            " WHERE tipo = 'IDENTIDAD_AMBIGUA'"
        )
    ).one()
    assert incidencia.source_id == "F01"
    assert incidencia.candidatos["otros_firmantes"] == ["SECRETARIA DE AGRICULTURA Y GANADERIA"]
    assert incidencia.candidatos["emisor_cargado"] == "SECRETARIA DE COMERCIO"


def test_ninguna_norma_queda_sin_identificador(conexion: Connection) -> None:
    """Una norma cargada desde el catálogo sin su id oficial sería un duplicado
    invisible: no se puede volver a encontrar ni reconciliar en la próxima
    corrida. La gate de duplicados canónicos es cero."""
    filas = [_fila(id_norma="1"), _fila(id_norma="1", organismo_origen="OTRO"), _fila(id_norma="2")]
    ImportadorInfoleg(conexion).importar(_zip(filas))
    huerfanas = conexion.execute(
        text(
            "SELECT count(*) FROM normas n "
            " WHERE NOT EXISTS (SELECT 1 FROM norma_identificadores i WHERE i.norma_id = n.id)"
        )
    ).scalar_one()
    assert huerfanas == 0


def test_zip_con_ruta_fuera_del_arbol_se_rechaza(conexion: Connection) -> None:
    """No hay extracción a disco, pero un nombre así indica que el archivo no es
    el que se espera: se frena y se conserva el diagnóstico."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("../fuera.csv", "id_norma\n1\n")
    with pytest.raises(ArchivoInseguro, match="fuera del árbol"):
        ImportadorInfoleg(conexion).importar(memoria.getvalue())


def test_expansion_por_encima_del_presupuesto_se_rechaza(
    conexion: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Una bomba de descompresión no se procesa: el presupuesto se controla por
    tamaño declarado y también durante la lectura."""
    monkeypatch.setattr(infoleg, "PRESUPUESTO_EXPANSION", 128)
    contenido = _zip([_fila(id_norma=str(i)) for i in range(50)])
    with pytest.raises(ArchivoInseguro, match="presupuesto"):
        ImportadorInfoleg(conexion).importar(contenido)
