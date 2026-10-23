package io.github.miguelarc0401.liturgicum;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.support.v4.media.MediaMetadataCompat;
import android.support.v4.media.session.MediaSessionCompat;
import android.support.v4.media.session.PlaybackStateCompat;
import android.util.Log;
import androidx.core.app.NotificationCompat;
import androidx.core.app.ServiceCompat;

/**
 * Lo que mantiene la voz en marcha con la pantalla apagada, y los mandos de
 * fuera.
 *
 * Es un servicio en primer plano, con su aviso en la barra de
 * notificaciones: mientras está, Android no duerme la app aunque la
 * pantalla se apague. Lleva una sesión de medios —la que recibe el botón
 * del volante y el de los auriculares, y la que pinta los mandos en la
 * pantalla de bloqueo— y, mientras suena, un audio que no se oye. Android
 * le da los botones de fuera a la app que ha sonado la última, y la voz del
 * sistema no suena desde esta app sino desde el motor de voz, que es otra:
 * sin el audio mudo, el volante iría a la radio o a la música. Es lo mismo
 * que hace la web con su <audio> mudo (app.js, «el audio que no se oye»).
 *
 * No sabe nada de lo que se reza: la página le dice qué poner de título y
 * si suena o está en pausa (VozPlugin.mandos), y él le devuelve lo que se
 * toca (VozPlugin.manda).
 */
public class VozServicio extends Service {

    static final String PON = "pon";
    private static final String CANAL = "voz";
    private static final int AVISO = 1;

    private MediaSessionCompat sesion;
    private PowerManager.WakeLock vela;
    private AudioTrack mudo;
    private AudioManager audio;
    private AudioFocusRequest foco;
    private AudioManager.OnAudioFocusChangeListener oyenteFoco;
    private Bitmap icono;
    private boolean enPrimerPlano = false;

    private String titulo = "Liturgicum";
    private String artista = "";
    private boolean sonando = false;

    @Override
    public void onCreate() {
        super.onCreate();
        audio = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        icono = BitmapFactory.decodeResource(getResources(), R.mipmap.ic_launcher_foreground);

        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && nm.getNotificationChannel(CANAL) == null) {
            NotificationChannel c = new NotificationChannel(CANAL, "Rezar en alta voz", NotificationManager.IMPORTANCE_LOW);
            c.setDescription("Los mandos de la voz mientras se reza");
            c.setShowBadge(false);
            nm.createNotificationChannel(c);
        }

        sesion = new MediaSessionCompat(this, "Liturgicum");
        sesion.setCallback(
            new MediaSessionCompat.Callback() {
                @Override
                public void onPlay() {
                    VozPlugin.manda("sigue");
                }

                @Override
                public void onPause() {
                    VozPlugin.manda("pausa");
                }

                @Override
                public void onStop() {
                    VozPlugin.manda("para");
                }

                @Override
                public void onSkipToNext() {
                    VozPlugin.manda("siguiente");
                }

                @Override
                public void onSkipToPrevious() {
                    VozPlugin.manda("anterior");
                }

                @Override
                public void onFastForward() {
                    VozPlugin.manda("adelante");
                }

                @Override
                public void onRewind() {
                    VozPlugin.manda("atras");
                }
            }
        );
        sesion.setSessionActivity(abreLaApp());
        sesion.setActive(true);

        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        vela = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "liturgicum:voz");
        vela.setReferenceCounted(false);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // Android exige el aviso en cuanto se arranca: antes que nada
        if (!enPrimerPlano) ponEnPrimerPlano();
        if (intent == null) {
            // lo ha vuelto a arrancar el sistema, sin página detrás
            stopSelf();
            return START_NOT_STICKY;
        }
        String accion = intent.getAction();
        if (PON.equals(accion)) {
            titulo = valor(intent.getStringExtra("titulo"), "Liturgicum");
            artista = valor(intent.getStringExtra("artista"), "");
            sonando = "sonando".equals(intent.getStringExtra("estado"));
            aplica();
        } else if (accion != null) {
            // un botón del aviso, en los Android que todavía los pintan
            VozPlugin.manda(accion);
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        // quitada la app de las recientes, la página ya no está: se calla todo
        VozPlugin.manda("para");
        stopSelf();
    }

    @Override
    public void onDestroy() {
        callaElMudo();
        if (vela.isHeld()) vela.release();
        sueltaElFoco();
        sesion.setActive(false);
        sesion.release();
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private static String valor(String s, String siNo) {
        return s == null || s.isEmpty() ? siNo : s;
    }

    /* ---------------------------------------------------------------- estado */

    private void aplica() {
        sesion.setMetadata(
            new MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, titulo)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, artista)
                .putBitmap(MediaMetadataCompat.METADATA_KEY_ART, icono)
                .build()
        );
        sesion.setPlaybackState(
            new PlaybackStateCompat.Builder()
                .setActions(
                    PlaybackStateCompat.ACTION_PLAY |
                    PlaybackStateCompat.ACTION_PAUSE |
                    PlaybackStateCompat.ACTION_PLAY_PAUSE |
                    PlaybackStateCompat.ACTION_STOP |
                    PlaybackStateCompat.ACTION_SKIP_TO_NEXT |
                    PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS |
                    PlaybackStateCompat.ACTION_FAST_FORWARD |
                    PlaybackStateCompat.ACTION_REWIND
                )
                .setState(
                    sonando ? PlaybackStateCompat.STATE_PLAYING : PlaybackStateCompat.STATE_PAUSED,
                    PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN,
                    sonando ? 1f : 0f
                )
                .build()
        );
        ponEnPrimerPlano();
        if (sonando) {
            pideElFoco();
            suenaElMudo();
            // cuatro horas como mucho: un día entero de horas son cuarenta y
            // cuatro minutos, y si algo se queda colgado no gasta la batería
            vela.acquire(4 * 60 * 60 * 1000L);
        } else {
            callaElMudo();
            if (vela.isHeld()) vela.release();
        }
        Log.i(VozPlugin.TAG, "servicio de voz: " + (sonando ? "sonando" : "en pausa") + " · " + titulo);
    }

    private void ponEnPrimerPlano() {
        int tipo = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q ? ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK : 0;
        ServiceCompat.startForeground(this, AVISO, aviso(), tipo);
        enPrimerPlano = true;
    }

    private NotificationCompat.Builder base() {
        return new NotificationCompat.Builder(this, CANAL)
            .setSmallIcon(R.drawable.ic_voz)
            .setLargeIcon(icono)
            .setContentTitle(titulo)
            .setContentText(artista)
            .setContentIntent(abreLaApp())
            .setOnlyAlertOnce(true)
            .setShowWhen(false)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT);
    }

    private android.app.Notification aviso() {
        return base()
            .addAction(android.R.drawable.ic_media_previous, "Sección anterior", boton("anterior", 1))
            .addAction(
                sonando ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play,
                sonando ? "Pausa" : "Seguir",
                boton(sonando ? "pausa" : "sigue", 2)
            )
            .addAction(android.R.drawable.ic_media_next, "Sección siguiente", boton("siguiente", 3))
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Dejar de leer", boton("para", 4))
            .setStyle(
                new androidx.media.app.NotificationCompat.MediaStyle()
                    .setMediaSession(sesion.getSessionToken())
                    .setShowActionsInCompactView(0, 1, 2)
            )
            .setOngoing(sonando)
            .build();
    }

    private PendingIntent boton(String accion, int codigo) {
        Intent i = new Intent(this, VozServicio.class).setAction(accion);
        return PendingIntent.getService(this, codigo, i, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private PendingIntent abreLaApp() {
        Intent i = new Intent(this, MainActivity.class).setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return PendingIntent.getActivity(this, 0, i, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    /* ------------------------------------------------------- el audio mudo */

    /**
     * Medio segundo a 8 kHz con la onda más pequeña que cabe, en bucle: un bit
     * de los dieciséis, que no se oye en ningún altavoz. No es silencio exacto
     * a propósito, como el WAV de la web.
     */
    private void suenaElMudo() {
        if (mudo != null) {
            if (mudo.getPlayState() != AudioTrack.PLAYSTATE_PLAYING) mudo.play();
            return;
        }
        try {
            int hz = 8000;
            int n = hz / 2;
            short[] onda = new short[n];
            for (int i = 0; i < n; i++) onda[i] = (short) (i % 2 == 0 ? 1 : -1);
            mudo = new AudioTrack.Builder()
                .setAudioAttributes(atributos())
                .setAudioFormat(
                    new AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(hz)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setTransferMode(AudioTrack.MODE_STATIC)
                .setBufferSizeInBytes(n * 2)
                .build();
            mudo.write(onda, 0, n);
            mudo.setLoopPoints(0, n, -1);
            mudo.play();
        } catch (Exception e) {
            Log.w(VozPlugin.TAG, "sin audio mudo: el volante puede no llegar", e);
            mudo = null;
        }
    }

    private void callaElMudo() {
        if (mudo == null) return;
        try {
            mudo.stop();
            mudo.release();
        } catch (Exception ignorada) {
            // ya estaba suelto
        }
        mudo = null;
    }

    private static AudioAttributes atributos() {
        return new AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build();
    }

    /* --------------------------------------------------------------- el foco */

    /**
     * Al empezar se pide el audio, como cualquier reproductor: así se calla
     * la música que estuviera sonando. Lo que pase después no se atiende
     * todavía —pausar en una llamada y seguir al colgar— porque el motor de
     * voz y el WebView también suenan, y hay que ver en un teléfono de verdad
     * que no se pisan entre ellos antes de fiarse de esos avisos.
     */
    private void pideElFoco() {
        if (oyenteFoco != null) return;
        oyenteFoco = (cambio) -> Log.i(VozPlugin.TAG, "foco del audio: " + cambio);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            foco = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(atributos())
                .setOnAudioFocusChangeListener(oyenteFoco)
                .build();
            audio.requestAudioFocus(foco);
        } else {
            audio.requestAudioFocus(oyenteFoco, AudioManager.STREAM_MUSIC, AudioManager.AUDIOFOCUS_GAIN);
        }
    }

    private void sueltaElFoco() {
        if (oyenteFoco == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && foco != null) audio.abandonAudioFocusRequest(foco);
        else audio.abandonAudioFocus(oyenteFoco);
        foco = null;
        oyenteFoco = null;
    }
}
