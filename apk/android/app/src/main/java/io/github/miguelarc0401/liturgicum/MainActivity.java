package io.github.miguelarc0401.liturgicum;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // los plugins de la propia app (la voz, la pantalla, las voces de
        // Piper en archivos) no van por npm: se apuntan aquí, antes de abrir
        registerPlugin(VozPlugin.class);
        registerPlugin(PantallaPlugin.class);
        registerPlugin(ArchivosPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
