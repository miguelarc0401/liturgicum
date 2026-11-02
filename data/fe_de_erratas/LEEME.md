# La fe de erratas

Lo corregido a mano en el texto de la app, una errata por fichero
(`<id>.json`). Cada una dice el trozo como estaba (`antes`) y como queda
(`despues`), con unas palabras alrededor, y los sitios donde se cambió: el
fichero de `app/datos/` y la ruta dentro de él.

Los textos de `app/datos/` se rehacen desde sus fuentes cada vez que se
publica; por eso lo corregido se apunta aquí, y cada fase que los escribe lo
vuelve a poner antes de escribir (`src/erratas.py`, `aplica()`). Si un día
una errata ya no se encuentra —la fuente cambió, o ya trae la corrección—,
la fase lo dice con un AVISO.

Se escriben desde la propia app:

* **en el ordenador**, con `editar.bat`: el editor la apunta aquí y cambia
  `app/datos/` al momento; la ven todos al publicar;
* **en el teléfono**, con la llave de GitHub en Ajustes › Editor del libro:
  el teléfono deja un pedido en `data/erratas_pendientes/`, y GitHub lo
  aplica, lo apunta aquí y vuelve a publicar la app
  (`.github/workflows/erratas.yml`). Lo que no se puede aplicar queda en
  `data/erratas_rechazadas/` con el motivo.

Van una por fichero para que lo corregido en el teléfono y en el ordenador
no choque nunca al juntarse en git: son ficheros nuevos, no renglones del
mismo. Para quitar una, mejor «Deshacer» en la lista de la app, que también
devuelve el texto a como estaba.
