# Acta de identidad y credenciales

Evidencia de P-017 criterio 1: «la identidad validada determina los roles y actor
auditado; no se acepta un X-Actor libre como identidad de producción y se prueba
revocación de sesión».

## Qué había

Las rutas de administración pedían un token de una lista en `BN_ADMIN_TOKENS` y
tomaban al actor de la cabecera `X-Actor`. La puerta estaba —sin la variable
configurada no se administraba nada— pero **el token identifica al despliegue, no
a la persona**: quien lo tuviera podía firmar como cualquiera, y el nombre que
quedaba en la bitácora lo escribía quien llamaba.

Lo que se firma en este sistema es que una regla dice lo que dice el derecho. Una
bitácora donde el actor es texto libre no acredita eso.

## Qué hay ahora

**Una credencial por persona, firmada, con vencimiento.** Dice quién es, qué
puede y hasta cuándo, y va firmada con HMAC-SHA256 contra `BN_CREDENCIAL_SECRETO`.
El actor **sale de la credencial**: `X-Actor` deja de ser una identidad y se
ignora cuando hay credencial.

```
bn operacion emitir-credencial --actor "curacion_juridica:nombre" --rol revisor --dias 30
```

El token se imprime una vez y no se guarda. Lo que la base conoce es su
identificador, para poder revocarlo.

**Roles adentro de la credencial.** `revisor`, `publicador`, `auditor`. Un revisor
no publica aunque conozca la ruta, y un publicador no decide reglas: revisar y
publicar son decisiones distintas y las toma gente distinta. Eso también cierra
la mitad de P-016 criterio 2 que es del backend.

**Vencimiento con tope de 90 días.** Una credencial que no vence es una
contraseña que nadie rota.

**Revocación.** `bn operacion revocar-credencial <id> --actor … --motivo …`. Deja
de valer en el pedido siguiente. La fila no se borra ni se puede modificar —tiene
el mismo disparador de inmutabilidad que la bitácora—: que una credencial haya
sido revocada, cuándo y por qué es parte de la historia de quién pudo hacer qué.

**Sin secreto no se verifica nada.** No hay valor por omisión, a propósito: uno
compartido haría que una credencial emitida en la máquina de cualquiera valiera
en producción.

## La bitácora dice cómo se supo quién era

La columna `auditoria_eventos.identidad` guarda la procedencia del actor:

| Valor | Qué significa |
| --- | --- |
| `CREDENCIAL_FIRMADA` | Credencial por persona, verificada y no revocada. |
| `AUTODECLARADA` | Token compartido y actor escrito por quien llamaba. Solo con `BN_IDENTIDAD_MODO=desarrollo`. |
| `PROCESO_LOCAL` | CLI o acceso directo a la base. |
| `NO_REGISTRADA` | Anterior a que esto se registrara. |

No la pasa cada sitio que escribe en la bitácora —son siete y alcanza con que uno
se olvide—: sale de `bn.identidad`, un ajuste de sesión que la API pone al abrir
la transacción, y la columna la toma por omisión. Sin ajuste queda
`PROCESO_LOCAL`, que es lo que efectivamente es.

Las nueve filas anteriores a la migración quedaron en `NO_REGISTRADA`. No se les
adivina la procedencia: decir de un evento viejo que fue `PROCESO_LOCAL` sería
inventar una constancia, que es justo lo que esta columna viene a evitar.

## El modo desarrollo, y por qué existe igual

Con `BN_IDENTIDAD_MODO=desarrollo` se admite la puerta vieja. Sirve para probar
sin montar credenciales, y **todo lo que entra por ahí queda marcado
`AUTODECLARADA` para siempre**. Es la diferencia entre una excepción que se ve en
los datos y una que vive en un comentario: dentro de dos años, una firma jurídica
hecha en modo desarrollo se va a poder distinguir de una hecha con credencial.

En producción la variable no se pone. Sin ella, un token compartido recibe 403 y
el mensaje dice por qué.

## Lo que este acta no acredita

- **No hay proveedor de identidad.** Las credenciales las emite un comando que
  corre quien tiene acceso al secreto de firma. Para una organización con altas y
  bajas de personal eso es poco: lo que corresponde es OIDC contra el directorio
  que ya usen. El diseño lo contempla —las rutas piden una `Identidad`, no un
  formato de token— pero elegir el proveedor no es una decisión de acá.
- **Sin lista de direcciones permitidas.** Cualquiera con una credencial válida
  entra desde donde sea.
- **Los criterios 2 y 3 de P-017 siguen abiertos en parte.** Falta la política
  explícita de retención de la conversación y de los hechos mínimos, y los
  límites de abuso y la protección XSS/CSRF, que dependen del mecanismo de sesión
  del front. No hay front todavía.
