"""Segmentación de texto normativo en unidades documentales.

El objetivo no es "partir el texto en artículos": es no perder la jerarquía ni
confundir un artículo dispositivo con el texto de otro artículo citado dentro de
él. Esa confusión es la que hace que una reforma se aplique sobre el artículo
equivocado.

Señales que usa para decidir que un marcador de artículo **no** es una raíz:

1. El artículo en curso contiene un verbo de sustitución o incorporación
   ("sustitúyese", "incorpórase", "reemplázase") antes del marcador nuevo.
2. La numeración no avanza: un artículo con número menor o igual al último
   dispositivo no puede abrir una unidad nueva en el mismo nivel.
3. El párrafo viene entrecomillado, que es como suele transcribirse el texto
   sustituido.

Cuando las señales se contradicen, la unidad queda marcada como ambigua y el
segmentador lo informa: la revisión humana decide, el parser no adivina.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from backend_normativo.db.vocabularios import RolContenido, TipoUnidad

# --- Expresiones de estructura ----------------------------------------------
# `ARTICULO 1°`, `Art. 14 bis`, `ARTÍCULO 26.-`. El ordinal y la puntuación
# varían mucho entre boletines, así que se aceptan todas las variantes.
ORDINALES = r"bis|ter|quater|quáter|quinquies|sexies|septies|octies|nonies|decies"

RE_ARTICULO = re.compile(
    r"^\s*(?:ART[IÍ]CULO|ARTICULO|ART\.?)\s*"
    r"(?:N[°º.]?\s*)?"
    r"(\d+)\s*"
    r"(?:[°ºª]\s*)?"
    r"(" + ORDINALES + r")?"
    r"\s*[.\-–—:)]*\s*",
    re.IGNORECASE,
)

RE_TITULO = re.compile(r"^\s*T[IÍ]TULO\s+([IVXLCDM\d]+)\b", re.IGNORECASE)
RE_CAPITULO = re.compile(r"^\s*CAP[IÍ]TULO\s+([IVXLCDM\d]+)\b", re.IGNORECASE)
RE_SECCION = re.compile(r"^\s*SECCI[OÓ]N\s+([IVXLCDM\d]+)\b", re.IGNORECASE)
RE_LIBRO = re.compile(r"^\s*LIBRO\s+([IVXLCDM\d]+)\b", re.IGNORECASE)
RE_ANEXO = re.compile(r"^\s*ANEXO\s*([IVXLCDM\d]*)\b", re.IGNORECASE)
RE_TRANSITORIA = re.compile(
    r"^\s*(?:DISPOSICI[OÓ]N(?:ES)?\s+)?(?:TRANSITORIA|COMPLEMENTARIA)S?\b", re.IGNORECASE
)
RE_INCISO = re.compile(r"^\s*([a-z]|\d{1,2})\s*[).]\s+", re.IGNORECASE)
RE_VISTO = re.compile(r"^\s*VISTO\b", re.IGNORECASE)
RE_CONSIDERANDO = re.compile(r"^\s*CONSIDERANDO\b", re.IGNORECASE)

# Verbos que introducen texto de otra norma dentro del artículo en curso.
# Los boletines usan enclíticos en singular y plural: "sustitúyese",
# "sustitúyense", "sustitúyanse". Perder una variante hace que el texto
# transcripto se tome por articulado nuevo.
RE_VERBO_SUSTITUCION = re.compile(
    r"\b(?:"
    r"sust[ií]t[uú]y[ae]n?se|"
    r"reempl[aá]z[ae]n?se|"
    r"incorp[oó]r[ae]n?se|"
    r"d[eé]j[ae]n?se\s+redactad[oa]s?|"
    r"modif[ií]c[ae]n?se"
    r")\b",
    re.IGNORECASE,
)

# Números de artículo que el texto dice estar sustituyendo: "Sustitúyese el
# artículo 10 de la Ordenanza N° 43.478". Cuando el marcador siguiente coincide
# con uno de estos, no hay ambigüedad que informar.
RE_ARTICULO_REFERIDO = re.compile(
    r"\b(?:art[ií]culos?|arts?\.?)\s+"
    r"(\d+(?:\s*(?:" + ORDINALES + r"))?(?:\s*(?:,|y|e)\s*\d+(?:\s*(?:" + ORDINALES + r"))?)*)",
    re.IGNORECASE,
)


def numeros_referidos(texto: str) -> set[int]:
    """Artículos que un texto declara sustituir o incorporar."""
    numeros: set[int] = set()
    for coincidencia in RE_ARTICULO_REFERIDO.finditer(texto):
        numeros.update(int(n) for n in re.findall(r"\d+", coincidencia.group(1)))
    return numeros


# Nota editorial del boletín. Lleva información de vigencia pero no es texto
# dispositivo: se conserva aparte para no confundirla con la norma.
RE_NOTA = re.compile(r"^\s*\(?\s*Nota\s+Infoleg\b", re.IGNORECASE)

NIVELES_JERARQUIA: dict[TipoUnidad, int] = {
    TipoUnidad.LIBRO: 1,
    TipoUnidad.TITULO: 2,
    TipoUnidad.CAPITULO: 3,
    TipoUnidad.SECCION: 4,
    TipoUnidad.ANEXO: 1,
}


@dataclass
class UnidadSegmentada:
    tipo: TipoUnidad
    texto: str
    orden: int
    rol_contenido: RolContenido = RolContenido.DISPOSITIVO
    numero: str | None = None
    sufijo: str | None = None
    rotulo: str | None = None
    ruta: str = ""
    inicio: int | None = None
    fin: int | None = None
    pagina_desde: int | None = None
    pagina_hasta: int | None = None
    padre_indice: int | None = None
    ambigua: bool = False
    motivo_ambiguedad: str | None = None

    @property
    def numero_completo(self) -> str | None:
        if self.numero is None:
            return None
        return f"{self.numero}{'-' + self.sufijo if self.sufijo else ''}"


@dataclass
class Parrafo:
    """Fragmento de texto con su lugar en el documento original."""

    texto: str
    inicio: int
    fin: int
    pagina: int | None = None
    # Dónde termina, que puede no ser dónde empieza: un párrafo de PDF cortado en
    # renglones cruza el corte de página, y una cita que dice «página 4» cuando
    # la frase sigue en la 5 manda a buscar donde no está.
    pagina_hasta: int | None = None
    entrecomillado: bool = False

    @property
    def paginas(self) -> tuple[int | None, int | None]:
        return self.pagina, self.pagina_hasta if self.pagina_hasta is not None else self.pagina


# --- Páginas que publican una línea por párrafo -------------------------------
# Varios boletines publican el PDF convertido a HTML con un `<p>` por línea
# visual. El marcado dice «párrafo» y lo que hay es un renglón: una oración
# queda repartida en cuatro bloques y ninguna cita de una frase completa se
# puede anclar a una unidad.
#
# Unir esos renglones no es cosmética. La evidencia de una regla apunta a una
# unidad documental; si la unidad es media oración, la cita no cabe adentro y la
# afirmación queda colgada de un fragmento que no dice lo que se afirma.
#
# La señal que se usa es local y no admite dos lecturas: **un bloque que empieza
# con minúscula está a mitad de una oración**. Un ítem de menú, una fila de
# directorio o un título empiezan con mayúscula; un renglón cortado, no. Se
# probó antes decidirlo por documento —qué proporción de bloques termina en
# punto— y eso confundía una guía telefónica con una norma cortada en renglones:
# en las dos, casi ningún bloque termina en punto. La proporción se descartó por
# eso, no por gusto.

# Con qué cierra una oración. El paréntesis y las comillas van después del punto
# en las notas del boletín: «(...) B.O. 4/11/2020)».
RE_CIERRE_DE_ORACION = re.compile("[.:;!?][\\s'\"\u00bb)\\]]*$")

# Un renglón que continúa el anterior empieza con letra minúscula. Los dígitos
# quedan afuera a propósito: un bloque que empieza con un número puede ser tanto
# la continuación de un monto como un teléfono suelto, y unir de más pega dos
# cosas que nadie escribió juntas.
RE_CONTINUA_LA_ORACION = re.compile(r"^[a-záéíóúüñ]")

# Un correo, una dirección web o un dominio empiezan con minúscula y no son la
# continuación de nada: en las páginas de directorio vienen justo debajo del
# teléfono, que tampoco cierra oración. Sin esta excepción, el mail de una
# defensoría termina pegado a su número de interno.
RE_ES_UN_ENLACE = re.compile(r"^(?:https?://|www\.|[\w.+-]+@[\w-]+\.)", re.IGNORECASE)

# Subincisos como «j.2)» o «a.1)», que los boletines usan para abrir un ítem
# dentro de un inciso. `RE_INCISO` no los reconoce —pide un solo carácter antes
# del paréntesis— y sin esta marca un subinciso se lee como continuación del
# párrafo anterior.
RE_SUBINCISO = re.compile(r"^\s*[a-z]\.\s*\d{1,2}\s*[).]\s*", re.IGNORECASE)

# Un renglón que arranca con un paréntesis corto y lo cierra enseguida —«(INDEC),
# u organismo que…»— es la continuación de la oración de arriba. Se pide que
# cierre cerca: las notas del boletín también empiezan con paréntesis
# —«(Artículo sustituido por art. 1° del Decreto…)»— y esas no son continuación
# de nada, son otra cosa que la norma dice sobre sí misma.
LARGO_MAXIMO_DEL_PARENTESIS = 24
RE_PARENTESIS_CORTO = re.compile(rf"^\(.{{1,{LARGO_MAXIMO_DEL_PARENTESIS}}}?\)")

# Palabras con las que ninguna oración termina. Un renglón que corta en «de la»
# o en «para cubrir la» sigue abajo, empiece la línea siguiente con mayúscula o
# con minúscula: «...para cubrir la» + «Canasta Básica Total» es una sola
# oración partida por el ancho de la página, y sin esta lista queda partida
# también en la base. Es una lista cerrada de palabras de función: ninguna de
# ellas puede ser la última de una oración en castellano.
PALABRAS_QUE_NO_CIERRAN = frozenset(
    [
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "lo",
        "al",
        "del",
        "a",
        "ante",
        "bajo",
        "con",
        "contra",
        "de",
        "desde",
        "durante",
        "en",
        "entre",
        "hacia",
        "hasta",
        "mediante",
        "para",
        "por",
        "según",
        "sin",
        "sobre",
        "tras",
        "y",
        "e",
        "o",
        "u",
        "ni",
        "que",
        "pero",
        "sino",
        "aunque",
        "porque",
        "si",
        "cuando",
        "como",
        "donde",
        "mientras",
        "su",
        "sus",
        "mi",
        "mis",
        "tu",
        "tus",
        "este",
        "esta",
        "estos",
        "estas",
        "ese",
        "esa",
        "esos",
        "esas",
        "aquel",
        "aquella",
        "cuyo",
        "cuya",
        "cuyos",
        "cuyas",
        "cual",
        "cuales",
        "quien",
        "quienes",
        "se",
        "le",
        "les",
        "me",
        "te",
        "nos",
        "más",
        "muy",
        "cada",
        "todo",
        "toda",
        "todos",
        "todas",
        "otro",
        "otra",
        "otros",
        "otras",
    ]
)

RE_ULTIMA_PALABRA = re.compile(r"([\wáéíóúüñÁÉÍÓÚÜÑ]+)[^\w]*$")

MARCAS_DE_ESTRUCTURA = (
    RE_SUBINCISO,
    RE_ARTICULO,
    RE_TITULO,
    RE_CAPITULO,
    RE_SECCION,
    RE_LIBRO,
    RE_ANEXO,
    RE_TRANSITORIA,
    RE_INCISO,
    RE_VISTO,
    RE_CONSIDERANDO,
    RE_NOTA,
)


def continua_el_renglon(anterior: str, actual: str) -> bool:
    """Si `actual` es la continuación del renglón `anterior`.

    Las tres condiciones son necesarias: que el anterior haya quedado abierto,
    que este empiece a mitad de oración y que no abra una unidad nueva. Un
    inciso que arranca en minúscula —«a) acreditar…»— abre unidad igual: la
    marca de estructura gana sobre la minúscula.
    """
    anterior = anterior.strip()
    actual = actual.strip()
    if not anterior or not actual:
        return False
    if RE_CIERRE_DE_ORACION.search(anterior):
        return False
    if RE_ES_UN_ENLACE.match(anterior):
        # Un correo tampoco continúa hacia adelante. Sin esto, el mail de una
        # oficina se lleva pegado el encabezado que viene abajo.
        return False
    if any(marca.match(actual) for marca in MARCAS_DE_ESTRUCTURA):
        return False
    if RE_ES_UN_ENLACE.match(actual):
        return False
    if RE_CONTINUA_LA_ORACION.match(actual) or RE_PARENTESIS_CORTO.match(actual):
        return True
    return _corta_en_palabra_de_funcion(anterior)


def _corta_en_palabra_de_funcion(texto: str) -> bool:
    coincidencia = RE_ULTIMA_PALABRA.search(texto)
    if coincidencia is None:
        return False
    return coincidencia.group(1).lower() in PALABRAS_QUE_NO_CIERRAN


def unir_renglones(parrafos: list[Parrafo]) -> list[Parrafo]:
    """Junta los renglones de un mismo párrafo y reindexa los desplazamientos."""
    grupos: list[list[Parrafo]] = []
    for parrafo in parrafos:
        if not parrafo.texto.strip():
            continue
        if grupos and continua_el_renglon(grupos[-1][-1].texto, parrafo.texto):
            grupos[-1].append(parrafo)
        else:
            grupos.append([parrafo])

    unidos: list[Parrafo] = []
    cursor = 0
    for grupo in grupos:
        # Un bloque solo conserva su texto tal cual: normalizarlo movería los
        # desplazamientos de todo lo que ya estaba bien.
        texto = grupo[0].texto if len(grupo) == 1 else " ".join(p.texto.strip() for p in grupo)
        unidos.append(
            Parrafo(
                texto=texto,
                inicio=cursor,
                fin=cursor + len(texto),
                pagina=grupo[0].pagina,
                pagina_hasta=grupo[-1].paginas[1],
                # Si alguno de los renglones venía entrecomillado, el párrafo
                # entero se marca así: tratar como disposición propia un texto
                # que la norma está citando es el error caro de los dos.
                entrecomillado=any(p.entrecomillado for p in grupo),
            )
        )
        cursor += len(texto) + 1
    return unidos


@dataclass
class ResultadoSegmentacion:
    unidades: list[UnidadSegmentada] = field(default_factory=list)
    # Texto que no se pudo clasificar. Es visible a propósito: la especificación
    # exige que los segmentos no reconocidos detengan la publicación afectada en
    # lugar de desaparecer.
    sin_clasificar: list[Parrafo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def cobertura(self) -> float:
        """Proporción del texto que quedó dentro de una unidad."""
        clasificado = sum(len(u.texto) for u in self.unidades)
        perdido = sum(len(p.texto) for p in self.sin_clasificar)
        total = clasificado + perdido
        return clasificado / total if total else 0.0

    @property
    def articulos_dispositivos(self) -> list[UnidadSegmentada]:
        return [
            u
            for u in self.unidades
            if u.tipo is TipoUnidad.ARTICULO and u.rol_contenido is RolContenido.DISPOSITIVO
        ]


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _normalizar_sufijo(sufijo: str | None) -> str | None:
    if not sufijo:
        return None
    return _sin_acentos(sufijo).lower()


class Segmentador:
    """Convierte párrafos en unidades documentales jerarquizadas."""

    def __init__(self) -> None:
        self._unidades: list[UnidadSegmentada] = []
        self._resultado = ResultadoSegmentacion()
        # Pila de contenedores abiertos (libro, título, capítulo, sección).
        self._contenedores: list[int] = []
        self._articulo_actual: int | None = None
        self._ultimo_numero_raiz: int | None = None
        # Último número transcripto dentro del bloque de sustitución en curso.
        self._ultimo_numero_sustituido: int | None = None
        self._en_anexo: bool = False

    def segmentar(self, parrafos: list[Parrafo]) -> ResultadoSegmentacion:
        self.__init__()
        for parrafo in parrafos:
            if not parrafo.texto.strip():
                continue
            self._procesar(parrafo)
        self._resultado.unidades = self._unidades
        self._calcular_rutas()
        return self._resultado

    # --- Clasificación de un párrafo --------------------------------------

    def _procesar(self, parrafo: Parrafo) -> None:
        texto = parrafo.texto.strip()

        if RE_NOTA.match(texto):
            self._agregar(
                parrafo, TipoUnidad.NO_RECONOCIDO, rol=RolContenido.NOTA, rotulo="Nota editorial"
            )
            return

        for regex, tipo in (
            (RE_LIBRO, TipoUnidad.LIBRO),
            (RE_TITULO, TipoUnidad.TITULO),
            (RE_CAPITULO, TipoUnidad.CAPITULO),
            (RE_SECCION, TipoUnidad.SECCION),
        ):
            coincidencia = regex.match(texto)
            if coincidencia:
                self._abrir_contenedor(parrafo, tipo, coincidencia.group(1))
                return

        coincidencia = RE_ANEXO.match(texto)
        if coincidencia:
            self._en_anexo = True
            self._abrir_contenedor(parrafo, TipoUnidad.ANEXO, coincidencia.group(1) or None)
            return

        if RE_TRANSITORIA.match(texto):
            self._agregar(parrafo, TipoUnidad.TRANSITORIA)
            self._articulo_actual = len(self._unidades) - 1
            return

        if RE_VISTO.match(texto):
            self._agregar(parrafo, TipoUnidad.VISTO)
            return

        if RE_CONSIDERANDO.match(texto):
            self._agregar(parrafo, TipoUnidad.CONSIDERANDO)
            return

        coincidencia = RE_ARTICULO.match(texto)
        if coincidencia:
            self._procesar_articulo(parrafo, coincidencia)
            return

        if self._articulo_actual is not None and RE_INCISO.match(texto):
            self._agregar(
                parrafo,
                TipoUnidad.INCISO,
                numero=RE_INCISO.match(texto).group(1),
                padre=self._articulo_actual,
                rol=self._unidades[self._articulo_actual].rol_contenido,
            )
            return

        if self._articulo_actual is not None:
            self._agregar(
                parrafo,
                TipoUnidad.PARRAFO,
                padre=self._articulo_actual,
                rol=self._unidades[self._articulo_actual].rol_contenido,
            )
            return

        # Encabezados, firmas y texto suelto antes del primer artículo. No se
        # descartan: quedan visibles como no clasificados.
        self._resultado.sin_clasificar.append(parrafo)

    def _procesar_articulo(self, parrafo: Parrafo, coincidencia: re.Match[str]) -> None:
        numero = coincidencia.group(1)
        sufijo = _normalizar_sufijo(coincidencia.group(2))
        rol, motivo = self._rol_del_articulo(parrafo, int(numero), sufijo)

        padre = None
        if rol is not RolContenido.DISPOSITIVO:
            # El texto citado o sustituido cuelga del artículo que lo introduce.
            padre = self._articulo_actual
        elif self._contenedores:
            padre = self._contenedores[-1]

        self._agregar(
            parrafo,
            TipoUnidad.ARTICULO,
            numero=numero,
            sufijo=sufijo,
            padre=padre,
            rol=rol,
            ambigua=motivo is not None,
            motivo=motivo,
        )
        if rol is RolContenido.DISPOSITIVO:
            self._articulo_actual = len(self._unidades) - 1
            self._ultimo_numero_raiz = int(numero)
            self._ultimo_numero_sustituido = None
        else:
            self._ultimo_numero_sustituido = int(numero)

    def _rol_del_articulo(
        self, parrafo: Parrafo, numero: int, sufijo: str | None
    ) -> tuple[RolContenido, str | None]:
        """Decide si el marcador abre una unidad nueva o transcribe otra.

        El caso difícil es salir de un bloque de sustitución: después del texto
        transcripto vuelve el articulado dispositivo, y confundirlos haría que
        el resto de la norma cuelgue del artículo equivocado.
        """
        if self._articulo_actual is None:
            return RolContenido.DISPOSITIVO, None

        actual = self._unidades[self._articulo_actual]
        hay_verbo = bool(RE_VERBO_SUSTITUCION.search(actual.texto))
        retrocede = self._ultimo_numero_raiz is not None and numero <= self._ultimo_numero_raiz
        continua_raiz = (
            self._ultimo_numero_raiz is not None and numero == self._ultimo_numero_raiz + 1
        )
        continua_bloque = (
            self._ultimo_numero_sustituido is not None
            and numero == self._ultimo_numero_sustituido + 1
        )

        # El propio texto dice qué artículo sustituye: si el marcador coincide,
        # la señal es directa y no hace falta inferir nada.
        if hay_verbo and int(numero) in numeros_referidos(actual.texto):
            return RolContenido.SUSTITUTIVO, None

        if not hay_verbo:
            if retrocede and sufijo is None:
                return (
                    RolContenido.CITADO,
                    f"El artículo {numero} repite o retrocede la numeración sin verbo de "
                    "sustitución; hay que confirmar si es una cita o un error de extracción.",
                )
            return RolContenido.DISPOSITIVO, None

        # A partir de acá el artículo en curso introduce texto de otra norma.
        if parrafo.entrecomillado or retrocede:
            return RolContenido.SUSTITUTIVO, None
        if continua_bloque and not continua_raiz:
            # Sigue la transcripción: el bloque sustituye varios artículos.
            return RolContenido.SUSTITUTIVO, None
        if continua_raiz and not continua_bloque:
            # El articulado dispositivo retoma donde había quedado.
            return RolContenido.DISPOSITIVO, None
        return (
            RolContenido.SUSTITUTIVO,
            f"El artículo {numero} aparece tras un verbo de sustitución y la numeración "
            "no distingue si continúa el texto transcripto o el articulado dispositivo; "
            "hay que confirmarlo contra la fuente.",
        )

    # --- Construcción de unidades -----------------------------------------

    def _abrir_contenedor(self, parrafo: Parrafo, tipo: TipoUnidad, numero: str | None) -> None:
        nivel = NIVELES_JERARQUIA.get(tipo, 5)
        while self._contenedores:
            abierto = self._unidades[self._contenedores[-1]]
            if NIVELES_JERARQUIA.get(abierto.tipo, 5) >= nivel:
                self._contenedores.pop()
            else:
                break
        padre = self._contenedores[-1] if self._contenedores else None
        self._agregar(parrafo, tipo, numero=numero, padre=padre)
        self._contenedores.append(len(self._unidades) - 1)
        self._articulo_actual = None
        if tipo is TipoUnidad.ANEXO:
            # Un anexo reinicia la numeración: el artículo 1 del anexo no
            # retrocede respecto del último artículo del cuerpo.
            self._ultimo_numero_raiz = None
            self._ultimo_numero_sustituido = None

    def _agregar(
        self,
        parrafo: Parrafo,
        tipo: TipoUnidad,
        *,
        numero: str | None = None,
        sufijo: str | None = None,
        padre: int | None = None,
        rol: RolContenido = RolContenido.DISPOSITIVO,
        rotulo: str | None = None,
        ambigua: bool = False,
        motivo: str | None = None,
    ) -> None:
        unidad = UnidadSegmentada(
            tipo=tipo,
            texto=parrafo.texto.strip(),
            orden=len(self._unidades) + 1,
            rol_contenido=rol,
            numero=numero,
            sufijo=sufijo,
            rotulo=rotulo,
            inicio=parrafo.inicio,
            fin=parrafo.fin,
            pagina_desde=parrafo.paginas[0],
            pagina_hasta=parrafo.paginas[1],
            padre_indice=padre,
            ambigua=ambigua,
            motivo_ambiguedad=motivo,
        )
        self._unidades.append(unidad)
        if motivo:
            self._resultado.avisos.append(motivo)

    def _calcular_rutas(self) -> None:
        """Ruta jerárquica única por versión.

        Solo las unidades dispositivas compiten por unicidad: el texto citado o
        sustituido puede repetir el número de artículo dentro de su bloque, y su
        ruta incluye la del artículo que lo contiene.
        """
        for indice, unidad in enumerate(self._unidades):
            componentes: list[str] = []
            cursor: int | None = indice
            visitados: set[int] = set()
            while cursor is not None and cursor not in visitados:
                visitados.add(cursor)
                actual = self._unidades[cursor]
                etiqueta = actual.tipo.value.lower()
                if actual.numero_completo:
                    etiqueta += f"-{actual.numero_completo}"
                if actual.rol_contenido is not RolContenido.DISPOSITIVO:
                    # El rol entra en la ruta: sin esto, un artículo 10 citado
                    # dentro del artículo 10 colisionaría con la raíz.
                    etiqueta += f"[{actual.rol_contenido.value.lower()}:{actual.orden}]"
                elif actual.tipo in (TipoUnidad.PARRAFO, TipoUnidad.INCISO) or (
                    not actual.numero_completo
                ):
                    # Sin número no hay con qué distinguir dos unidades del mismo
                    # tipo. Un PDF que encabeza dos bloques con la palabra
                    # "ANEXO" a secas produce dos unidades y la ruta tiene que
                    # separarlas; si no, la segunda pisa a la primera.
                    etiqueta += f"-{actual.orden}"
                componentes.append(etiqueta)
                cursor = actual.padre_indice
            unidad.ruta = "/".join(reversed(componentes))
