# ADR 0005 · Capturas inmutables y almacén direccionado por contenido

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

Toda afirmación del corpus tiene que poder rastrearse hasta los bytes que la
sostienen, en la fecha en que se leyeron. Si esos bytes se editan o se pierden,
la evidencia deja de serlo.

## Decisión

1. **El almacén se direcciona por contenido.** El nombre del objeto es el
   SHA-256 de sus bytes. Guardar dos veces el mismo contenido es una operación
   sin efecto: dos capturas idénticas comparten objeto y ninguna pisa a la otra.
   La escritura pasa por un archivo temporal y un renombrado, para que una
   corrida interrumpida no deje un objeto a medias con un hash que promete
   contenido completo.
2. **La base guarda URI y hashes, no rutas locales.** El URI lleva esquema
   (`file://` en local) y no contiene la ruta del disco de quien lo escribió.
3. **Las filas de `capturas` son inmutables**, por trigger. Un cambio se
   registra como una captura nueva.
4. **Un `304 Not Modified` exige una captura previa con cuerpo propio.** Reutiliza
   su objeto y su hash y deja constancia de cuál en `captura_previa_id`; nunca
   inventa un cuerpo descargado. La búsqueda de la previa excluye otras
   revalidaciones, para que la cadena no pierda el objeto original.
5. **Las cabeceras conservadas describen el recurso, no la sesión.** Se guarda
   una lista cerrada (`content-type`, `etag`, `last-modified`, …) y se excluyen
   cookies y cabeceras de autorización.
6. **Un rechazo no es "no hay datos".** Un 403, un 429 o un fallo de TLS
   degradan la fuente, cambian su `access_status` y abren una incidencia con
   responsable. La fuente queda pausada; no se rotan identidades.
7. **`Crawl-delay` manda sobre nuestro presupuesto.** El presupuesto por dominio
   es un piso: si el sitio pide más espera, se respeta. Una configuración de
   fuente puede ser más conservadora que la política, nunca menos.

## Consecuencias

- Los contadores de una corrida distinguen tres cosas: lo pedido, lo resuelto
  con contenido (transferido o revalidado) y lo rechazado. Una corrida solo
  figura `COMPLETA` si cerró y resolvió todo lo que pidió.
- Revalidar es barato: una segunda corrida sobre fuentes sin cambios no
  transfiere bytes y aun así deja constancia fechada de que se verificó.
- El almacén local no está replicado. Migrar a un almacén remoto implica
  implementar la misma interfaz; los URI guardados cambian de esquema y hay que
  reescribirlos en una migración de datos.
