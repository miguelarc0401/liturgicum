package io.github.miguelarc0401.liturgicum;

import android.net.Uri;
import android.util.Log;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Las piezas de Piper, en archivos de la app.
 *
 * En Chrome viven en la caché del navegador, que las puede tirar para hacer
 * sitio; aquí van a files/piper/, que es de la app: Android no lo toca, y
 * sólo se va si se quita desde Ajustes o se desinstala la app. Las baja el
 * teléfono y no el worker de piper.js, que no puede hablar con él; al
 * worker se le dan después las direcciones de los archivos ya bajados
 * (app.js, «Piper en archivos»).
 */
@CapacitorPlugin(name = "Archivos")
public class ArchivosPlugin extends Plugin {

    // de una en una: son las piezas de una voz, y en paralelo no se baja antes
    private final ExecutorService bajador = Executors.newSingleThreadExecutor();

    private File carpeta() {
        File d = new File(getContext().getFilesDir(), "piper");
        if (!d.exists()) d.mkdirs();
        return d;
    }

    /** Sólo el nombre de la pieza, sin rutas: nada de salirse de la carpeta. */
    private static String limpio(String nombre) {
        return nombre == null ? "" : nombre.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    @PluginMethod
    public void hay(PluginCall call) {
        try {
            List<String> nombres = call.getArray("nombres", new JSArray()).toList();
            JSArray hay = new JSArray();
            for (String n : nombres) {
                File f = new File(carpeta(), limpio(n));
                hay.put(f.isFile() && f.length() > 0);
            }
            JSObject r = new JSObject();
            r.put("hay", hay);
            r.put("uri", Uri.fromFile(carpeta()).toString() + "/");
            call.resolve(r);
        } catch (Exception e) {
            call.reject("No se ha podido mirar: " + e.getMessage());
        }
    }

    @PluginMethod
    public void baja(PluginCall call) {
        final String url = call.getString("url", "");
        final String nombre = limpio(call.getString("nombre"));
        if (url.isEmpty() || nombre.isEmpty()) {
            call.reject("Falta qué bajar");
            return;
        }
        bajador.execute(() -> {
            File destino = new File(carpeta(), nombre);
            File parte = new File(carpeta(), nombre + ".parte");
            HttpURLConnection c = null;
            try {
                c = (HttpURLConnection) new URL(url).openConnection();
                c.setConnectTimeout(20000);
                c.setReadTimeout(60000);
                c.setInstanceFollowRedirects(true);
                int codigo = c.getResponseCode();
                if (codigo != 200) throw new Exception("la red responde " + codigo);
                long total = c.getContentLengthLong();
                long hecho = 0;
                long avisado = 0;
                try (InputStream in = c.getInputStream(); OutputStream out = new FileOutputStream(parte)) {
                    byte[] buf = new byte[64 * 1024];
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        out.write(buf, 0, n);
                        hecho += n;
                        if (hecho - avisado > 256 * 1024) {
                            avisado = hecho;
                            avisa(nombre, hecho, total);
                        }
                    }
                }
                // se renombra al acabar: una pieza a medias no cuenta como bajada
                if (destino.exists()) destino.delete();
                if (!parte.renameTo(destino)) throw new Exception("no se ha podido guardar");
                avisa(nombre, hecho, total);
                Log.i(VozPlugin.TAG, "bajada " + nombre + " (" + hecho + " bytes)");
                JSObject r = new JSObject();
                r.put("bytes", hecho);
                call.resolve(r);
            } catch (Exception e) {
                parte.delete();
                Log.w(VozPlugin.TAG, "sin bajar " + nombre, e);
                call.reject(e.getMessage() == null ? "sin red" : e.getMessage());
            } finally {
                if (c != null) c.disconnect();
            }
        });
    }

    private void avisa(String nombre, long hecho, long total) {
        JSObject o = new JSObject();
        o.put("nombre", nombre);
        o.put("hecho", hecho);
        o.put("total", total);
        notifyListeners("progreso", o);
    }

    @PluginMethod
    public void borra(PluginCall call) {
        try {
            for (String n : call.getArray("nombres", new JSArray()).<String>toList()) {
                new File(carpeta(), limpio(n)).delete();
            }
            call.resolve();
        } catch (Exception e) {
            call.reject("No se ha podido borrar: " + e.getMessage());
        }
    }

    /** Lo que ocupan, para decirlo en Ajustes. */
    @PluginMethod
    public void ocupa(PluginCall call) {
        long bytes = 0;
        File[] todos = carpeta().listFiles();
        if (todos != null) for (File f : todos) bytes += f.length();
        JSObject r = new JSObject();
        r.put("bytes", bytes);
        call.resolve(r);
    }
}
