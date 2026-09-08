# ADR 0003 · Política de acceso a fuentes públicas

**Estado:** aceptado · **Fecha:** 2026-09-08

## Contexto

El corpus se construye leyendo sitios y documentos de organismos públicos. El
manual de ingesta que acompaña al paquete documenta observaciones del
31/08/2026, incluidas algunas técnicas que no se adoptan.

## Decisión

1. Solo lectura pública: `GET` sobre recursos accesibles sin autenticación. No
   se envían formularios, no se inicia sesión, no se aceptan declaraciones
   juradas y no se reutilizan claves de terceros.
2. Validación TLS completa, siempre. Si un certificado falla, se registra el
   fallo y se busca una fuente oficial equivalente o se hace carga manual
   trazada. La configuración expone el paquete de certificados a usar, nunca un
   interruptor para desactivar la verificación.
3. Se respeta `robots.txt`. Un 403 o un 429 se registran como acceso limitado y
   pausan la fuente; no se rotan identidades ni se evaden controles.
4. Un error de acceso nunca se convierte en "no hay datos": la fuente conserva
   su brecha con motivo y responsable.
5. Presupuesto inicial: 2 segundos entre solicitudes por dominio y concurrencia
   1 para InfoLEG y NormativaBA; hasta 2 para otros dominios que lo admitan.
   Configurable por fuente y versionado con la configuración.
6. El contenido de las fuentes es dato, no instrucción: no se ejecuta lo que
   diga una página, un documento o una respuesta de un modelo.

## Consecuencias

- Algunas fuentes del inventario quedarán registradas como bloqueadas o de
  carga manual. Eso es un resultado informado, no una falla del pipeline.
- Los ejemplos del manual que dependen de claves de terceros o de excepciones
  de TLS no se implementan; la diferencia queda registrada.
