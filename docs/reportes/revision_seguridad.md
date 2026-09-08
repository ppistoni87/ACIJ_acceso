# Revisión de seguridad del código de esta iteración

Barrido sobre lo que se agregó: dos migraciones de esquema, un endpoint con
parámetro nuevo, cuatro módulos de curación, dos adaptadores y las capturas de
red que se hicieron para poblar los casos.

## Lo que se buscó y no apareció

- **Secretos en código.** Ninguna credencial, token ni clave. La configuración
  operativa sale del entorno.
- **Validación de TLS relajada.** Ningún `verify=False`, ningún contexto SSL sin
  verificación, ningún `CERT_NONE`. Las capturas nuevas (la ficha de la Comuna 2
  y la publicación de ACIJ) se hicieron con validación completa.
- **Backtracking catastrófico** en las expresiones regulares nuevas. Se midió el
  peor caso de cada una —textos de 40.000 caracteres sin separadores— y todas
  responden en milisegundos.
- **SQL armado con la entrada del usuario.** Los `f"…{donde}"` de la API
  concatenan condiciones que son literales del módulo; los valores viajan
  siempre como parámetros. Los nombres de tabla del reporte de rendimiento salen
  de una tupla del propio módulo.

## Lo que apareció y se corrigió

### El nombre de la base se interpolaba sin validar

`CREATE DATABASE` y `DROP DATABASE` no aceptan un parámetro para el nombre: la
sentencia se arma interpolando. Dos comandos del CLI —`bn operacion restaurar` y
`bn calidad ensayo-actualizacion`— reciben ese nombre por opción, y el primero
borra la base antes de crearla.

Un nombre con comilla doble cierra el identificador y lo que sigue se ejecuta.
Quien corre el CLI ya tiene credenciales del motor, así que no es una escalada de
privilegios; es un arma cargada apuntando a la base de producción cuando el
nombre viene de un script o de una variable de entorno.

Ahora el nombre se valida contra un identificador simple antes de tocar el
motor, y el comando falla con un mensaje que dice por qué.

### La lectura de fechas era cuadrática

Para clasificar cada fecha hay que saber si está dentro de una nota de
consolidación, y eso se resolvía recorriendo el texto desde el principio por
cada fecha encontrada. Sobre un boletín de 240 KB con cuatro mil fechas la
extracción tardaba **31,7 segundos**.

No hace falta un atacante: un boletín oficial grande es exactamente eso, y el
tiempo lo paga la ingesta. Los tramos entre paréntesis se calculan ahora una vez
por documento y se buscan por bisección: **0,35 segundos**, con el mismo
resultado.

Las dos correcciones tienen prueba propia. La de la lectura de fechas incluye un
tope de tiempo, para que si alguien vuelve a hacerla por fecha la prueba lo diga.
