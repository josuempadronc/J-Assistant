"""
J — AI ASSISTANT v2.0
Asistente personal Jarvis con control total del teléfono:
llamadas, SMS, WhatsApp, apps, linterna, batería, alarmas, cámara,
volumen, brillo, clima, contactos + reproductor de música + LLM (Groq).
"""
import os
import math
import json
import re
import ssl
import random
import threading
import urllib.request
import urllib.parse
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import (
    Color, Ellipse, Line, Rectangle, RoundedRectangle,
)
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import NumericProperty, BooleanProperty

# ── Android ───────────────────────────────────────────────────────────────────
try:
    from jnius import autoclass, PythonJavaClass, java_method
    ANDROID = True
except ImportError:
    ANDROID = False

# ── Configuración ─────────────────────────────────────────────────────────────
try:
    from config import GROQ_API_KEY   # archivo local gitignoreado
except ImportError:
    GROQ_API_KEY = ""                 # sin key = modo comandos simples
GROQ_MODEL   = "llama-3.1-8b-instant"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# Mapa de nombres comunes → package de Android
APPS_CONOCIDAS = {
    'whatsapp':      'com.whatsapp',
    'youtube':       'com.google.android.youtube',
    'instagram':     'com.instagram.android',
    'facebook':      'com.facebook.katana',
    'twitter':       'com.twitter.android',
    'x':             'com.twitter.android',
    'maps':          'com.google.android.apps.maps',
    'google':        'com.google.android.googlequicksearchbox',
    'chrome':        'com.android.chrome',
    'spotify':       'com.spotify.music',
    'netflix':       'com.netflix.mediaclient',
    'tiktok':        'com.zhiliaoapp.musically',
    'telegram':      'org.telegram.messenger',
    'gmail':         'com.google.android.gm',
    'drive':         'com.google.android.apps.docs',
    'calendar':      'com.google.android.calendar',
    'calendario':    'com.google.android.calendar',
    'calculadora':   'com.google.android.calculator',
    'calculator':    'com.google.android.calculator',
    'camara':        'com.android.camera2',
    'cámara':        'com.android.camera2',
    'galeria':       'com.google.android.apps.photos',
    'galería':       'com.google.android.apps.photos',
    'fotos':         'com.google.android.apps.photos',
    'configuracion': 'com.android.settings',
    'ajustes':       'com.android.settings',
    'settings':      'com.android.settings',
    'clock':         'com.google.android.deskclock',
    'reloj':         'com.google.android.deskclock',
}

# Frases de personalidad Jarvis — se elige una al azar en cada respuesta
JARVIS = {
    'ok':         ["Entendido, señor.", "Como ordene.", "De acuerdo.", "Por supuesto, señor."],
    'musica_play':["Reproduciendo, señor.", "Iniciando música.", "Como ordene, señor.", "Con gusto."],
    'musica_sig': ["Siguiente pista, señor.", "Cambiando.", "Siguiente.", "Adelante."],
    'musica_ant': ["Pista anterior, señor.", "Volviendo.", "De acuerdo, señor."],
    'musica_pau': ["En pausa, señor.", "Pausando.", "Pausa activada, señor."],
    'musica_stop':["Detenido, señor.", "Música detenida.", "Como ordene, señor."],
    'vol_up':     ["Subiendo el volumen, señor.", "Volumen aumentado.", "Ahí va, señor."],
    'vol_down':   ["Bajando el volumen, señor.", "Volumen reducido.", "Listo, señor."],
    'flash_on':   ["Linterna encendida, señor.", "Iluminando.", "Luz activada, señor."],
    'flash_off':  ["Linterna apagada, señor.", "Luz desactivada.", "Oscureciendo."],
    'bateria':    ["Revisando batería, señor.", "Un momento.", "Comprobando nivel de carga."],
    'llamar':     ["Llamando a {}, señor.", "Conectando con {}.", "Realizando la llamada."],
    'sms':        ["Enviando mensaje a {}, señor.", "Mensaje en camino a {}.", "Enviado, señor."],
    'whatsapp':   ["Enviando WhatsApp a {}, señor.", "Mensaje de WhatsApp en camino a {}."],
    'abrir':      ["Abriendo {}, señor.", "Iniciando {}.", "Ejecutando {}, señor."],
    'alarma':     ["Alarma configurada para las {}, señor.", "Alarma puesta. Descanse, señor."],
    'foto':       ["Capturando foto, señor.", "Tomando fotografía.", "Clic. Listo, señor."],
    'brillo':     ["Brillo al {}%, señor.", "Ajustando brillo a {}%.", "Listo, señor."],
    'volumen':    ["Volumen al {}%, señor.", "Ajustando volumen a {}%.", "Listo."],
    'clima':      ["Consultando el clima, señor.", "Buscando información del tiempo.", "Un momento."],
    'cancion':    ["Reproduciendo {}, señor.", "Poniendo {}.", "Aquí está {}, señor."],
    'no_entiendo':["No he comprendido, señor. Repita la orden.", "Podría repetir eso?",
                   "No entendí, señor. Intente de nuevo.", "No capté la orden, señor."],
    'activado':   ["Sistema J activo. A sus órdenes, señor.", "Listo para asistirle, señor.",
                   "J en línea. Qué necesita, señor?", "A su servicio, señor."],
    'hora':       ["Son las {}, señor.", "La hora actual es {}, señor.", "{}"],
    'fecha':      ["Hoy es {}, señor.", "La fecha de hoy es {}.", "{}, señor."],
    'timer':      ["Temporizador de {} minutos activado, señor.", "Contando {} minutos, señor."],
    'sin_canciones': ["No hay canciones en la biblioteca, señor.", "Biblioteca vacía, señor."],
    'no_cancion': ["No encontré esa canción, señor.", "No la encontré en la biblioteca."],
    'no_contacto':["No encontré ese contacto, señor.", "Contacto no localizado."],
}


# ─────────────────────────────────────────────────────────────────────────────
# ORBE ANIMADO (azul/cian — estética Jarvis)
# ─────────────────────────────────────────────────────────────────────────────
class OrbWidget(Widget):
    angle     = NumericProperty(0)
    angle2    = NumericProperty(0)
    pulse     = NumericProperty(0)
    ray_phase = NumericProperty(0)
    is_playing = BooleanProperty(False)
    _particles = [(i * 37.3, 68 + (i % 4) * 8, 2 + (i % 3)) for i in range(12)]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pulse_dir = 1
        self.bind(pos=self._redraw, size=self._redraw,
                  angle=self._redraw, angle2=self._redraw,
                  pulse=self._redraw, ray_phase=self._redraw,
                  is_playing=self._redraw)
        Clock.schedule_interval(self._tick, 1/30)

    def _tick(self, dt):
        spd = 1.8 if self.is_playing else 0.6
        self.angle     = (self.angle  + dt * 28 * spd) % 360
        self.angle2    = (self.angle2 - dt * 18 * spd) % 360
        self.ray_phase = (self.ray_phase + dt * 2.2) % (2 * math.pi)
        self.pulse += dt * self._pulse_dir * (0.9 if self.is_playing else 0.35)
        if self.pulse >= 1:   self.pulse = 1; self._pulse_dir = -1
        elif self.pulse <= 0: self.pulse = 0; self._pulse_dir =  1

    def _redraw(self, *a):
        self.canvas.clear()
        cx, cy, p = self.center_x, self.center_y, self.pulse
        with self.canvas:
            Color(0.0, 0.4, 1.0, 0.06 + p*0.06)
            d = 160 + p*12
            Ellipse(pos=(cx-d/2, cy-d/2), size=(d, d))

            self._rune_ring(cx, cy, 64, 12, self.angle,
                            (0.2, 0.6, 1.0, 0.45+p*.25))
            Color(0.1, 0.5, 1.0, 0.55+p*.25)
            Line(ellipse=(cx-58, cy-58, 116, 116), width=1.3)

            self._rune_ring(cx, cy, 46, 8, self.angle2,
                            (0.3, 0.7, 1.0, 0.5+p*.3))
            Color(0.1, 0.6, 1.0, 0.6+p*.2)
            Line(ellipse=(cx-44, cy-44, 88, 88), width=1.5)

            self._rays(cx, cy, p)

            rc = 30+p*5
            Color(0.0, 0.15, 0.5, 0.9)
            Ellipse(pos=(cx-rc, cy-rc), size=(rc*2, rc*2))
            r1 = 20+p*4
            Color(0.1, 0.45, 0.9, 0.75)
            Ellipse(pos=(cx-r1, cy-r1), size=(r1*2, r1*2))
            r2 = 10+p*3
            Color(0.4, 0.75, 1.0, 0.9)
            Ellipse(pos=(cx-r2, cy-r2), size=(r2*2, r2*2))
            Color(0.9, 0.97, 1.0, 0.95)
            Ellipse(pos=(cx-5, cy-5), size=(10, 10))
            Color(0.2, 0.6, 1.0, 0.4+p*.4)
            Line(ellipse=(cx-rc, cy-rc, rc*2, rc*2), width=1.2)
            self._particles_draw(cx, cy)

    def _rune_ring(self, cx, cy, r, n, off, col):
        Color(*col)
        for i in range(n):
            a = math.radians(off + i*(360/n))
            rx, ry = cx+r*math.cos(a), cy+r*math.sin(a)
            Line(points=[rx-3*math.sin(a), ry+3*math.cos(a),
                         rx+3*math.sin(a), ry-3*math.cos(a)], width=1.1)
            Line(points=[rx-3, ry, rx+3, ry], width=0.8)

    def _rays(self, cx, cy, p):
        for i, (ba, r0, r1) in enumerate(
            [(90,55,80),(270,55,80),(0,55,80),(180,55,80),
             (45,50,70),(135,50,70),(225,50,70),(315,50,70)]):
            ph = i*0.78
            inten = abs(math.sin(self.ray_phase+ph))
            if inten < 0.2: continue
            alp = inten*(0.5+p*0.4)
            a = math.radians(ba + math.sin(self.ray_phase*2.3+ph)*6)
            x1,y1 = cx+r0*math.cos(a), cy+r0*math.sin(a)
            x2,y2 = cx+(r1+p*10)*math.cos(a), cy+(r1+p*10)*math.sin(a)
            Color(0.1, 0.5, 1.0, alp*.85)
            Line(points=[x1,y1,x2,y2], width=1.4)
            m = 0.55
            Color(0.5, 0.85, 1.0, alp*.5)
            Line(points=[x1+(x2-x1)*m, y1+(y2-y1)*m, x2, y2], width=0.8)

    def _particles_draw(self, cx, cy):
        t = self.ray_phase
        for i, (ba, br, sz) in enumerate(self._particles):
            a = math.radians(ba + self.angle*0.4 + i*5)
            r = br + math.sin(t*0.8+i*1.1)*8
            px, py = cx+r*math.cos(a), cy+r*math.sin(a)
            alp = 0.3+0.5*abs(math.sin(t*0.6+i*0.9))
            Color(0.3, 0.7, 1.0, alp) if i%3==0 else Color(0.6, 0.9, 1.0, alp*.7)
            Ellipse(pos=(px-sz/2, py-sz/2), size=(sz, sz))


# ─────────────────────────────────────────────────────────────────────────────
# BARRA DE PROGRESO
# ─────────────────────────────────────────────────────────────────────────────
class ProgressWidget(Widget):
    progress = NumericProperty(0.0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._rd, size=self._rd, progress=self._rd)
    def _rd(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(0.05, 0.1, 0.3, 0.45)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[3])
            Color(0.1, 0.4, 0.8, 0.32)
            Line(rounded_rectangle=[self.x,self.y,self.width,self.height,3], width=0.8)
            fw = max(self.progress*self.width, 0)
            if fw > 0:
                Color(0.2, 0.6, 1.0, 0.92)
                RoundedRectangle(pos=self.pos, size=(fw, self.height), radius=[3])
                Color(0.7, 0.9, 1.0, 1)
                dot = 8
                Ellipse(pos=(self.x+fw-dot/2, self.center_y-dot/2), size=(dot,dot))
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.progress = (touch.x-self.x)/self.width
            App.get_running_app().seek(self.progress)
            return True


# ─────────────────────────────────────────────────────────────────────────────
# ÍTEM DE CANCIÓN
# ─────────────────────────────────────────────────────────────────────────────
class SongItem(Button):
    """Item minimalista sin canvas custom para no bloquear el UI thread."""
    def __init__(self, nombre, indice, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.nombre          = nombre
        self.indice          = indice
        self.app_ref         = app_ref
        self.text            = nombre
        self.font_size       = '11sp'
        self.halign          = 'left'
        self.text_size       = (None, None)
        self.size_hint_y     = None
        self.height          = '34dp'
        self.background_normal  = ''
        self.background_color   = (0.04, 0.08, 0.25, 0.85)
        self.color           = (0.78, 0.78, 0.78, 1)
        self.bind(on_press=lambda *_: self.app_ref.reproducir_indice(self.indice))

    def set_activo(self, v):
        if v:
            self.background_color = (0.05, 0.2, 0.55, 0.95)
            self.color = (0.5, 0.9, 1.0, 1)
            self.bold  = True
            self.text  = f'> {self.nombre}'
        else:
            self.background_color = (0.04, 0.08, 0.25, 0.85)
            self.color = (0.78, 0.78, 0.78, 1)
            self.bold  = False
            self.text  = self.nombre


# ─────────────────────────────────────────────────────────────────────────────
# ANDROID: CLASES JAVA
# ─────────────────────────────────────────────────────────────────────────────
if ANDROID:
    class JVoiceListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']
        __javacontext__ = 'app'
        def __init__(self, app_ref):
            super().__init__(); self.app_ref = app_ref
        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, p):
            Clock.schedule_once(lambda dt: self.app_ref._set_mic_ui(True,'ESCUCHANDO...'), 0)
        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            SR = autoclass('android.speech.SpeechRecognizer')
            m = results.getStringArrayList(SR.RESULTS_RECOGNITION)
            if m and m.size() > 0:
                t = m.get(0)
                Clock.schedule_once(lambda dt,x=t: self.app_ref.procesar_voz(x), 0)
        @java_method('(I)V')
        def onError(self, error):
            Clock.schedule_once(lambda dt: self.app_ref._on_voice_error(error), 0)
        @java_method('()V')
        def onBeginningOfSpeech(self): pass
        @java_method('()V')
        def onEndOfSpeech(self): pass
        @java_method('(F)V')
        def onRmsChanged(self, rms): pass
        @java_method('([B)V')
        def onBufferReceived(self, buf): pass
        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, pr): pass
        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, et, p): pass

    class JTTSListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
        __javacontext__ = 'app'
        def __init__(self, app_ref):
            super().__init__(); self.app_ref = app_ref
        @java_method('(I)V')
        def onInit(self, status):
            Clock.schedule_once(lambda dt,s=status: self.app_ref._tts_ready(s), 0)

    class _Runnable(PythonJavaClass):
        __javainterfaces__ = ['java/lang/Runnable']
        __javacontext__ = 'app'
        def __init__(self, fn):
            super().__init__(); self._fn = fn
        @java_method('()V')
        def run(self): self._fn()


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
class J_Layout(BoxLayout):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# APP PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
class J_App(App):

    def build(self):
        Window.clearcolor = (0.01, 0.02, 0.08, 1)
        Builder.load_file('j.kv')

        self.carpeta_musica = "/storage/emulated/0/Music"
        self.sonido_actual  = None
        self.lista_musica   = []
        self.indice_actual  = 0
        self.en_pausa       = False
        self.song_items     = []
        self.mic_activo     = False
        self._recognizer    = None
        self._tts           = None
        self._tts_listo     = False
        self._flash_on      = False
        self._wake_lock     = None
        self._batch_idx     = 0

        self.root_widget = J_Layout()
        Clock.schedule_interval(self._tick_progreso, 0.5)

        if ANDROID:
            Clock.schedule_once(self._pedir_permisos, 0.6)
            Clock.schedule_once(self._init_tts, 1.2)
        else:
            Clock.schedule_once(self.cargar_biblioteca, 0.8)

        return self.root_widget

    # ══════════════════════════════════════════════════════════════════════════
    # TTS
    # ══════════════════════════════════════════════════════════════════════════

    def _init_tts(self, dt=0):
        try:
            PA  = autoclass('org.kivy.android.PythonActivity')
            TTS = autoclass('android.speech.tts.TextToSpeech')
            self._tts_listener = JTTSListener(self)
            self._tts = TTS(PA.mActivity, self._tts_listener)
        except Exception:
            self._tts_listo = False

    def _tts_ready(self, status):
        try:
            TTS    = autoclass('android.speech.tts.TextToSpeech')
            Locale = autoclass('java.util.Locale')
            if status == TTS.SUCCESS:
                # Intentar español; fallback al idioma del dispositivo
                r = self._tts.setLanguage(Locale("es", "ES"))
                if r < 0:   # LANG_MISSING_DATA o LANG_NOT_SUPPORTED
                    r = self._tts.setLanguage(Locale("es"))
                if r < 0:
                    self._tts.setLanguage(Locale.getDefault())
                self._tts_listo = True
                self._set_status('TTS LISTO')
                Clock.schedule_once(lambda dt: self._hablar("J en linea."), 0.8)
            else:
                self._set_status('TTS ERROR: ' + str(status))
                self._tts_listo = False
        except Exception as e:
            self._set_status('TTS INIT ERR: ' + str(e)[:20])
            self._tts_listo = False

    def _hablar(self, texto):
        self._set_j_response(texto)
        if ANDROID and self._tts_listo and self._tts:
            try:
                TTS     = autoclass('android.speech.tts.TextToSpeech')
                Bundle  = autoclass('android.os.Bundle')
                JString = autoclass('java.lang.String')
                params  = Bundle()
                # JString explícito para que Pyjnius resuelva el overload CharSequence
                self._tts.speak(JString(texto), TTS.QUEUE_FLUSH, params, "J")
            except Exception as e:
                self._set_status('TTS ERR: ' + str(e)[:30])

    # ══════════════════════════════════════════════════════════════════════════
    # BIBLIOTECA
    # ══════════════════════════════════════════════════════════════════════════

    def cargar_biblioteca(self, dt=0):
        self._set_status('ESCANEANDO...')
        threading.Thread(target=self._escanear_bg, daemon=True).start()

    def _escanear_bg(self):
        archivos = self._escanear_musica_android() if ANDROID else self._escanear_local()
        Clock.schedule_once(lambda dt, a=archivos: self._poblar_biblioteca(a), 0)

    def _poblar_biblioteca(self, archivos):
        grid = self.root_widget.ids.lista_grid
        grid.clear_widgets()
        self.song_items.clear()
        self._batch_idx = 0

        self.lista_musica = archivos or ["Demo — Sin Señal.mp3", "Protocolo J.mp3"]
        total = len(self.lista_musica)
        self.root_widget.ids.lbl_biblioteca.text = f'BIBLIOTECA: {total} TEMAS'
        if self.lista_musica:
            self._actualizar_ui_cancion()
            self._set_status('CARGANDO LISTA...')
        Clock.schedule_once(self._poblar_batch, 0)

    def _poblar_batch(self, dt):
        BATCH = 12
        grid  = self.root_widget.ids.lista_grid
        fin   = min(self._batch_idx + BATCH, len(self.lista_musica))
        for i in range(self._batch_idx, fin):
            ruta = self.lista_musica[i]
            item = SongItem(nombre=os.path.basename(ruta), indice=i, app_ref=self)
            grid.add_widget(item)
            self.song_items.append(item)
        self._batch_idx = fin
        if fin < len(self.lista_musica):
            Clock.schedule_once(self._poblar_batch, 0.04)
        else:
            self._set_status('SISTEMAS LISTOS')

    def _escanear_local(self):
        if not os.path.exists(self.carpeta_musica):
            return []
        return sorted([
            os.path.join(self.carpeta_musica, f)
            for f in os.listdir(self.carpeta_musica)
            if f.lower().endswith(('.mp3','.ogg','.wav','.flac','.m4a'))
        ])

    def _escanear_musica_android(self):
        """Usa MediaStore (índice del SO) para encontrar música; fallback a filesystem."""
        # ── 1. MediaStore ─────────────────────────────────────────────────────
        try:
            PA       = autoclass('org.kivy.android.PythonActivity')
            Media    = autoclass('android.provider.MediaStore$Audio$Media')
            uri      = Media.EXTERNAL_CONTENT_URI
            resolver = PA.mActivity.getContentResolver()
            cursor   = resolver.query(uri, None, 'is_music=1', None, 'title ASC')
            archivos = []
            if cursor and cursor.moveToFirst():
                col = cursor.getColumnIndex('_data')
                while True:
                    path = cursor.getString(col)
                    if path and '/Android/' not in path and os.path.isfile(path):
                        archivos.append(path)
                    if not cursor.moveToNext():
                        break
                cursor.close()
            if archivos:
                return archivos[:100]
        except Exception:
            pass

        # ── 2. Fallback: filesystem 3 niveles ─────────────────────────────────
        EXT  = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.opus')
        DIRS = ["/storage/emulated/0/Music", "/storage/emulated/0/music",
                "/storage/emulated/0/Musica", "/storage/emulated/0/Download",
                "/storage/emulated/0/Downloads", "/sdcard/Music", "/sdcard/Download"]
        archivos, seen = [], set()

        def _scan(path, depth):
            if depth > 3 or '/Android/' in path: return
            try:
                for e in os.listdir(path):
                    ruta = os.path.join(path, e)
                    if e.lower().endswith(EXT):
                        k = os.path.realpath(ruta)
                        if k not in seen: seen.add(k); archivos.append(ruta)
                    elif os.path.isdir(ruta) and not e.startswith('.'):
                        _scan(ruta, depth + 1)
            except Exception:
                pass

        for d in DIRS:
            if os.path.exists(d): _scan(d, 1)
        return sorted(archivos, key=lambda x: os.path.basename(x).lower())[:100]

    def _actualizar_ui_cancion(self):
        nombre = self.lista_musica[self.indice_actual]
        self.root_widget.ids.lbl_cancion.text = os.path.basename(nombre).rsplit('.',1)[0]
        for i, item in enumerate(self.song_items):
            item.set_activo(i == self.indice_actual)

    # ══════════════════════════════════════════════════════════════════════════
    # CONTROLES DE MÚSICA
    # ══════════════════════════════════════════════════════════════════════════

    def reproducir(self):
        if not self.lista_musica: return
        if self.en_pausa and self.sonido_actual:
            self.sonido_actual.play(); self.en_pausa = False
            self._set_status('▶ REPRODUCIENDO')
            self.root_widget.ids.orb.is_playing = True; return
        self._cargar_y_play()

    def reproducir_indice(self, i):
        self.indice_actual = i; self.en_pausa = False
        if self.sonido_actual: self.sonido_actual.stop(); self.sonido_actual = None
        self._cargar_y_play()

    def _cargar_y_play(self):
        if self.sonido_actual: self.sonido_actual.stop(); self.sonido_actual = None
        ruta = self.lista_musica[self.indice_actual]
        if not os.path.isabs(ruta): ruta = os.path.join(self.carpeta_musica, ruta)
        if not os.path.exists(ruta):
            self._set_status('▶ MODO DEMO')
            self._actualizar_ui_cancion()
            self.root_widget.ids.orb.is_playing = True; return
        self.sonido_actual = SoundLoader.load(ruta)
        if self.sonido_actual:
            self.sonido_actual.volume = self.root_widget.ids.vol_slider.value
            self.sonido_actual.bind(on_stop=self._on_fin)
            self.sonido_actual.play(); self.en_pausa = False
            self._set_status('▶ REPRODUCIENDO')
            self._actualizar_ui_cancion()
            self.root_widget.ids.orb.is_playing = True

    def pausar(self):
        if self.sonido_actual and not self.en_pausa:
            self.sonido_actual.stop(); self.en_pausa = True
            self._set_status('⏸ EN PAUSA')
            self.root_widget.ids.orb.is_playing = False

    def detener(self):
        if self.sonido_actual: self.sonido_actual.stop(); self.sonido_actual = None
        self.en_pausa = False; self._set_status('⏹ DETENIDO')
        self.root_widget.ids.orb.is_playing = False
        self.root_widget.ids.prog_widget.progress = 0

    def siguiente(self):
        if not self.lista_musica: return
        self.indice_actual = (self.indice_actual+1) % len(self.lista_musica)
        self.en_pausa = False
        if self.sonido_actual: self.sonido_actual.stop(); self.sonido_actual = None
        self._cargar_y_play()

    def anterior(self):
        if not self.lista_musica: return
        self.indice_actual = (self.indice_actual-1) % len(self.lista_musica)
        self.en_pausa = False
        if self.sonido_actual: self.sonido_actual.stop(); self.sonido_actual = None
        self._cargar_y_play()

    def _on_fin(self, *_):
        Clock.schedule_once(lambda dt: self.siguiente(), 0.5)

    def _tick_progreso(self, dt):
        if self.sonido_actual and self.sonido_actual.state == 'play':
            dur = self.sonido_actual.length
            pos = self.sonido_actual.get_pos()
            if dur and dur > 0:
                self.root_widget.ids.prog_widget.progress = pos/dur
                self.root_widget.ids.lbl_tiempo.text   = self._fmt(pos)
                self.root_widget.ids.lbl_duracion.text = self._fmt(dur)

    def seek(self, p):
        if self.sonido_actual and self.sonido_actual.length:
            self.sonido_actual.seek(p * self.sonido_actual.length)

    def cambiar_volumen(self, slider, val):
        if self.sonido_actual: self.sonido_actual.volume = val

    @staticmethod
    def _fmt(s):
        s = int(s); return f'{s//60}:{s%60:02d}'

    # ══════════════════════════════════════════════════════════════════════════
    # VOZ
    # ══════════════════════════════════════════════════════════════════════════

    def toggle_microfono(self):
        self.mic_activo = not self.mic_activo
        if self.mic_activo:
            self.root_widget.ids.btn_mic.text = '( * )  J: ACTIVO'
            self._set_mic_ui(True, 'INICIANDO...')
            if ANDROID:
                self._adquirir_wakelock()
                self._iniciar_reconocimiento()
                # J saluda al activarse
                Clock.schedule_once(lambda dt: self._hablar(self._j('activado')), 0.5)
            else:
                self._set_mic_ui(True, 'MODO PC — SIN MIC REAL')
        else:
            self.root_widget.ids.btn_mic.text = '( o )  ACTIVAR J'
            self._set_mic_ui(False, 'MICROFONO INACTIVO')
            if ANDROID:
                self._liberar_wakelock()
                self._detener_reconocimiento()
                Clock.schedule_once(lambda dt: self._hablar('Hasta luego, señor.'), 0)

    def _set_mic_ui(self, activo, texto):
        lbl  = self.root_widget.ids.lbl_mic_status
        lbl2 = self.root_widget.ids.lbl_mic_comando
        lbl.text  = texto
        lbl.color = (0.3,0.7,1.0,1) if activo else (0.45,0.45,0.45,1)
        lbl2.text  = 'habla con J: llama, WhatsApp, apps, música, clima...' if activo \
                     else 'di cualquier cosa a J'
        lbl2.color = (0.2,0.6,1.0,0.9) if activo else (0.3,0.3,0.5,0.8)

    def _iniciar_reconocimiento(self):
        try:
            Handler = autoclass('android.os.Handler')
            Looper  = autoclass('android.os.Looper')
            Handler(Looper.getMainLooper()).post(_Runnable(self._setup_recognizer))
        except Exception as e:
            self._set_mic_ui(False, f'MIC ERROR: {str(e)[:28]}')
            self.mic_activo = False

    def _setup_recognizer(self):
        try:
            if self._recognizer:
                try: self._recognizer.stopListening(); self._recognizer.destroy()
                except: pass
                self._recognizer = None
            PA  = autoclass('org.kivy.android.PythonActivity')
            SR  = autoclass('android.speech.SpeechRecognizer')
            Int = autoclass('android.content.Intent')
            RI  = autoclass('android.speech.RecognizerIntent')
            act = PA.mActivity
            self._recognizer = SR.createSpeechRecognizer(act)
            self._vl = JVoiceListener(self)
            self._recognizer.setRecognitionListener(self._vl)
            intent = Int(RI.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RI.EXTRA_LANGUAGE, "es")
            intent.putExtra(RI.EXTRA_LANGUAGE_PREFERENCE, "es")
            intent.putExtra(RI.EXTRA_MAX_RESULTS, 5)
            intent.putExtra(RI.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500)
            intent.putExtra(RI.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 300)
            intent.putExtra(RI.EXTRA_CALLING_PACKAGE, act.getPackageName())
            self._recognizer.startListening(intent)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e):
                self._set_mic_ui(False, f'MIC ERROR: {err[:28]}'), 0)
            Clock.schedule_once(lambda dt: setattr(self,'mic_activo',False), 0)

    def _detener_reconocimiento(self):
        if not self._recognizer: return
        rec = self._recognizer; self._recognizer = None
        try:
            Handler = autoclass('android.os.Handler')
            Looper  = autoclass('android.os.Looper')
            def _stop():
                try: rec.stopListening(); rec.destroy()
                except: pass
            Handler(Looper.getMainLooper()).post(_Runnable(_stop))
        except: pass

    def _on_voice_error(self, error):
        # 6=NO_MATCH, 7=SPEECH_TIMEOUT, 5=CLIENT — todos reinician silenciosamente
        # 1=NETWORK, 2=NETWORK_TIMEOUT — reiniciar después de 3s
        # 3=AUDIO, 4=SERVER — reiniciar después de 2s
        if not self.mic_activo:
            return
        if error in (6, 7, 5):
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 0.8)
        elif error in (1, 2):
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 3.0)
        elif error in (3, 4):
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 2.0)
        else:
            self._set_mic_ui(True, f'ERR {error} — reintentando...')
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 2.0)

    # ══════════════════════════════════════════════════════════════════════════
    # LLM (GROQ) — CEREBRO DE J
    # ══════════════════════════════════════════════════════════════════════════

    def procesar_voz(self, texto: str):
        self._set_mic_ui(True, f'"{texto[:24]}"')
        # Local siempre primero. Groq solo si hay key Y el comando local falló.
        handled = self._cmd_local(texto.lower().strip())
        if not handled and GROQ_API_KEY and GROQ_API_KEY != "TU_API_KEY_AQUI":
            self._set_status('J PROCESANDO...')
            threading.Thread(target=self._llamar_groq, args=(texto,), daemon=True).start()
        elif not handled:
            self._hablar(self._j('no_entiendo'))
            self._auto_reiniciar()

    def _llamar_groq(self, texto):
        try:
            payload = json.dumps({
                'model':    GROQ_MODEL,
                'messages': [
                    {'role':'system', 'content': self._system_prompt()},
                    {'role':'user',   'content': texto},
                ],
                'max_tokens':  100,
                'temperature': 0.6,
            }).encode('utf-8')
            req = urllib.request.Request(
                GROQ_URL, data=payload, method='POST',
                headers={'Authorization': f'Bearer {GROQ_API_KEY}',
                         'Content-Type': 'application/json'})
            # SSL context sin verificación (necesario en p4a/Android sin CA bundle)
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
                data = json.loads(r.read().decode('utf-8'))
                resp = data['choices'][0]['message']['content'].strip()
                Clock.schedule_once(lambda dt, x=resp: self._on_llm(x), 0)
        except Exception as e:
            err = str(e)[:35]
            Clock.schedule_once(lambda dt, m=err: self._set_status(f'GROQ: {m}'), 0)
            Clock.schedule_once(lambda dt: self._hablar(self._j('no_entiendo')), 0)
            Clock.schedule_once(lambda dt: self._auto_reiniciar(), 0.1)

    def _on_llm(self, respuesta):
        match = re.search(r'\[CMD:([^\]]+)\]', respuesta)
        accion, params = None, []
        if match:
            partes = match.group(1).split('|')
            accion = partes[0]
            params = partes[1:] if len(partes) > 1 else []
        texto_limpio = re.sub(r'\[CMD:[^\]]+\]\s*', '', respuesta).strip()
        self._hablar(texto_limpio)
        if accion:
            Clock.schedule_once(lambda dt, a=accion, p=params:
                self._ejecutar(a, p), 0.3)
        self._auto_reiniciar(3.0)

    def _system_prompt(self):
        n  = len(self.lista_musica)
        cn = os.path.basename(self.lista_musica[self.indice_actual]).rsplit('.',1)[0] \
             if self.lista_musica else '—'
        st = ('reproduciendo' if (self.sonido_actual and not self.en_pausa)
              else 'en pausa' if self.en_pausa else 'detenido')
        return f"""Eres J, asistente personal de IA con control total del teléfono Android, como Jarvis de Iron Man.
Respondes SIEMPRE en español. Máximo 1 oración corta. Sin emojis. Tono directo y confiado.

Para ejecutar cualquier acción incluye al INICIO de tu respuesta: [CMD:accion|param1|param2]

COMANDOS DISPONIBLES:
Música : [CMD:reproducir] [CMD:pausar] [CMD:detener] [CMD:siguiente] [CMD:anterior] [CMD:subir_vol] [CMD:bajar_vol]
Llamar : [CMD:llamar|nombre_o_numero]
SMS    : [CMD:sms|nombre_o_numero|texto del mensaje]
WhatsApp: [CMD:whatsapp|nombre_o_numero|texto del mensaje]
Abrir app: [CMD:abrir|nombre]  (youtube, instagram, maps, chrome, spotify, netflix, telegram...)
Alarma : [CMD:alarma|hora|minuto]   ej: [CMD:alarma|7|30]
Foto   : [CMD:foto]
Linterna: [CMD:flash|on]  o  [CMD:flash|off]
Batería: [CMD:bateria]
Volumen: [CMD:volumen|0_a_100]
Brillo : [CMD:brillo|0_a_100]
Clima  : [CMD:clima|ciudad]

Estado: música={n} canciones | actual={cn} | {st}
Responde lo que el usuario preguntó y ejecuta el comando apropiado."""

    # ══════════════════════════════════════════════════════════════════════════
    # EJECUTAR ACCIONES (CONTROL TOTAL DEL TELÉFONO)
    # ══════════════════════════════════════════════════════════════════════════

    def _ejecutar(self, accion, params=None):
        params = params or []

        # — Música —
        if   accion == 'reproducir': self.reproducir()
        elif accion == 'pausar':     self.pausar()
        elif accion == 'detener':    self.detener()
        elif accion == 'siguiente':  self.siguiente()
        elif accion == 'anterior':   self.anterior()
        elif accion == 'subir_vol':
            s = self.root_widget.ids.vol_slider
            s.value = min(s.value + 0.15, 1.0)
        elif accion == 'bajar_vol':
            s = self.root_widget.ids.vol_slider
            s.value = max(s.value - 0.15, 0.0)

        # — Teléfono / Mensajes —
        elif accion == 'llamar' and params:
            threading.Thread(target=self._hacer_llamada, args=(params[0],), daemon=True).start()
        elif accion == 'sms' and len(params) >= 2:
            threading.Thread(target=self._enviar_sms,
                             args=(params[0], '|'.join(params[1:])), daemon=True).start()
        elif accion == 'whatsapp' and len(params) >= 2:
            threading.Thread(target=self._enviar_whatsapp,
                             args=(params[0], '|'.join(params[1:])), daemon=True).start()

        # — Apps —
        elif accion == 'abrir' and params:
            threading.Thread(target=self._abrir_app, args=(params[0],), daemon=True).start()

        # — Sistema —
        elif accion == 'alarma':
            h = int(params[0]) if params else 7
            m = int(params[1]) if len(params) > 1 else 0
            self._set_alarma(h, m)
        elif accion == 'foto':
            self._tomar_foto()
        elif accion == 'flash':
            on = (params[0].lower() == 'on') if params else True
            threading.Thread(target=self._toggle_flash, args=(on,), daemon=True).start()
        elif accion == 'bateria':
            threading.Thread(target=self._check_bateria, daemon=True).start()
        elif accion == 'volumen' and params:
            self._set_volumen(int(params[0]))
        elif accion == 'brillo' and params:
            self._set_brillo(int(params[0]))
        elif accion == 'clima' and params:
            ciudad = params[0]
            threading.Thread(target=self._get_clima, args=(ciudad,), daemon=True).start()

    # ── Llamadas ─────────────────────────────────────────────────────────────

    def _hacer_llamada(self, destino):
        try:
            numero = self._resolver_numero(destino)
            if not numero:
                Clock.schedule_once(lambda dt: self._hablar(f"No encontré el contacto."), 0)
                return
            PA     = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri    = autoclass('android.net.Uri')
            intent = Intent(Intent.ACTION_CALL, Uri.parse(f"tel:{numero}"))
            PA.mActivity.startActivity(intent)
            Clock.schedule_once(lambda dt: self._hablar("Llamando."), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("Error al llamar."), 0)

    # ── SMS ──────────────────────────────────────────────────────────────────

    def _enviar_sms(self, destino, mensaje):
        try:
            numero = self._resolver_numero(destino)
            if not numero:
                Clock.schedule_once(lambda dt: self._hablar("No encontré el número."), 0)
                return
            SmsManager = autoclass('android.telephony.SmsManager')
            SmsManager.getDefault().sendTextMessage(numero, None, mensaje, None, None)
            Clock.schedule_once(lambda dt: self._hablar("Mensaje enviado."), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("Error al enviar SMS."), 0)

    # ── WhatsApp ─────────────────────────────────────────────────────────────

    def _enviar_whatsapp(self, destino, mensaje):
        try:
            numero = self._resolver_numero(destino)
            if not numero:
                Clock.schedule_once(lambda dt: self._hablar("No encontré el contacto."), 0)
                return
            num_limpio = re.sub(r'\D', '', numero)
            PA     = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri    = autoclass('android.net.Uri')
            url    = f"https://wa.me/{num_limpio}?text={urllib.parse.quote(mensaje)}"
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            PA.mActivity.startActivity(intent)
            Clock.schedule_once(lambda dt: self._hablar("Abriendo WhatsApp."), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("Error con WhatsApp."), 0)

    # ── Contactos ────────────────────────────────────────────────────────────

    def _resolver_numero(self, texto):
        if re.match(r'^[\d\+\-\s\(\)]+$', texto):
            return re.sub(r'\D', '', texto)
        if ANDROID:
            return self._buscar_contacto(texto)
        return None

    def _buscar_contacto(self, nombre):
        try:
            PA       = autoclass('org.kivy.android.PythonActivity')
            Phone    = autoclass('android.provider.ContactsContract$CommonDataKinds$Phone')
            cr       = PA.mActivity.getContentResolver()
            cursor   = cr.query(Phone.CONTENT_URI, None,
                                "display_name LIKE ?", [f"%{nombre}%"], None)
            if cursor and cursor.moveToFirst():
                col    = cursor.getColumnIndex('number')
                numero = cursor.getString(col)
                cursor.close()
                return numero
            if cursor: cursor.close()
        except Exception:
            pass
        return None

    # ── Abrir aplicaciones ───────────────────────────────────────────────────

    def _abrir_app(self, nombre):
        try:
            PA = autoclass('org.kivy.android.PythonActivity')
            pm = PA.mActivity.getPackageManager()
            pkg = APPS_CONOCIDAS.get(nombre.lower())

            if not pkg:
                Intent   = autoclass('android.content.Intent')
                apps_lst = pm.queryIntentActivities(
                    Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0)
                for info in apps_lst.toArray():
                    label = str(pm.getApplicationLabel(info.activityInfo.applicationInfo))
                    if nombre.lower() in label.lower():
                        pkg = info.activityInfo.packageName; break

            if pkg:
                launch = pm.getLaunchIntentForPackage(pkg)
                if launch:
                    PA.mActivity.startActivity(launch)
                    Clock.schedule_once(lambda dt: self._hablar(f"Abriendo {nombre}."), 0)
                    return
            Clock.schedule_once(lambda dt: self._hablar(f"No encontré {nombre}."), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("Error al abrir la app."), 0)

    # ── Alarma ───────────────────────────────────────────────────────────────

    def _set_alarma(self, hora, minuto):
        try:
            PA         = autoclass('org.kivy.android.PythonActivity')
            Intent     = autoclass('android.content.Intent')
            AlarmClock = autoclass('android.provider.AlarmClock')
            intent = Intent(AlarmClock.ACTION_SET_ALARM)
            intent.putExtra(AlarmClock.EXTRA_HOUR, hora)
            intent.putExtra(AlarmClock.EXTRA_MINUTES, minuto)
            intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True)
            PA.mActivity.startActivity(intent)
            self._hablar(f"Alarma a las {hora}:{minuto:02d}.")
        except Exception:
            self._hablar("Error al poner la alarma.")

    # ── Cámara ───────────────────────────────────────────────────────────────

    def _tomar_foto(self):
        try:
            PA         = autoclass('org.kivy.android.PythonActivity')
            Intent     = autoclass('android.content.Intent')
            MediaStore = autoclass('android.provider.MediaStore')
            PA.mActivity.startActivity(Intent(MediaStore.ACTION_IMAGE_CAPTURE))
            self._hablar("Abriendo cámara.")
        except Exception:
            self._hablar("Error al abrir la cámara.")

    # ── Linterna ─────────────────────────────────────────────────────────────

    def _toggle_flash(self, on):
        try:
            PA = autoclass('org.kivy.android.PythonActivity')
            cm = PA.mActivity.getSystemService('camera')
            cm.setTorchMode(cm.getCameraIdList()[0], on)
            self._flash_on = on
            Clock.schedule_once(lambda dt: self._hablar(
                "Linterna encendida." if on else "Linterna apagada."), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("Error con la linterna."), 0)

    # ── Batería ──────────────────────────────────────────────────────────────

    def _check_bateria(self):
        try:
            PA  = autoclass('org.kivy.android.PythonActivity')
            BM  = autoclass('android.os.BatteryManager')
            bm  = PA.mActivity.getSystemService('batterymanager')
            pct = bm.getIntProperty(BM.BATTERY_PROPERTY_CAPACITY)
            Clock.schedule_once(lambda dt, n=pct:
                self._hablar(f"Batería al {n} por ciento."), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("No pude leer la batería."), 0)

    # ── Volumen del sistema ───────────────────────────────────────────────────

    def _set_volumen(self, pct):
        try:
            PA = autoclass('org.kivy.android.PythonActivity')
            AM = autoclass('android.media.AudioManager')
            am = PA.mActivity.getSystemService('audio')
            mx = am.getStreamMaxVolume(AM.STREAM_MUSIC)
            am.setStreamVolume(AM.STREAM_MUSIC, int(mx * pct / 100), 0)
            self._hablar(f"Volumen al {pct} por ciento.")
        except Exception:
            self._hablar("Error al cambiar el volumen.")

    # ── Brillo ───────────────────────────────────────────────────────────────

    def _set_brillo(self, pct):
        try:
            PA  = autoclass('org.kivy.android.PythonActivity')
            win = PA.mActivity.getWindow()
            lp  = win.getAttributes()
            lp.screenBrightness = max(0.01, min(1.0, pct / 100.0))
            win.setAttributes(lp)
            self._hablar(f"Brillo al {pct} por ciento.")
        except Exception:
            self._hablar("Error al cambiar el brillo.")

    # ── Clima ─────────────────────────────────────────────────────────────────

    def _get_clima(self, ciudad):
        try:
            url = f"https://wttr.in/{urllib.parse.quote(ciudad)}?format=3&lang=es"
            req = urllib.request.Request(url, headers={'User-Agent': 'J-Assistant/2.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                texto = r.read().decode('utf-8').strip()
                Clock.schedule_once(lambda dt, t=texto: self._hablar(t), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._hablar("No pude obtener el clima."), 0)

    # ══════════════════════════════════════════════════════════════════════════
    # CEREBRO LOCAL — JARVIS SIN INTERNET
    # ══════════════════════════════════════════════════════════════════════════

    def _j(self, key, *args):
        """Elige una frase Jarvis aleatoria para la clave dada."""
        frases = JARVIS.get(key, JARVIS['ok'])
        f = random.choice(frases)
        try:
            return f.format(*args) if args else f
        except Exception:
            return f

    def _auto_reiniciar(self, delay=2.0):
        """Reinicia el micrófono para escucha continua."""
        if ANDROID and self.mic_activo:
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), delay)

    def _buscar_cancion(self, query):
        """Busca una canción por nombre aproximado en la biblioteca."""
        if not self.lista_musica:
            return -1
        q = query.lower()
        for i, ruta in enumerate(self.lista_musica):
            n = os.path.basename(ruta).lower()
            if q in n:
                return i
        # Coincidencia parcial: primeras 4 letras
        if len(q) >= 4:
            for i, ruta in enumerate(self.lista_musica):
                if os.path.basename(ruta).lower().startswith(q[:4]):
                    return i
        return -1

    def _cmd_local(self, t):
        """Procesador de comandos local completo. Retorna True si manejó el comando."""

        # ── Hora ─────────────────────────────────────────────────────────
        if any(p in t for p in ['qué hora','que hora','hora es','dime la hora','qué horas son']):
            hora = datetime.now().strftime('%H:%M')
            self._hablar(self._j('hora', hora))
            self._auto_reiniciar(); return True

        # ── Fecha ─────────────────────────────────────────────────────────
        if any(p in t for p in ['qué día','que dia','qué fecha','que fecha','hoy es','día de hoy']):
            DIAS  = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
            MESES = ['enero','febrero','marzo','abril','mayo','junio','julio',
                     'agosto','septiembre','octubre','noviembre','diciembre']
            hoy = datetime.now()
            s = f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]}"
            self._hablar(self._j('fecha', s))
            self._auto_reiniciar(); return True

        # ── Temporizador ──────────────────────────────────────────────────
        m = re.search(r'temporizador\s+(?:de\s+)?(\d+)\s*(?:minuto|min)', t)
        if m:
            mins = int(m.group(1))
            self._hablar(self._j('timer', mins))
            if ANDROID:
                try:
                    PA     = autoclass('org.kivy.android.PythonActivity')
                    Intent = autoclass('android.content.Intent')
                    intent = Intent('android.intent.action.SET_TIMER')
                    intent.putExtra('android.intent.extra.alarm.LENGTH', mins * 60)
                    intent.putExtra('android.intent.extra.alarm.SKIP_UI', True)
                    PA.mActivity.startActivity(intent)
                except Exception: pass
            self._auto_reiniciar(); return True

        # ── Llamar ────────────────────────────────────────────────────────
        for pref in ['llama a ','llamar a ','llama al ','llamar al ','marca ','llama ','llame a ','comunicame con ']:
            if pref in t:
                contacto = t.split(pref, 1)[1].strip()
                self._hablar(self._j('llamar', contacto))
                threading.Thread(target=self._hacer_llamada, args=(contacto,), daemon=True).start()
                self._auto_reiniciar(4.0); return True

        # ── WhatsApp ──────────────────────────────────────────────────────
        for pref in ['whatsapp a ','manda whatsapp a ','envía whatsapp a ','envia whatsapp a ',
                     'mensaje de whatsapp a ','mándame whatsapp a ']:
            if pref in t:
                resto = t.split(pref, 1)[1].strip()
                mg = re.search(r'\b(?:diciendo|di que|que diga|dile|diciendo que)\s+(.+)', resto)
                contacto = resto[:mg.start()].strip() if mg else resto
                msg = mg.group(1) if mg else 'Hola'
                self._hablar(self._j('whatsapp', contacto))
                threading.Thread(target=self._enviar_whatsapp, args=(contacto, msg), daemon=True).start()
                self._auto_reiniciar(); return True

        # ── SMS ───────────────────────────────────────────────────────────
        for pref in ['sms a ','mensaje a ','manda sms a ','envía mensaje a ','envia mensaje a ']:
            if pref in t:
                resto = t.split(pref, 1)[1].strip()
                mg = re.search(r'\b(?:diciendo|di que|que diga|dile)\s+(.+)', resto)
                contacto = resto[:mg.start()].strip() if mg else resto
                msg = mg.group(1) if mg else 'Hola'
                self._hablar(self._j('sms', contacto))
                threading.Thread(target=self._enviar_sms, args=(contacto, msg), daemon=True).start()
                self._auto_reiniciar(); return True

        # ── Abrir app ─────────────────────────────────────────────────────
        for pref in ['abre ','abrir ','abre la ','abre el ','abrir la ','abrir el ',
                     'inicia ','lanza ','entra a ','entra en ','ve a ']:
            if pref in t:
                app = t.split(pref, 1)[1].strip()
                self._hablar(self._j('abrir', app))
                threading.Thread(target=self._abrir_app, args=(app,), daemon=True).start()
                self._auto_reiniciar(); return True

        # ── Alarma ────────────────────────────────────────────────────────
        m = re.search(r'(?:alarma|despertador)[^\d]*(\d{1,2})(?::(\d{2}))?', t)
        if m:
            h = int(m.group(1)); mn = int(m.group(2)) if m.group(2) else 0
            self._hablar(self._j('alarma', f'{h}:{mn:02d}'))
            self._set_alarma(h, mn)
            self._auto_reiniciar(); return True

        # ── Volumen específico ─────────────────────────────────────────────
        m = re.search(r'volumen\s+(?:al\s+)?(\d+)\s*%?', t)
        if m:
            pct = int(m.group(1))
            self._hablar(self._j('volumen', pct))
            self._set_volumen(pct)
            self._auto_reiniciar(); return True

        # ── Brillo específico ─────────────────────────────────────────────
        m = re.search(r'brillo\s+(?:al\s+)?(\d+)\s*%?', t)
        if m:
            pct = int(m.group(1))
            self._hablar(self._j('brillo', pct))
            self._set_brillo(pct)
            self._auto_reiniciar(); return True

        # ── Clima ─────────────────────────────────────────────────────────
        m = re.search(r'(?:clima|tiempo|temperatura|pronóstico)\s+(?:de\s+|en\s+)?(.+)', t)
        if m:
            ciudad = m.group(1).strip()
            self._hablar(self._j('clima'))
            threading.Thread(target=self._get_clima, args=(ciudad,), daemon=True).start()
            self._auto_reiniciar(); return True

        # ── Canción específica ─────────────────────────────────────────────
        for pref in ['pon ','toca ','reproduce ','busca la canción ','busca ','quiero escuchar ']:
            if pref in t:
                query = t.split(pref, 1)[1].strip()
                idx = self._buscar_cancion(query)
                if idx >= 0:
                    nombre = os.path.basename(self.lista_musica[idx]).rsplit('.',1)[0]
                    self.indice_actual = idx
                    self._cargar_y_play()
                    self._hablar(self._j('cancion', nombre))
                elif not self.lista_musica:
                    self._hablar(self._j('sin_canciones'))
                else:
                    self._hablar(self._j('no_cancion'))
                self._auto_reiniciar(); return True

        # ── Comandos simples ──────────────────────────────────────────────
        SIMPLE = [
            (['reproduce','play','música','musica','reanuda','continúa','continua','pon música','pon musica'],
             'reproducir', 'musica_play'),
            (['pausa','pause','para la música','para la musica','detén la música'],
             'pausar', 'musica_pau'),
            (['detén','deten','stop','para todo','silencio','apaga la música'],
             'detener', 'musica_stop'),
            (['siguiente','next','la que sigue','otra canción','otra cancion','cambia canción','avanza'],
             'siguiente', 'musica_sig'),
            (['anterior','atrás','atras','la anterior','vuelve','regresa'],
             'anterior', 'musica_ant'),
            (['sube el volumen','sube volumen','más alto','mas alto','más volumen','mas volumen'],
             'subir_vol', 'vol_up'),
            (['baja el volumen','baja volumen','más bajo','mas bajo','menos volumen','silencia'],
             'bajar_vol', 'vol_down'),
            (['enciende la linterna','prende la linterna','linterna','enciende la luz','prende la luz'],
             'flash_on', 'flash_on'),
            (['apaga la linterna','apaga la luz','apaga el flash','linterna apagada'],
             'flash_off', 'flash_off'),
            (['batería','bateria','cuánta batería','nivel de batería','carga del teléfono'],
             'bateria', 'bateria'),
            (['toma una foto','toma foto','foto','fotografía','saca una foto','captura'],
             'foto', 'foto'),
        ]
        for kws, cmd, resp_key in SIMPLE:
            if any(kw in t for kw in kws):
                self._hablar(self._j(resp_key))
                if   cmd == 'flash_on':  threading.Thread(target=self._toggle_flash, args=(True,),  daemon=True).start()
                elif cmd == 'flash_off': threading.Thread(target=self._toggle_flash, args=(False,), daemon=True).start()
                elif cmd == 'bateria':   threading.Thread(target=self._check_bateria, daemon=True).start()
                elif cmd == 'foto':      self._tomar_foto()
                else:                    self._ejecutar(cmd)
                self._auto_reiniciar(); return True

        return False  # no manejado → caller decide (Groq o "no entendí")

    # ══════════════════════════════════════════════════════════════════════════
    # BACKGROUND — PANTALLA BLOQUEADA — WAKELOCK
    # ══════════════════════════════════════════════════════════════════════════

    def on_pause(self):
        # Kivy: retornar True permite que la app siga corriendo en background
        return True

    def on_resume(self):
        pass

    def _adquirir_wakelock(self):
        """Mantiene la CPU activa con la pantalla apagada."""
        try:
            PA = autoclass('org.kivy.android.PythonActivity')
            PM = autoclass('android.os.PowerManager')
            pm = PA.mActivity.getSystemService('power')
            if not hasattr(self, '_wake_lock') or self._wake_lock is None:
                # PARTIAL_WAKE_LOCK: CPU encendida, pantalla puede apagarse
                self._wake_lock = pm.newWakeLock(
                    PM.PARTIAL_WAKE_LOCK, 'J::AssistantWakeLock')
            if not self._wake_lock.isHeld():
                self._wake_lock.acquire()
            self._activar_sobre_pantalla_bloqueada()
        except Exception as e:
            self._set_status('WAKELOCK ERR: ' + str(e)[:20])

    def _liberar_wakelock(self):
        try:
            if hasattr(self, '_wake_lock') and self._wake_lock \
                    and self._wake_lock.isHeld():
                self._wake_lock.release()
        except Exception:
            pass

    def _activar_sobre_pantalla_bloqueada(self):
        """Permite que J responda incluso con la pantalla bloqueada."""
        try:
            PA  = autoclass('org.kivy.android.PythonActivity')
            WLP = autoclass('android.view.WindowManager$LayoutParams')
            win = PA.mActivity.getWindow()
            # Mantener pantalla encendida + mostrar sobre lock screen
            win.addFlags(
                WLP.FLAG_KEEP_SCREEN_ON |
                WLP.FLAG_SHOW_WHEN_LOCKED |
                WLP.FLAG_TURN_SCREEN_ON
            )
        except Exception:
            pass

    def _pedir_exencion_bateria(self, dt=0):
        """Solicita al usuario que J quede exento de optimización de batería."""
        try:
            PA       = autoclass('org.kivy.android.PythonActivity')
            Intent   = autoclass('android.content.Intent')
            Uri      = autoclass('android.net.Uri')
            Settings = autoclass('android.provider.Settings')
            activity = PA.mActivity
            pkg      = activity.getPackageName()
            intent   = Intent(
                Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                Uri.parse(f"package:{pkg}")
            )
            activity.startActivity(intent)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # PERMISOS
    # ══════════════════════════════════════════════════════════════════════════

    def _pedir_permisos(self, dt):
        try:
            from android.permissions import request_permissions, Permission
            VERSION = autoclass('android.os.Build$VERSION')
            perms = [
                Permission.RECORD_AUDIO,
                Permission.CALL_PHONE,
                Permission.READ_CONTACTS,
                Permission.SEND_SMS,
                Permission.READ_SMS,
                Permission.CAMERA,
                Permission.ACCESS_FINE_LOCATION,
                Permission.VIBRATE,
            ]
            if VERSION.SDK_INT >= 33:
                perms.append('android.permission.READ_MEDIA_AUDIO')
            else:
                perms.extend([Permission.READ_EXTERNAL_STORAGE,
                               Permission.WRITE_EXTERNAL_STORAGE])
            request_permissions(perms, self._on_permisos)
        except Exception:
            Clock.schedule_once(self.cargar_biblioteca, 0.3)

    def _on_permisos(self, permissions, results):
        Clock.schedule_once(self.cargar_biblioteca, 0.3)

    # ══════════════════════════════════════════════════════════════════════════
    # UTILS
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, t):
        self.root_widget.ids.lbl_status.text = t

    def _set_j_response(self, t):
        self.root_widget.ids.lbl_j_response.text = f'J: {t}'


if __name__ == '__main__':
    J_App().run()
