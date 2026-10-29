# Lo que falta del libro de horas de México

Las 21 celebraciones del calendario de México que no tienen oficio en ninguna
de las fuentes del proyecto. Hoy la app las reza con su común y la colecta del
Misal mexicano, que es un apaño correcto pero no es lo que trae el libro.

De cada una falta, por este orden de valor:

1. **la reseña** y **la segunda lectura con su responsorio** — de esto no
   tenemos nada, ni en la fuente argentina, ni en el PDF español, ni en el
   Misal;
2. **la oración** — tenemos la colecta del Misal mexicano como suplente, pero
   la del libro manda sobre ella.

Lo demás (salmodia, himnos, antífonas, lectura breve, preces) lo da el común y
no hay que copiarlo.

## La lista, por fecha

| fecha | grado | celebración | estado |
|---|---|---|---|
| 25-02 | memoria libre | Beato Sebastián de Aparicio, religioso | falta |
| 27-02 | memoria libre | San Gregorio de Narek, abad y doctor de la Iglesia | falta |
| 27-04 | memoria libre | Santa María Guadalupe García Zavala, virgen | falta |
| 13-05 | memoria libre | Nuestra Señora de Fátima | falta |
| 16-05 | memoria libre | San Juan Nepomuceno, presbítero y mártir | falta |
| 29-05 | memoria libre | San Pablo VI, papa | falta |
| 27-06 | memoria libre | Nuestra Señora del Perpetuo Socorro | falta |
| 30-07 | memoria libre | Santa María de Jesús Sacramentado Venegas, virgen | falta |
| 09-08 | memoria libre | Santa Teresa Benedicta de la Cruz, virgen y mártir | falta |
| 16-08 | memoria libre | Beato Bartolomé Laurel, religioso y mártir | falta |
| 19-08 | memoria libre | Beatos Pedro de Zúñiga y Luis Flores, presbíteros y mártires | falta |
| 26-08 | memoria libre | San Junípero Serra, presbítero | falta |
| 02-09 | memoria libre | Beato Bartolomé Gutiérrez, presbítero y mártir | falta |
| 05-09 | memoria libre | Santa Teresa de Calcuta, virgen | falta |
| 17-09 | memoria libre | Santa Hildegarda de Bingen, virgen y doctora de la Iglesia | falta |
| 19-09 | memoria libre | San José María de Yermo y Parres, presbítero | falta |
| 05-10 | memoria libre | Santa Faustina Kowalska, virgen | falta |
| 23-10 | memoria libre | San Juan de Capistrano, presbítero | **hecha** (del libro, a mano) |
| 24-10 | fiesta | San Rafael Guízar y Valencia, obispo | oraciones hechas; faltan reseña y segunda lectura |
| 25-10 | memoria libre | San Antonio María Claret, obispo | falta |
| 23-11 | memoria libre | Beato Miguel Agustín Pro, presbítero y mártir | falta |
| 10-12 | memoria libre | Nuestra Señora de Loreto | falta |

Veinte de las veintiuna son **memorias libres**. Eso es lo que hace difícil
encontrarlas en la red: las webs y las apps que siguen la traducción mexicana
suelen rezar la feria cuando el día es memoria libre, y no ofrecen el propio
del santo. Es lo que ya le pasa a eBreviary.

## Las dos comprobaciones que deciden si Appostolica sirve

Appostolica (la app de la Conferencia del Episcopado Mexicano) trae Liturgia de
las Horas en la traducción de México. No se puede abrir desde aquí, así que
estas dos las tiene que hacer el usuario en su teléfono. Son un minuto cada una.

**1. ¿Es de veras el texto del libro?** El 24 de octubre, San Rafael Guízar y
Valencia, que en México es fiesta. Abrir el Oficio de lectura de ese día y
comparar su oración con la que ya está copiada a mano del libro impreso en
`datos/libro/libro_mexicano.json` (clave `st_1024_234`). Si coincide palabra por
palabra, la app es la edición mexicana y se puede copiar de ella con confianza.

**2. ¿Da el propio en las memorias libres?** El 25 de octubre, San Antonio
María Claret, que es memoria libre y está en la lista. Abrir el Oficio de
lectura de ese día y ver si la app ofrece elegir el santo —con su reseña y su
segunda lectura propias— o si sólo reza la feria. Si sólo da la feria, la app
no resuelve estas veinte y hay que seguir con el libro impreso.

Si la app tiene selector de fecha, las dos se pueden hacer ahora mismo sin
esperar al día.

## Cómo entra lo que se copie

El texto de la app se puede **seleccionar y copiar**, que es mucho mejor que
fotografiar la página: no hay que pasar nada por OCR y no se cuelan erratas de
lectura. Basta pegar aquí, de cada celebración, la reseña, la segunda lectura
con su responsorio y la oración, y se arma la entrada de
`libro_mexicano.json` igual que las dos que ya están.
