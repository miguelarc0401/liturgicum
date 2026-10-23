package io.github.miguelarc0401.liturgicum;

import android.content.Intent;
import android.media.AudioAttributes;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.speech.tts.Voice;
import android.util.Log;
import androidx.core.content.ContextCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * La voz del teléfono, para cuando la app corre dentro del APK.
 *
 * El WebView de Android no trae speechSynthesis, así que app/nativo.js monta
 * uno encima de esto: cada locución que la página encola llega aquí con su
 * id, se le pasa al motor de voz de Android (el que tenga puesto el
 * teléfono), y lo que el motor va diciendo —empieza, va por tal palabra,
 * acaba— vuelve a la página por el evento "trozo". Y lleva también los
 * mandos: arranca el servicio que mantiene la app viva con la pantalla
 * apagada (VozServicio) y le pasa a la página lo que se toca en la
 * notificación o en el volante, por el evento "mando".
 */
@CapacitorPlugin(name = "Voz")
public class VozPlugin extends Plugin {

    static final String TAG = "Liturgicum";
    private static VozPlugin instancia;

    private TextToSpeech tts;
    private boolean lista = false;
    private boolean fallida = false;
    private final List<Runnable> esperando = new ArrayList<>();
    private String vozPuesta = null;

    @Override
    public void load() {
        instancia = this;
        tts = new TextToSpeech(getContext(), (estado) -> {
            List<Runnable> pendientes;
            synchronized (esperando) {
                lista = estado == TextToSpeech.SUCCESS;
                fallida = !lista;
                pendientes = new ArrayList<>(esperando);
                esperando.clear();
            }
            Log.i(TAG, "motor de voz: " + (lista ? "listo, " + tts.getDefaultEngine() : "no arranca"));
            for (Runnable r : pendientes) r.run();
        });
        // por el canal de la música: es el que va al coche por Bluetooth
        tts.setAudioAttributes(
            new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build()
        );
        tts.setOnUtteranceProgressListener(
            new UtteranceProgressListener() {
                @Override
                public void onStart(String id) {
                    avisa(id, "empieza", -1);
                }

                @Override
                public void onDone(String id) {
                    avisa(id, "acaba", -1);
                }

                @Override
                @Deprecated
                public void onError(String id) {
                    avisa(id, "error", -1);
                }

                @Override
                public void onError(String id, int codigo) {
                    avisa(id, "error", -1);
                }

                @Override
                public void onStop(String id, boolean interrumpida) {
                    avisa(id, "callada", -1);
                }

                @Override
                public void onRangeStart(String id, int inicio, int fin, int marco) {
                    avisa(id, "palabra", inicio);
                }
            }
        );
    }

    @Override
    protected void handleOnDestroy() {
        if (tts != null) tts.shutdown();
        getContext().stopService(new Intent(getContext(), VozServicio.class));
        if (instancia == this) instancia = null;
    }

    /** Lo que llega antes de que el motor haya arrancado espera a que arranque. */
    private void cuandoEsteLista(PluginCall call, Runnable r) {
        synchronized (esperando) {
            if (!lista && !fallida) {
                esperando.add(r);
                return;
            }
        }
        if (fallida) {
            call.reject("El teléfono no tiene motor de voz");
            return;
        }
        r.run();
    }

    private void avisa(String id, String que, int inicio) {
        if (!"palabra".equals(que)) Log.d(TAG, "voz " + id + ": " + que);
        JSObject o = new JSObject();
        o.put("id", id);
        o.put("que", que);
        if (inicio >= 0) o.put("inicio", inicio);
        notifyListeners("trozo", o);
    }

    /** Lo tocado en la notificación o en el volante, para la página. */
    static void manda(String accion) {
        VozPlugin p = instancia;
        if (p == null) return;
        Log.i(TAG, "mando: " + accion);
        JSObject o = new JSObject();
        o.put("accion", accion);
        p.notifyListeners("mando", o);
    }

    /* ------------------------------------------------------------ las voces */

    @PluginMethod
    public void voces(PluginCall call) {
        cuandoEsteLista(call, () -> {
            JSArray salida = new JSArray();
            Set<Voice> todas = null;
            try {
                todas = tts.getVoices();
            } catch (Exception e) {
                Log.w(TAG, "sin lista de voces", e);
            }
            Voice porOmision = null;
            try {
                porOmision = tts.getDefaultVoice();
            } catch (Exception ignorada) {
                // hay motores que no la dicen
            }
            Locale es = new Locale("es");
            if (todas != null) {
                for (Voice v : todas) {
                    Set<String> rasgos = v.getFeatures();
                    if (rasgos != null && rasgos.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED)) continue;
                    JSObject o = new JSObject();
                    o.put("id", v.getName());
                    o.put("lengua", v.getLocale().toLanguageTag());
                    o.put("nombre", nombreDe(v, es));
                    o.put("red", v.isNetworkConnectionRequired());
                    o.put("porOmision", porOmision != null && porOmision.getName().equals(v.getName()));
                    salida.put(o);
                }
            }
            Log.i(TAG, "voces: " + salida.length());
            JSObject r = new JSObject();
            r.put("voces", salida);
            call.resolve(r);
        });
    }

    /**
     * Los nombres que da Android son de máquina —es-us-x-esc-local—: se dice
     * la lengua con su país, y detrás la marca de la voz para distinguir las
     * del mismo país; «red» si sólo habla con conexión, que es lo que Ajustes
     * explica.
     */
    private static String nombreDe(Voice v, Locale en) {
        String lengua = v.getLocale().getDisplayName(en);
        if (!lengua.isEmpty()) lengua = lengua.substring(0, 1).toUpperCase(en) + lengua.substring(1);
        String[] partes = v.getName().split("-");
        String marca = partes.length >= 4 ? partes[3] : v.getName();
        return lengua + " · " + marca + (v.isNetworkConnectionRequired() ? " · red" : "");
    }

    /* --------------------------------------------------------------- decir */

    @PluginMethod
    public void di(PluginCall call) {
        final String id = call.getString("id", "");
        final String texto = call.getString("texto", "");
        final String voz = call.getString("voz");
        final String lengua = call.getString("lengua", "es-ES");
        final float vel = call.getFloat("vel", 1f);
        cuandoEsteLista(call, () -> {
            ponVoz(voz, lengua);
            tts.setSpeechRate(Math.max(0.5f, Math.min(2f, vel)));
            int r = tts.speak(texto, TextToSpeech.QUEUE_ADD, new Bundle(), id);
            if (r != TextToSpeech.SUCCESS) avisa(id, "error", -1);
            call.resolve();
        });
    }

    /** La voz elegida, y si no está, la lengua; y si tampoco, el castellano que haya. */
    private void ponVoz(String voz, String lengua) {
        if (voz != null && !voz.equals(vozPuesta)) {
            try {
                for (Voice v : tts.getVoices()) {
                    if (v.getName().equals(voz)) {
                        tts.setVoice(v);
                        vozPuesta = voz;
                        return;
                    }
                }
            } catch (Exception ignorada) {
                // sin lista: se pide por la lengua
            }
        }
        if (voz != null && voz.equals(vozPuesta)) return;
        vozPuesta = null;
        int r = tts.setLanguage(Locale.forLanguageTag(lengua));
        if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
            tts.setLanguage(new Locale("es"));
        }
    }

    /** El silencio entre secciones, dentro de la misma cola: no hace falta que la página despierte para contarlo. */
    @PluginMethod
    public void silencio(PluginCall call) {
        final String id = call.getString("id", "");
        final int ms = call.getInt("ms", 1000);
        cuandoEsteLista(call, () -> {
            tts.playSilentUtterance(Math.max(50, ms), TextToSpeech.QUEUE_ADD, id);
            call.resolve();
        });
    }

    @PluginMethod
    public void calla(PluginCall call) {
        if (tts != null && lista) tts.stop();
        call.resolve();
    }

    /* -------------------------------------------------------------- mandos */

    /**
     * El servicio de los mandos: con estado "sonando" o "pausada" se pone en
     * marcha (o se actualiza) con lo que se está rezando por título; con
     * "parada", se va.
     */
    @PluginMethod
    public void mandos(PluginCall call) {
        String estado = call.getString("estado", "parada");
        Intent i = new Intent(getContext(), VozServicio.class);
        if ("parada".equals(estado)) {
            getContext().stopService(i);
            call.resolve();
            return;
        }
        i.setAction(VozServicio.PON);
        i.putExtra("titulo", call.getString("titulo", ""));
        i.putExtra("artista", call.getString("artista", ""));
        i.putExtra("estado", estado);
        try {
            ContextCompat.startForegroundService(getContext(), i);
            call.resolve();
        } catch (Exception e) {
            // con la app en segundo plano Android no deja arrancarlo: se dice,
            // y la voz sigue sin mandos
            Log.w(TAG, "sin servicio de mandos", e);
            call.reject("No se ha podido poner el servicio: " + e.getMessage());
        }
    }
}
