# Leccionario latino — la app

El mismo leccionario de `out/`, pero para leerlo en el teléfono: abre por las
lecturas de hoy, funciona **sin conexión** y se instala en la pantalla de
inicio con su icono, como cualquier otra app.

No es un desarrollo aparte: los textos, las fórmulas latinas y la acentuación
salen de los mismos ficheros de `data/` que componen los DOCX y los PDF, y los
genera `src/15_app_data.py` importando el propio `8_render.py`. Si mañana se
corrige un versículo en el corpus, se regenera y la app lo trae.

## Qué trae

* **Las lecturas de hoy** al abrir, con la fecha litúrgica calculada (Pascua,
  Adviento, ciclo A/B/C y año ferial I/II). Flechas para pasar de día y un
  toque en la fecha para saltar a cualquier otra.
* **Y como se leen.** La lectura va **de corrido**, aunque el leccionario
  salte versículos: lo que se salta lo dicen la cita de arriba y los números
  del margen, y no hace falta un aviso de omisión que parta en pedazos lo
  que en la misa se lee de una sola vez. En el salmo, al revés: cada estrofa
  va en su párrafo y detrás se repite la respuesta **entera**, en las dos
  lenguas, que es lo que se canta. Los salmos que el leccionario da sin
  letra —239 en latín, con nada más la cita de dónde sale la respuesta— se
  quedan con el signo ℟. solo. Con el Misal de 1977 el salmo va además en
  **renglones**, con sangría francesa, que es como lo imprime aquel libro y
  como se canta.
* **Clementina, Nova Vulgata, el Misal con lecturas de 1977, castellano y
  bilingüe**, con un interruptor en Ajustes. El de 1977 es el leccionario
  como lo imprimió el *Missale Romanum cum lectionibus* (Roma, 1977), pero
  sin copiarle ni una letra: de aquel libro se toma la **decisión** —qué
  latín se lee en cada perícopa: la Nova en el Nuevo Testamento y en los
  salmos, la Clementina en el Antiguo, que es de donde él mismo los tomaba—
  y lo que es suyo y de nadie más, el **íncipit** litúrgico («In illo
  témpore», «Fratres») y la fórmula con que presenta la lectura. Donde el
  libro no añade el íncipit sino que reescribe con él el arranque de la
  perícopa, se recorta lo que el texto ya dice: se toca el íncipit y nunca
  el texto. Suyos son también el **salmo en estrofas y renglones**, como lo
  canta, y la **aclamación antes del Evangelio**, que en Cuaresma no es el
  Allelúia sino el versículo solo bajo el rótulo «Versus ante Evangelium».
  Los renglones no salen del OCR: son los del salterio de la Nova Vulgata,
  que es el que ese Misal compone, y cotejados con los suyos coinciden en
  el 96,9 % de los cortes (los que el libro hace de más son los que no le
  caben en su columna de 250 puntos, y en un teléfono los vuelve a hacer la
  pantalla). Por qué no se publica su texto —su capa es un OCR malo— está
  medido en [`Missale/Leccionario-1977.md`](../Missale/Leccionario-1977.md).
  El castellano es la traducción litúrgica aprobada para México,
  cosechada por [`Missale/`](../Missale/LEEME.md) del misalito mensual de
  2018 a 2026: tres de cada cuatro lecturas la tienen, y la que no se
  imprimió ni una vez en los nueve años lo dice en su sitio en vez de
  disimularlo. La cita del leccionario y la que el misalito imprime no
  siempre son la misma, y la perícopa se busca por tres caminos: la cita,
  los versículos que abarca y el día del calendario en que se imprimió;
  cuando el leccionario de México canta otros versículos del mismo salmo,
  se enseñan las dos citas. No se traduce nada: si no está, se dice que no está. El
  bilingüe enfrenta las dos lenguas —en el teléfono, una debajo de otra; en
  una pantalla ancha, a dos columnas— y el latín que pone es el último que
  se eligió, de modo que quien lee la Nova la sigue teniendo.
* **La misa entera, no sólo las lecturas.** El formulario de arriba abajo:
  la reseña, la antífona de entrada, la colecta, las lecturas, la oración
  sobre las ofrendas, el prefacio, la plegaria eucarística, la antífona de
  comunión y la oración de después, con el **Ordinario de la misa**
  intercalado donde va —las 146 rúbricas del Ordo, en las dos lenguas y
  alineadas por su número—. El Ordinario viene **plegado**, porque no se lee
  cada día, pero cuando se busca se busca ahí: un toque en su rótulo lo
  abre, y lo que se deja abierto se queda abierto mientras dure la sesión.
  En Ajustes puede venir abierto, o no salir.
* **Lo que se enseña del formulario, se dice en Ajustes.** «Qué se enseña de
  la misa» da tres modos. *Todo*, que es el formulario entero. *Lo breve*,
  que es lo que cambia cada día y se dice: antífona de entrada, el Gloria
  los días que lo lleva, la colecta, las lecturas con su salmo y su
  aclamación, la oración de los fieles, la oración sobre las ofrendas, la
  antífona de comunión y la oración después de la comunión. Y *lo que yo
  elija*, que es la misma lista de veintidós piezas con una casilla cada
  una, en el orden de la misa; empieza por lo que se estuviera viendo. En
  los dos últimos modos las piezas pedidas vienen abiertas, y el ajuste del
  Ordinario —que sólo dice si viene plegado— no se ofrece, porque allí lo
  que entra ya está decidido pieza por pieza.
* **Lo que la misa deja elegir, se elige.** El saludo (tres fórmulas), la
  invitación al acto penitencial (cuatro) y su fórmula (I, II y III), el
  símbolo —niceno o de los apóstoles—, el «Oren, hermanos», el prefacio
  (los sesenta y siete castellanos, los veintiocho propios cosechados del
  misalito y los treinta y nueve que sólo existen en latín), la plegaria
  eucarística (las cuatro del Ordinario y, en latín, las de la
  reconciliación y las de diversas necesidades), el Misterio de la fe, la
  invitación al padrenuestro y a la paz, la oración antes de comulgar, la
  bendición final —las veinte solemnes y las veintiocho oraciones sobre el
  pueblo del apéndice del Misal— y la despedida. Lo que el día **manda** no
  se pregunta: el Gloria y el Credo los pone o los calla el formulario, y el
  prefacio que el día marca viene elegido. Con una enmienda: el formulario
  no siempre es del día —las ferias del tiempo ordinario toman el del
  domingo de su semana, y con él se traían su Gloria y su Credo—, así que
  una feria los calla. Qué es feria lo dice el calendario del proyecto con
  su rango de la Tabla de los días litúrgicos, y se miran las del rango 13;
  los días de la octava de Navidad, que son del 9 y sí los dicen, los
  acierta el formulario porque es suyo. Donde el Misal no marca ninguno
  —los domingos del tiempo ordinario, por ejemplo— se dice que la elección
  es libre y se ofrece el juego del tiempo.
* **Las otras misas del mismo día.** Las que el leccionario numera —las tres
  de Navidad— salen en la tira de formularios de la cabecera; las que no
  numera —la vespertina de la vigilia de san Juan Bautista y de los
  Apóstoles, la segunda y la tercera de Difuntos— se eligen dentro, en «La
  misa»: cambian los propios y no las lecturas.
* **El año ferial no se ofrece a elegir.** Las ferias del tiempo ordinario
  tienen dos formularios en el leccionario —el del año I, de los impares, y
  el del año II, de los pares—, y el día ya dice cuál es el suyo: con fecha
  delante la tira no los enseña, que sería dar a elegir lo que no se elige
  (el año va dicho en el subtítulo, junto al ciclo). Desde el índice, que se
  hojea sin fecha, los dos siguen estando: allí no hay año que mande.
* **De dónde sale cada texto castellano**, cuando no salió del sitio obvio:
  bajo la pieza, en pequeño, «del día» o «del común», con el porqué y los
  testigos en el título. Lo que el misalito no imprimió en nueve años lo dice
  en su sitio.
* **El devocionario**, en Inicio: 461 oraciones latinas —el Padre nuestro y
  el Ave María, los himnos de santo Tomás, las letanías, los oficios parvos,
  los salmos penitenciales, las oraciones antes y después de la misa— en la
  ortografía de los libros litúrgicos, con su jota, su ligadura y su acento,
  y con el castellano de cada una donde se ha podido verificar de dónde
  sale. No va por fechas: va **por once capítulos, por cuándo y a quién** se
  reza —las oraciones comunes, el día, la misa, la confesión, el año, las
  horas, a Dios, a la Virgen y a los santos, en cada necesidad, la Escritura
  y lo que se sabe de memoria—, y lo que la pieza *es* no es una carpeta
  sino una señal en la fila y un filtro que atraviesa el libro: 132
  oraciones, 108 himnos, 43 letanías, 18 conmemoraciones, 12 oficios parvos,
  11 novenas, 11 jaculatorias… veintiocho formas en total, y otro filtro
  para ver sólo lo que ya tiene castellano. La fila dice qué es la pieza, a
  qué hora la canta el Breviario cuando se sabe, y si todavía está sólo en
  latín. Las veintidós del apéndice del Compendio del Catecismo van
  marcadas donde vivan. También se busca por el título, en cualquiera de las
  dos lenguas, o por lo que la pieza es: «letanía», «novena». Cada oración
  lleva al pie, plegada, su
  procedencia: la del latín y la del castellano, con la autoridad, el
  territorio y si es traducción aprobada o sólo publicada. Las que todavía
  no tienen castellano lo dicen; «no hay» significa que aquí no se ha
  verificado cuál es, no que no exista.
  **Y se hojea como un libro.** La portada es un **índice**: los capítulos
  en romanos, los puntos guía y, donde iría la página, cuántas oraciones
  trae cada uno. Encima, la puerta de quien empieza —**las veintidós del
  Compendio, en su orden y numeradas**— y debajo los filtros, todos a la
  vista. Cada capítulo abre con su portadilla, que dice cuántas trae y
  cuántas tienen ya castellano; los cortos llevan una tira para saltar a
  cada sección. La página de las formas dice **qué es cada una** en un
  renglón —qué es una letanía, una conmemoración, una jaculatoria—, y el
  filtro de una forma lo repite bajo el título: el devocionario es también
  para aprender a rezar. Abierta una oración, su ficha lleva a las demás
  de su clase, la procedencia va como una ficha de biblioteca, y al pie
  están **la anterior y la siguiente de la lista de la que se vino** —el
  capítulo, el filtro, la búsqueda o las del Compendio—, porque una novena
  se reza de corrido y volver al índice entre parte y parte es perder el
  hilo. La búsqueda se recuerda al volver de una oración. Lo hace
  [`Enchiridion/`](../Enchiridion/LEEME.md).
  **Y las de cada uno, a mano.** Una estrella en la ficha de la oración la
  marca como **favorita**, y las favoritas abren la portada, antes que
  nada: las cinco últimas marcadas, y si hay más, un enlace a todas; en
  cualquier otra lista llevan su estrellita detrás del título. Se guardan
  en el propio teléfono, por el id de la pieza, que no cambia al rehacer
  el devocionario.
* **Acentuación litúrgica** encendida o apagada, números de versículo,
  tamaño de letra, y aspecto claro / sepia / oscuro.
* **Ajustes, en tarjetas.** Una por pestaña, en cuatro grupos —cómo se lee,
  la misa, las horas, el año y la app—, y bajo el nombre de cada una lo que
  tiene puesto, que se pone al día al tocar cualquier cosa: plegadas, son el
  índice de lo que se puede cambiar. Cada ajuste lleva el mando que le va,
  y no una lista desplegable para todo: el sí o no, un interruptor; dos,
  tres o cuatro opciones cortas, una tira con todas a la vista; las que hay
  que explicar —la versión, qué se enseña de la misa, la voz—, una tarjeta
  por opción con lo que trae; y la letra, el papel y el color se eligen
  viéndolos: cada letra pinta sus aes con la suya, cada papel es una hoja
  con su tinta y su rúbrica —aunque la app esté puesta en otro—, y cada
  color, su pastilla. La pista va debajo del nombre y a todo lo ancho, no
  apretada al lado del mando, y al final, como en un libro, el colofón.
* **El tamaño de la letra, a mano mientras se reza.** Dos aes en la cabecera
  —en la hora, en la misa y en la oración del devocionario, que son las tres
  páginas que se rezan— lo suben y lo bajan sin ir a Ajustes: que la
  letra se ve chica se nota rezando, no al abrir la app. Al cambiarlo, el
  renglón que se está leyendo se queda donde estaba: lo que crece o encoge
  es todo lo que va por encima, y el desplazamiento lo compensa.
* **Con el teléfono de lado, la cabecera en un solo renglón.** Tumbado sobra
  ancho y falta alto, así que lo que en vertical son tres filas —la fecha,
  la hora, lo que se celebra— se vuelve una: el nombre de la hora o del
  formulario, a continuación el día, las dos aes del tamaño y, al final, la
  fecha abreviada con sus flechas, que siguen cambiando de día y siguen
  abriendo el calendario. Lo que no cabe se abrevia; el renglón no se parte.
* **Un toque esconde la cabecera y la barra.** Tumbado caben diez renglones
  y de ellos los dos marcos se llevan tres: un toque en el texto los manda
  fuera de la pantalla —del todo, no atenuados— y otro los devuelve. De lado
  y de pie, y en las tres páginas que se rezan —la hora, la misa y la oración
  del devocionario—; en el calendario y en los demás paneles no, que allí la
  barra es la única puerta. El
  renglón que se está leyendo no se mueve ni al esconderlos ni al traerlos;
  el índice al borde se queda, que es una cinta y no un mando. En las horas,
  pasar de hora deslizando el dedo los devuelve: la hora que entra se
  presenta en la cabecera, y es ahí donde se ve a cuál se ha pasado.
* **El formato del texto, una vez para todo o sección por sección.** La
  alineación, el interlineado y la partición de palabras se dicen una vez y
  valen para toda la app, que es lo que basta casi siempre; y quien quiera
  más apaga «un solo formato para todo» y entonces cada clase de texto
  —lecturas, salmos y cánticos, himnos, antífonas, oraciones, preces y
  responsorios, y el Ordinario de la misa— lleva el suyo, con una muestra
  al lado que no es un dibujo sino el mismo texto con las mismas reglas. Lo
  que una sección no diga lo sigue diciendo el general. Las secciones se
  agrupan por lo que son y no por el libro en que salen: la primera lectura
  de la misa y la lectura breve de Vísperas son la misma clase de texto.
  El interlineado no es una lista de cuatro medidas sino un número: menos,
  la cifra y más, de cinco en cinco centésimas, y la muestra de encima es el
  renglón de verdad mientras se aprieta. En una sección vale además «igual
  que todas», que es volver a seguir al general.
* **Cinco tipos de letra** —de libro, Garamond, Times New Roman, Alegreya
  (la de pluma, en lugar de Aldhabi, que no se puede llevar dentro) y de
  pantalla— y **el color de la app** fijo si se quiere: en vez del litúrgico
  del día, el que se elija. Cada color, además, en el tono que se quiera:
  siete por color, uno para el papel claro y otro para el oscuro. En el
  calendario el color sigue siendo el de cada día, porque allí el color es
  lo que se lee y no un adorno. La de libro y la de pantalla las pone el
  teléfono; Garamond (EB Garamond), Alegreya y Tinos —la Times de medidas
  idénticas, para donde el sistema no trae la Times— van dentro de la app, en
  `fuentes/`, con su licencia libre, y el service worker las guarda para
  leer sin conexión.
* **Calendario litúrgico** de cada año (2024–2060): qué se celebra cada día
  y con qué grado —solemnidad, fiesta, memoria, memoria libre, domingo,
  feria de Cuaresma, de Adviento…—, con su color, lo que se puede elegir y
  lo que se omite. Un toque en un día lo abre en la misa o en las horas.
  Arriba, un **buscador de celebraciones** («teresa», «ángeles», «asís»)
  deja sólo los días que las nombran, aunque sea como memoria libre o como
  lo que ese año se omite; y al bajar por el año la cabecera se queda
  arriba, resumida: el año, la tira de los meses con el que se está
  leyendo marcado, y la lupa. Desde él se llega al **índice del
  leccionario**.
* **Buscador** sobre el latín, en el índice del leccionario: ignora acentos y
  desata æ/œ, así que escribiendo `quaesumus` encuentra *quǽsumus*. También
  busca por cita: **«salmo 121»** devuelve los siete lugares donde se canta.
* **Se vuelve a donde se estaba.** Quien sale de Laudes al calendario y
  vuelve, vuelve al mismo renglón; otro día, otra hora u otra celebración
  empiezan arriba, y cerrar la app lo olvida. Cuando se anda por otro día,
  junto a la fecha sale **«Hoy»**, que vuelve a éste.
* **Los apéndices**: los versículos que pueden sustituir al del día antes del
  Evangelio en cada tiempo litúrgico (las antífonas «O» del 17 al 24 de
  diciembre, las aclamaciones de Cuaresma…) y los salmos comunes del
  responsorial. Están en el índice, al final.
* **El propio y el común de los santos** (leccionario V), las **misas por
  diversas necesidades y votivas** (VI) y las **rituales y de difuntos**
  (VIII), con su índice propio.
* **El santoral puesto en el calendario**, con el *Calendario general romano y
  latinoamericano*: cada fecha enseña la celebración que toca, con su grado
  (solemnidad, fiesta, memoria, memoria libre).
* **La concurrencia resuelta con la Tabla de los días litúrgicos**: cuando en
  una fecha coinciden varias celebraciones, salen en fila ordenadas por
  precedencia y la primera es la que se celebra. Las solemnidades impedidas se
  trasladan solas, y lo que se omite ese año se dice en vez de callarse.
* El **color litúrgico** tiñe la cabecera: el del tiempo, y el del santo cuando
  lo hay (rojo en los mártires, los apóstoles y la Santa Cruz). Cuatro días
  del temporal se salen del color de su tiempo y lo llevan dicho aparte:
  Pentecostés y el Viernes santo, rojos; el domingo de Ramos, rojo dentro de
  la Cuaresma; y la Misa crismal, blanca. (El rosa de Gaudete y Laetare no
  está: es optativo, el libro deja el morado.) Y nombrar a la Virgen no es
  ser de la Virgen: san José, los padres de la Virgen y los Siervos de santa
  María van de blanco, no del azul de las fiestas marianas.
* Epifanía, Ascensión y Corpus se pueden poner en su fecha o trasladados al
  domingo, según el uso del país; y en las memorias se puede preferir la
  lectura del santo o la continua de la feria.
* **La Liturgia de las Horas**, en la traducción litúrgica de México: las
  siete horas —Oficio de Lectura, Laudes, Tercia, Sexta, Nona, Vísperas y
  Completas— con sus rúbricas en rojo, como en el libro. Al entrar propone
  la hora que toca por el reloj. El oficio se arma en cascada: lo propio
  del santo, si no lo de su común, si no lo del tiempo, la salmodia del
  salterio y el ordinario para lo que no cambia. Sale de
  [`Breviarium/`](../Breviarium/LEEME.md), que es un módulo aparte y con
  su propia fuente.
* **Lo que las rúbricas dejan elegir, se ofrece.** Qué se celebra cada día
  lo dice el mismo calendario que la misa, con su precedencia. En las
  memorias, lo que el santo no tiene propio —el invitatorio, el himno y, en
  Laudes y Vísperas, de la lectura breve a las preces— lleva junto a su
  rótulo un selector discreto: *Del día · Doctores* (o *Pastores*, si el
  santo admite los dos comunes). La salmodia, la lectura bíblica del Oficio
  y Completas no lo llevan, porque ahí no se elige. La antífona del
  Benedictus y del Magníficat, en las memorias y fiestas de los santos,
  ofrece también la del día detrás de la del santo. Una
  memoria libre se puede celebrar o dejar, y en Cuaresma y las ferias
  privilegiadas sólo cabe como conmemoración: eso se elige arriba, con los
  chips de la cabecera. En Ajustes se dice qué opción sale marcada.
* **Cómo empieza la hora, lo elige quien reza.** El Oficio de lectura y
  Laudes empiezan de dos maneras: si ésta es la primera oración del día,
  con el *invitatorio* —«Señor, abre mis labios», la antífona del día y el
  salmo 94 con la antífona repetida después de cada estrofa—; y si antes se
  ha rezado ya alguna otra Hora, con la *invocación inicial*, «Dios mío,
  ven en mi auxilio». Eso no lo sabe el calendario, así que las dos van a
  elegir en lo alto de la hora, con la invocación marcada. Si el día deja
  escoger de dónde se toma el invitatorio (del común del santo o de la
  feria), ese selector sigue en su rótulo, debajo.
* **Primeras o segundas vísperas.** Un domingo y una solemnidad tienen dos
  vísperas, y la app dice cuáles son las de esa tarde, con el nombre y el
  color de la celebración a la que pertenecen. Cuál de las dos gana no se
  decide a ojo: se comparan los dos rangos de la Tabla de los días
  litúrgicos, como manda el n. 61 de los Principios y normas, y el empate es
  para el día que acaba. Así, la tarde del 14 de agosto —san Maximiliano
  María Kolbe, de rojo— son ya las **primeras vísperas de la Asunción**, y
  la cabecera se pone azul; y el 15, las segundas. Lo mismo el 24 de
  diciembre con Navidad, el 31 con Santa María Madre de Dios, la víspera del
  Sagrado Corazón, y el sábado con el domingo que entra. El Sábado santo no:
  su día es de rango 1 por sí mismo, y la Vigilia no son vísperas.
  **Y el texto, cuando no acompaña al rótulo, se dice.** La fuente publica
  por fechas, así que en la víspera de una solemnidad publica sus primeras
  vísperas, y al cosecharla fueron a la casilla de ese día: las del domingo,
  a la del sábado —medido: el sábado de la semana VII de Pascua trae el
  himno «Ven, Creador» y la antífona «Ven, Espíritu Santo», que son las de
  Pentecostés—, y las de una solemnidad de entre semana, al santo de la
  víspera: el 14 de agosto, san Maximiliano María Kolbe guarda las primeras
  vísperas de la Asunción, y así todos los años, porque el santoral va por
  fecha. Pero no siempre: la víspera de la Inmaculada trae las vísperas de
  san Ambrosio, y de la solemnidad sólo la oración. **Cuál de las dos cosas
  pasa no se supone, se mide**: si la oración de la tarde no es la de las
  Laudes de esa mañana, el día ya ha cambiado de celebración y los textos
  son los suyos. Cuando no, el rótulo y el color se ponen igual —son los de
  la hora que se reza— y la nota del día advierte de que el oficio que sigue
  es el del día que acaba.
* **La Hora intermedia**: la salmodia del día sale en Sexta y la
  complementaria (salmos graduales) en Tercia y Nona, y las tres dejan
  cambiar a la otra. En Adviento, Navidad, Cuaresma y Pascua la antífona de
  cada hora se queda aunque cambien los salmos. Los himnos que se ofrecen
  son los del tiempo: en el ordinario, los de las semanas I a XVII o los de
  la XVIII a la XXXIV. Los domingos, en Sexta sale primero «Cuando la luz
  del día está en su cumbre», que es el que el libro les señala —los otros
  del juego cantan al trabajo de la semana—; la fuente lo pone unas veces y
  otras no, según lo que aquel año imprimiera la web, y aquí se endereza.
  Los demás siguen ofreciéndose detrás, con su número.
* **Lo que la cosecha dejó de más, fuera.** La fuente publica por fechas y
  una página no siempre trae una sola hora: detrás de las Vísperas imprime
  a veces la cabecera y la oración de las primeras vísperas de la solemnidad
  que entra, y detrás del Oficio de lectura, la oración de la feria los días
  de memoria —o la misma otra vez—. Eso quedaba como una segunda oración
  después de la conclusión: en la memoria de Nuestra Señora del Rosario
  salían la de la Virgen y detrás la del tiempo ordinario. Son veinte piezas
  en todo el año, y ninguna se reza donde salía.
* **La lectura bíblica del Oficio sigue el ciclo de dos años** (año I los
  impares, año II los pares), como la fuente.
* **Reseña, himnos y antífona final.** La reseña del santo o de la fiesta va
  pegada a la segunda lectura, que es la que cuenta su vida, y se pliega:
  se lee una vez. Donde hay varios himnos posibles (Completas, la Hora
  intermedia, y los días en que el libro da más de uno) y en la antífona
  final de la Virgen, un selector numerado deja escoger.
* **Cómo se lee.** Himnos, salmos y cánticos van por renglones con sangría
  francesa, de modo que al agrandar la letra se ve dónde empieza cada uno;
  lecturas, responsorios, preces y oraciones, justificados —y todo eso se
  puede cambiar en Ajustes, junto o sección por sección—. Cuando el salmo
  empieza con las mismas palabras que su antífona (con o sin «aleluya»), una
  † roja al final de la antífona y otra donde se sigue. Lo que no está en la fuente y se tomó
  de los tomos impresos lleva la marca «ed. española» (ver
  [Breviarium/LEEME.md](../Breviarium/LEEME.md)).

* **Rezarla en alta voz, de camino.** El botón del altavoz, en la cabecera,
  la empieza a decir por la sección donde vaya la vista, y una barra de
  mandos grandes —sección anterior, parar y seguir, sección siguiente—
  queda abajo mientras suena.
  **Antes de empezar pregunta con qué voz**, entre las de Piper que hay
  bajadas y la del teléfono; la elegida se queda puesta en Ajustes y la
  próxima vez sale primera. Si no hay más que una, no pregunta. El botón del
  volante no pregunta: sigue con la que haya.
  **La hora, la misa y el devocionario.** Las tres se pintan en cajas de la
  misma hechura, así que el reproductor es uno solo y no sabe en qué libro
  está: lo único que cambia de una a otra —quién es la página, de dónde salen
  los nombres de sus secciones y qué pasa al acabar— está en una función de
  cinco renglones. En la misa los mandos pasan de parte —colecta, primera
  lectura, evangelio—; en una oración del devocionario, que es una sola caja,
  pasan de párrafo. Y al acabar sólo encadena la hora: una misa no sigue en
  otra, y de una oración no se pasa sola a la de al lado.
  **Donde hay dos lenguas, dice el castellano.** La columna latina del
  bilingüe no se dice —la voz es española y lo mismo está enfrente—, pero el
  latín solo sí: en una versión latina a secas, y en la oración del
  devocionario que no está traducida, es lo único que hay. Callan también el
  número del versículo —dicho sale «once en aquel tiempo»—, la cita que va
  dentro de la fórmula de la lectura, lo que dice de dónde sale la pieza
  («del día») y los avisos de la app, que son de la app y no del libro. **Lo que se dice es lo que se ve, menos la
  rúbrica**: el guión no sale de los datos sino de la página ya pintada, de
  modo que dice la opción que esté elegida en cada sección y la forma del
  comienzo que se haya escogido, y la reseña sólo si está abierta. La
  rúbrica se calla porque es una indicación y no una oración, y eso basta
  para callar con ella las siglas de los versículos, los rótulos de las
  antífonas y los títulos de los salmos: van todos marcados como rúbrica en
  la fuente (medido: 20 242 veces la sigla «V.» o «R.», ni una suelta). Lo
  poco que queda se allana —las comillas angulares, los corchetes del
  editor, la raya con que los tomos abren la respuesta de las preces— y la
  «N.» del hueco del nombre («Protege al papa N.») se quita, que dicha sale
  «ene».
  **Pensada para el coche.** Los mandos van también al volante y a los
  auriculares (MediaSession), de modo que se pasa de sección sin tocar el
  teléfono; y para que no se calle con la pantalla apagada suena de fondo un
  audio de un solo bit de amplitud, que no se oye y que al navegador le
  basta para tratar la página como un reproductor. Dentro de una sección no
  hay ni un temporizador: los trozos se le dan todos de golpe al motor y es
  él quien los va diciendo, así que no depende de que la página despierte;
  sólo al cambiar de sección se cuenta un silencio, y son siete u ocho en
  toda la hora. Aun así, **si el teléfono la corta, al volver a mirarlo
  sigue por donde iba**. Los trozos no pasan de 220 caracteres porque hay
  versiones de Chrome que truncan una locución de más de quince segundos.
  **Lo que cuesta.** Con una voz del sistema a velocidad normal (medido:
  15,1 caracteres por segundo), el Oficio de lectura son unos 11 minutos,
  Laudes 8, Vísperas 7, Completas 5 y las horas menores 4 cada una: las
  siete, unos 44 minutos.
  **Y una voz mejor, si se quiere.** La del sistema lee bien pero es voz de
  máquina. En Ajustes se puede dar la clave de un servicio de síntesis
  neuronal y entonces la dice ésa. Eso —y sólo eso— pide conexión: lo que se
  trae queda guardado en la caché del navegador, de modo que **una hora
  pedida una vez se vuelve a decir sin red**; y donde la red no llegue, ese
  trozo lo dice la voz del sistema y la hora no se corta (tres fallos
  seguidos y deja de pedir hasta la hora siguiente, con el motivo escrito en
  la barra). La clave se guarda en el teléfono; el texto de lo que se reza
  va al servicio, que para decirlo tiene que leerlo.
  **Dos servicios, y no dan lo mismo.** El que viene puesto es **Google
  Cloud**, y no por la voz —las dos son excelentes en español— sino por la
  cuenta: su tramo gratuito **no es uno solo, sino uno por familia de
  voces**, y con las **WaveNet** son cuatro millones de caracteres al mes.
  Las siete horas de un día son 37 785 caracteres, o sea 1,13 millones al
  mes rezándolas todas a diario: a Google le caben casi cuatro veces, y en
  **Azure**, que da 500 000, se sale. Por eso cada voz de la lista dice en
  su rótulo lo que trae de tramo gratuito. Con Google va texto limpio y la
  velocidad en su propio campo (`speakingRate`), de modo que no se paga ni
  una etiqueta; con Azure el SSML es obligatorio, y como **Microsoft cobra
  todo el marcado menos `<speak>` y `<voice>`**, el `<prosody>` sólo se pone
  cuando la velocidad no es la normal: son 37 caracteres por trozo, unos
  2 600 de los 7 000 que cuesta una hora.
  Los nombres de las voces se midieron contra la documentación, que es
  donde se ven las trampas: las WaveNet de España son **E, F, G y H**, y no
  las A–D que uno daría por supuestas.
  **Piper: una voz neuronal sin cuenta.** Las dos cuentas de arriba piden
  una tarjeta para abrirse, y eso deja fuera a quien no quiera darla. Piper
  es una voz neuronal que **se baja una vez y vive en el teléfono**: desde
  entonces habla sin conexión, sin cuenta y sin que el texto salga del
  teléfono. El motor está aparte, en `piper.js`, que corre en un worker
  para no trabar la página; trae de fuera tres piezas —onnxruntime-web de
  cdnjs, el fonetizador de piper (espeak-ng compilado a wasm) de jsDelivr y
  la voz de `rhasspy/piper-voices` en Hugging Face— y las guarda en una
  caché suya, `voz-piper`, que el service worker no tira al publicar. No se
  copian al repositorio: espeak-ng es GPL. El motor son 29 MB, comunes a
  todas las voces, y cada voz de 28 a 77 MB más; se bajan desde Ajustes, con
  su barra, y **decir no baja nunca nada**: noventa megas no se piden por
  sorpresa a media hora rezada.
  **Mexicanas, que es la lengua del libro.** Viene puesta una de México, no
  de España, porque el castellano de la app es la traducción litúrgica
  mexicana y el calendario es el de allá. Y no es sólo el acento: a espeak
  se le pide `es-419` en vez de `es`, de modo que **sesean** —«grasia», no
  «graθia»—, que es como se reza esto. Son **claude** (mujer; el nombre es
  del quien la entrenó y no tiene que ver con nada de aquí) y **ald** (Aldo,
  hombre), ésta también en una versión ligera que va un 25 % más deprisa y
  ocupa un tercio. De España quedan **sharvard** (mujer y hombre en un mismo
  modelo), **davefx** (hombre) y **carlfm** (la más rápida de todas), que
  distinguen la c y la z. Y dos italianas, **paola** y **riccardo**, para el
  latín con la pronunciación eclesiástica —las horas están en castellano,
  así que hoy leen el castellano con acento de Roma—.
  Lo descartado, y por qué: **Kokoro**, porque la versión para el navegador
  sólo trae voces inglesas; **Chatterbox**, porque pide tarjeta gráfica; y
  **daniela** (Argentina), porque al medirla tardaba 47 segundos en hacer 4
  de voz. Que una voz se llame «high» no dice si es lenta: daniela lo es y
  pesa 114 MB, mientras que claude, que también se llama «high», pesa 63 y
  corre como las medianas. Hay que medirlas, no deducirlo del rótulo.
  **Lo que tarda.** Piper hace la voz al momento, y eso se paga en tiempo.
  Medido en el PC y con la página a la vista, las medianas (claude, ald,
  sharvard) la hacen unas **2,8 veces** más deprisa de lo que se dice, la
  ligera mexicana **3,4** y carlfm **4,5**. Esas cifras bailan bastante de
  una pasada a otra —el equipo tiene sus rachas—, así que valen para
  comparar unas voces con otras, medidas a la vez, y no como promesa.
  Pero **con la página escondida el navegador la frena casi a 1:1**, y con
  la pantalla apagada pasará lo mismo. Por eso no se hace sólo el trozo
  siguiente, como en línea, sino **hasta cuarenta por delante** mientras la
  pantalla está encendida: lo adelantado al principio cubre después. Se
  guarda sólo en memoria y sólo mientras suena la hora (en disco serían cien
  megas al día de WAV). El botón **Probar** de Ajustes mide el teléfono
  mismo y dice si va sobrado o justo.

**Lo que no trae:** el leccionario IX (misas con niños), que sí está en `out/`,
en Word y en PDF.

## Probarla en el ordenador

La app **no funciona abriendo `index.html` con doble clic**: el navegador no
deja que una página `file://` lea sus propios datos. Hay que servir la carpeta,
aunque sea desde el propio ordenador:

```bash
python -m http.server 8765 --directory app
```

y abrir <http://localhost:8765>.

## Ponerla en el teléfono

Para instalarla hace falta servirla **una vez** por `https`. Después ya no
necesita ni servidor ni conexión: todo queda guardado en el teléfono.

### Opción 1 — Netlify Drop (lo más rápido, sin cuenta ni git)

1. Entra en <https://app.netlify.com/drop>.
2. Arrastra la carpeta `app/` entera a la página.
3. Te da una dirección `https://algo.netlify.app`.

### Opción 2 — GitHub Pages (si quieres que sea tuya, estable y que se actualice sola)

Es la que está montada: hay un flujo de trabajo en
`.github/workflows/publicar-app.yml` que publica `app/` en cada empujón, y un
`publicar.ps1` que rehace los datos y los sube en una orden. Los pasos de la
primera vez están en el [README](../README.md) de la raíz.

### Instalar en Android

Abre esa dirección en **Chrome**, toca los tres puntos y elige **«Añadir a la
pantalla de inicio»** o **«Instalar aplicación»**. Aparece el icono, y al
abrirla va a pantalla completa, sin barra del navegador. La primera vez
descarga unos 8 MB; por detrás y sin estorbar se guardan la segunda versión
latina (6 MB), las lecturas en castellano (5), el Misal entero (4) y la
liturgia de las horas (unos 25). A partir de ahí abre sin conexión, y sin
conexión están todas las vistas: no hay ninguna que pida la red la primera
vez que se abre.

> Si el navegador no ofrece instalarla, casi siempre es que la dirección es
> `http` y no `https`. Es el único requisito.

## Rehacer los datos

```bash
python src/12_calendario.py        # el esqueleto del año (si cambió algo antes)
python src/16_parse_anexos.py      # los apéndices
python src/5_resolve.py --anexos   # y con --fuente nova
python src/18_santoral.py          # santoral + precedencia -> calendario completo
python src/15_app_data.py          # -> app/datos/*.json
python Breviarium/src/4_app.py     # -> app/datos/horas*.json (la liturgia de las horas)
```

Las dos últimas son las que hay que repetir cuando se toca `data/santoral.csv`
o cualquiera de las tablas editables, y es justo lo que hace `.\publicar.ps1`.

El icono va aparte, porque no depende de los datos y casi nunca cambia:

```bash
python src/19_iconos.py            # src/icono-fuente.webp -> app/icono-*.png
```

Sale todo de una sola imagen, la tapa del breviario. Para cambiarlo se
sustituye `src/icono-fuente.webp` y se vuelve a pasar el guion; de ahí salen
el del navegador, el de iOS y los dos de Android —el normal y el `maskable`,
que es el que el sistema recorta con la forma que tenga el teléfono—.

`15_app_data.py` rehace de paso el leccionario de 1977 llamando a
`21_lect1977_app.py`, y no al reves: aquel fichero no es un corpus, sino la
elección entre los dos latinos que esta fase acaba de escribir, de modo que
hacerlo aparte lo dejaría atrasado en cuanto se corrigiera un versículo. Lo
único que va suelto es `20_lect1977.py`, que es el que lee los cuatro tomos
del Misal de 1977 y deja medido `data/lect1977_pericopas.json`; ése sólo hace
falta repetirlo si cambian los tomos.

`15_app_data.py` deja en `app/datos/version.js` una firma de los datos. El
service worker la usa como nombre de su caché, así que al cambiar los datos
tira la caché vieja sola: no hay que desinstalar nada en el teléfono. Y
`app.js` pregunta si hay versión nueva al arrancar, al volver la app a primer
plano y al recuperar la conexión, de modo que el teléfono se pone al día solo.

## ¿Y un `.apk` de verdad?

Esta misma carpeta se envuelve en un APK instalable con
[Capacitor](https://capacitorjs.com/) (`npx cap add android`, `webDir: "app"`),
o se publica en Play Store con [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
como *Trusted Web Activity*. Las dos exigen instalar JDK y el SDK de Android
(~3 GB) en el ordenador, y no aportan nada que la app instalada no haga ya:
por eso no está hecho.

## Los ficheros

```
index.html              la página
estilos.css             la hoja de estilo (colores litúrgicos, temas)
app.js                  toda la app: rutas, calendario, maquetación, buscador
sw.js                   el service worker: lo que la hace funcionar sin conexión
manifest.webmanifest    nombre, iconos y modo pantalla completa
icono-*.png             los saca src/19_iconos.py de src/icono-fuente.webp
datos/                  lo generado; no se edita a mano
datos/lecturas_*.json   las tres versiones latinas y la castellana
                        (clementina, nova y lect1977 las hacen
                        src/15_app_data.py y src/21_lect1977_app.py)
datos/horas*.json       la liturgia de las horas (la hace Breviarium/src/4_app.py)
datos/misa.json         el formulario de cada misa, con sus propios
datos/misal_latino.json el Misal de 2002, una vez y por su propio nombre
datos/prefacios.json    los dos juegos de prefacios, emparejados
datos/ordinario.json    el Ordo Missæ bilingüe, por número de rúbrica
                        (los cuatro los hace Missale/src/6_app.py)
datos/devocionario.json el devocionario latino, con su castellano y la
                        procedencia de cada pieza (Enchiridion/src/5_app.py)
```

Los cuatro ficheros de la misa son 3,8 MB y no se guardan *al instalar* la
app, sino justo después, en la segunda tanda del service worker: así instalar
no depende de bajarse 12 MB de golpe con mala cobertura. Pero se guardan los
cuatro, y sin que nadie abra una misa: la regla de la app es que una vez
instalada no hace falta internet para nada, y una vista que pidiera la red la
primera vez que se abre la rompería justo el día que se reza sin cobertura.
Van juntos porque `app.js` los pide juntos —sin los cuatro no se arma la
misa—, así que o están todos o no sirve ninguno.
