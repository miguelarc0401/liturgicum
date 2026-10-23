package io.github.miguelarc0401.liturgicum;

import android.view.WindowManager;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * «No apagar la pantalla» de Ajustes. En Chrome lo hace navigator.wakeLock,
 * que el WebView no trae; aquí basta con decírselo a la ventana, que lo
 * mantiene mientras la app esté delante y lo suelta sola al salir.
 */
@CapacitorPlugin(name = "Pantalla")
public class PantallaPlugin extends Plugin {

    @PluginMethod
    public void despierta(PluginCall call) {
        final boolean si = Boolean.TRUE.equals(call.getBoolean("si", true));
        getActivity().runOnUiThread(() -> {
            if (si) getActivity().getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            else getActivity().getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            call.resolve();
        });
    }
}
