"""
J — AI ASSISTANT v1.0
Asistente personal con LLM (Groq), reproductor de música, TTS y control por voz.
Kivy + SoundLoader + Pyjnius (Android) + Groq API (llama-3.1-8b-instant)
"""
import os
import math
import json
import re
import threading
import urllib.request

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import (
    Color, Ellipse, Line, Rectangle,
    RoundedRectangle,
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
GROQ_API_KEY = "TU_API_KEY_AQUI"          # console.groq.com → free tier
GROQ_MODEL   = "llama-3.1-8b-instant"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# ── Decoración ────────────────────────────────────────────────────────────────
RUNAS = 'ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ'


# ─────────────────────────────────────────────────────────────────────────────
# ORBE ANIMADO
# ─────────────────────────────────────────────────────────────────────────────
class OrbWidget(Widget):
    angle      = NumericProperty(0)
    angle2     = NumericProperty(0)
    pulse      = NumericProperty(0)
    ray_phase  = NumericProperty(0)
    is_playing = BooleanProperty(False)

    _particles = [(i * 37.3, 68 + (i % 4) * 8, 2 + (i % 3)) for i in range(12)]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pulse_dir = 1
        self.bind(pos=self._redraw, size=self._redraw,
                  angle=self._redraw, angle2=self._redraw,
                  pulse=self._redraw, ray_phase=self._redraw,
                  is_playing=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 30)

    def _tick(self, dt):
        speed = 1.8 if self.is_playing else 0.6
        self.angle     = (self.angle  + dt * 28 * speed) % 360
        self.angle2    = (self.angle2 - dt * 18 * speed) % 360
        self.ray_phase = (self.ray_phase + dt * 2.2) % (2 * math.pi)
        self.pulse += dt * self._pulse_dir * (0.9 if self.is_playing else 0.35)
        if self.pulse >= 1:
            self.pulse = 1; self._pulse_dir = -1
        elif self.pulse <= 0:
            self.pulse = 0; self._pulse_dir = 1

    def _redraw(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        p = self.pulse
        with self.canvas:
            # Halo
            Color(0.0, 0.4, 1.0, 0.06 + p * 0.06)
            d = 160 + p * 12
            Ellipse(pos=(cx - d/2, cy - d/2), size=(d, d))

            # Anillo runas exterior
            self._draw_rune_ring(cx, cy, 64, 12, self.angle,
                                 color=(0.2, 0.6, 1.0, 0.45 + p*0.25))
            Color(0.1, 0.5, 1.0, 0.55 + p * 0.25)
            Line(ellipse=(cx-58, cy-58, 116, 116), width=1.3)

            # Anillo interior (contra-rotatorio)
            self._draw_rune_ring(cx, cy, 46, 8, self.angle2,
                                 color=(0.3, 0.7, 1.0, 0.5 + p*0.3))
            Color(0.1, 0.6, 1.0, 0.6 + p * 0.2)
            Line(ellipse=(cx-44, cy-44, 88, 88), width=1.5)

            # Rayos
            self._draw_rays(cx, cy, p)

            # Núcleo
            r_core = 30 + p * 5
            Color(0.0, 0.15, 0.5, 0.9)
            Ellipse(pos=(cx-r_core, cy-r_core), size=(r_core*2, r_core*2))
            r1 = 20 + p * 4
            Color(0.1, 0.45, 0.9, 0.75)
            Ellipse(pos=(cx-r1, cy-r1), size=(r1*2, r1*2))
            r2 = 10 + p * 3
            Color(0.4, 0.75, 1.0, 0.9)
            Ellipse(pos=(cx-r2, cy-r2), size=(r2*2, r2*2))
            Color(0.9, 0.97, 1.0, 0.95)
            Ellipse(pos=(cx-5, cy-5), size=(10, 10))

            Color(0.2, 0.6, 1.0, 0.4 + p * 0.4)
            Line(ellipse=(cx-r_core, cy-r_core, r_core*2, r_core*2), width=1.2)

            self._draw_particles(cx, cy)

    def _draw_rune_ring(self, cx, cy, radius, n, angle_offset, color=(0.2,0.6,1,0.45)):
        Color(*color)
        for i in range(n):
            a = math.radians(angle_offset + i * (360 / n))
            rx = cx + radius * math.cos(a)
            ry = cy + radius * math.sin(a)
            Line(points=[rx - 3*math.sin(a), ry + 3*math.cos(a),
                         rx + 3*math.sin(a), ry - 3*math.cos(a)], width=1.1)
            Line(points=[rx - 3, ry, rx + 3, ry], width=0.8)

    def _draw_rays(self, cx, cy, p):
        ray_data = [(90,55,80),(270,55,80),(0,55,80),(180,55,80),
                    (45,50,70),(135,50,70),(225,50,70),(315,50,70)]
        for i, (base_a, r0, r1) in enumerate(ray_data):
            ph = i * 0.78
            intensity = abs(math.sin(self.ray_phase + ph))
            if intensity < 0.2:
                continue
            alpha  = intensity * (0.5 + p * 0.4)
            wobble = math.sin(self.ray_phase * 2.3 + ph) * 6
            a = math.radians(base_a + wobble)
            x1 = cx + r0 * math.cos(a);  y1 = cy + r0 * math.sin(a)
            x2 = cx + (r1 + p*10)*math.cos(a); y2 = cy + (r1+p*10)*math.sin(a)
            Color(0.1, 0.5, 1.0, alpha * 0.85)
            Line(points=[x1, y1, x2, y2], width=1.4)
            mid = 0.55
            Color(0.5, 0.85, 1.0, alpha * 0.5)
            Line(points=[x1+(x2-x1)*mid, y1+(y2-y1)*mid, x2, y2], width=0.8)

    def _draw_particles(self, cx, cy):
        t = self.ray_phase
        for i, (base_a, base_r, size) in enumerate(self._particles):
            a     = math.radians(base_a + self.angle * 0.4 + i * 5)
            drift = math.sin(t * 0.8 + i * 1.1) * 8
            r     = base_r + drift
            px    = cx + r * math.cos(a)
            py    = cy + r * math.sin(a)
            alpha = 0.3 + 0.5 * abs(math.sin(t * 0.6 + i * 0.9))
            Color(0.3, 0.7, 1.0, alpha) if i % 3 == 0 else \
                Color(0.6, 0.9, 1.0, alpha * 0.7)
            Ellipse(pos=(px - size/2, py - size/2), size=(size, size))


# ─────────────────────────────────────────────────────────────────────────────
# BARRA DE PROGRESO
# ─────────────────────────────────────────────────────────────────────────────
class ProgressWidget(Widget):
    progress = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, progress=self._redraw)

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.05, 0.1, 0.3, 0.45)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[3])
            Color(0.1, 0.4, 0.8, 0.32)
            Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 3], width=0.8)
            fill_w = max(self.progress * self.width, 0)
            if fill_w > 0:
                Color(0.2, 0.6, 1.0, 0.92)
                RoundedRectangle(pos=self.pos, size=(fill_w, self.height), radius=[3])
                Color(0.7, 0.9, 1.0, 1)
                dot = 8
                Ellipse(pos=(self.x+fill_w-dot/2, self.center_y-dot/2), size=(dot, dot))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.progress = (touch.x - self.x) / self.width
            App.get_running_app().seek(self.progress)
            return True


# ─────────────────────────────────────────────────────────────────────────────
# ÍTEM DE CANCIÓN
# ─────────────────────────────────────────────────────────────────────────────
class SongItem(Button):
    def __init__(self, nombre, indice, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.nombre    = nombre
        self.indice    = indice
        self.app_ref   = app_ref
        self.text      = f'  ᚱ  {nombre}'
        self.font_size = '11sp'
        self.halign    = 'left'
        self.size_hint_y = None
        self.height    = '36dp'
        self.background_normal  = ''
        self.background_color   = (0, 0, 0, 0)
        self.color     = (0.82, 0.82, 0.82, 1)
        self.bold      = False
        self.bind(on_press=lambda i: self.app_ref.reproducir_indice(self.indice))
        self.bind(pos=self._upd, size=self._upd)
        self._activo = False
        with self.canvas.before:
            self._c_bg  = Color(0.05, 0.1, 0.3, 0.09)
            self._r_bg  = RoundedRectangle(pos=self.pos, size=self.size, radius=[3])
            self._c_brd = Color(0.1, 0.35, 0.75, 0.22)
            self._l_brd = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 3],
                               width=0.7)

    def _upd(self, *_):
        self._r_bg.pos  = self.pos
        self._r_bg.size = self.size
        self._l_brd.rounded_rectangle = [self.x, self.y, self.width, self.height, 3]

    def set_activo(self, v):
        self._activo = v
        if v:
            self._c_bg.rgba  = (0.05, 0.2, 0.55, 0.32)
            self._c_brd.rgba = (0.3, 0.75, 1.0, 0.92)
            self.color = (0.5, 0.9, 1.0, 1)
            self.bold  = True
            self.text  = f'  ▶  {self.nombre}'
        else:
            self._c_bg.rgba  = (0.05, 0.1, 0.3, 0.09)
            self._c_brd.rgba = (0.1, 0.35, 0.75, 0.22)
            self.color = (0.82, 0.82, 0.82, 1)
            self.bold  = False
            self.text  = f'  ᚱ  {self.nombre}'


# ─────────────────────────────────────────────────────────────────────────────
# ANDROID: LISTENER DE VOZ + TTS + RUNNABLE
# ─────────────────────────────────────────────────────────────────────────────
if ANDROID:
    class JVoiceListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']
        __javacontext__    = 'app'

        def __init__(self, app_ref):
            super().__init__()
            self.app_ref = app_ref

        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, params):
            Clock.schedule_once(lambda dt:
                self.app_ref._set_mic_ui(True, 'ESCUCHANDO...'), 0)

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if matches and matches.size() > 0:
                texto = matches.get(0)
                Clock.schedule_once(
                    lambda dt, t=texto: self.app_ref.procesar_comando_voz(t), 0)

        @java_method('(I)V')
        def onError(self, error):
            Clock.schedule_once(lambda dt:
                self.app_ref._on_voice_error(error), 0)

        @java_method('()V')
        def onBeginningOfSpeech(self): pass

        @java_method('()V')
        def onEndOfSpeech(self): pass

        @java_method('(F)V')
        def onRmsChanged(self, rmsdB): pass

        @java_method('([B)V')
        def onBufferReceived(self, buffer): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, partialResults): pass

        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, eventType, params): pass

    class JTTSListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
        __javacontext__    = 'app'

        def __init__(self, app_ref):
            super().__init__()
            self.app_ref = app_ref

        @java_method('(I)V')
        def onInit(self, status):
            Clock.schedule_once(lambda dt, s=status:
                self.app_ref._tts_ready(s), 0)

    class _Runnable(PythonJavaClass):
        __javainterfaces__ = ['java/lang/Runnable']
        __javacontext__    = 'app'

        def __init__(self, fn):
            super().__init__()
            self._fn = fn

        @java_method('()V')
        def run(self):
            self._fn()


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT RAÍZ
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

        self.carpeta_musica  = "/storage/emulated/0/Music"
        self.sonido_actual   = None
        self.lista_musica    = []
        self.indice_actual   = 0
        self.en_pausa        = False
        self.song_items      = []
        self.mic_activo      = False
        self._recognizer     = None
        self._tts            = None
        self._tts_listo      = False
        self._procesando_llm = False

        self.root_widget = J_Layout()

        Clock.schedule_interval(self._tick_progreso, 0.5)

        if ANDROID:
            Clock.schedule_once(self._pedir_permisos, 0.6)
            Clock.schedule_once(self._init_tts, 1.0)
        else:
            Clock.schedule_once(self.cargar_biblioteca, 0.8)

        return self.root_widget

    # ── TTS ──────────────────────────────────────────────────────────────────

    def _init_tts(self, dt=0):
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            TextToSpeech   = autoclass('android.speech.tts.TextToSpeech')
            activity = PythonActivity.mActivity
            self._tts_listener = JTTSListener(self)
            self._tts = TextToSpeech(activity, self._tts_listener)
        except Exception:
            self._tts_listo = False

    def _tts_ready(self, status):
        try:
            TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
            Locale       = autoclass('java.util.Locale')
            if status == TextToSpeech.SUCCESS:
                self._tts.setLanguage(Locale("es", "ES"))
                self._tts_listo = True
                Clock.schedule_once(lambda dt: self._hablar("J en línea."), 0.8)
        except Exception:
            self._tts_listo = False

    def _hablar(self, texto):
        self._set_j_response(texto)
        if ANDROID and self._tts_listo and self._tts:
            try:
                TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
                self._tts.speak(texto, TextToSpeech.QUEUE_FLUSH, None, None)
            except Exception:
                pass

    # ── BIBLIOTECA ───────────────────────────────────────────────────────────

    def cargar_biblioteca(self, dt=0):
        grid = self.root_widget.ids.lista_grid
        grid.clear_widgets()
        self.song_items.clear()

        if ANDROID:
            archivos = self._escanear_musica_android()
        elif os.path.exists(self.carpeta_musica):
            archivos = sorted([
                os.path.join(self.carpeta_musica, f)
                for f in os.listdir(self.carpeta_musica)
                if f.lower().endswith(('.mp3', '.ogg', '.wav', '.flac', '.m4a'))
            ])
        else:
            archivos = []

        self.lista_musica = archivos if archivos else [
            "Demo — Sin Señal.mp3", "Protocolo J.mp3", "Sistema Activo.mp3",
        ]

        n = len(self.lista_musica)
        self.root_widget.ids.lbl_biblioteca.text = f'BIBLIOTECA: {n} TEMAS'

        for i, ruta in enumerate(self.lista_musica):
            display = os.path.basename(ruta)
            item = SongItem(nombre=display, indice=i, app_ref=self)
            grid.add_widget(item)
            self.song_items.append(item)

        if self.lista_musica:
            self._actualizar_ui_cancion()
            self._set_status('SISTEMAS LISTOS')

    def _escanear_musica_android(self):
        ext = ('.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus')
        carpetas = [
            "/storage/emulated/0/Music",
            "/storage/emulated/0/music",
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/sdcard/Music",
            "/sdcard/Download",
        ]
        archivos = []
        seen = set()
        for carpeta in carpetas:
            if not os.path.exists(carpeta):
                continue
            try:
                for entry in os.listdir(carpeta):
                    ruta = os.path.join(carpeta, entry)
                    if entry.lower().endswith(ext):
                        key = os.path.realpath(ruta)
                        if key not in seen:
                            seen.add(key); archivos.append(ruta)
                    elif os.path.isdir(ruta):
                        try:
                            for sub in os.listdir(ruta):
                                if sub.lower().endswith(ext):
                                    sp  = os.path.join(ruta, sub)
                                    key = os.path.realpath(sp)
                                    if key not in seen:
                                        seen.add(key); archivos.append(sp)
                        except Exception:
                            pass
            except Exception:
                pass
        return sorted(archivos, key=lambda x: os.path.basename(x).lower())

    def _actualizar_ui_cancion(self):
        nombre  = self.lista_musica[self.indice_actual]
        display = os.path.basename(nombre).rsplit('.', 1)[0]
        self.root_widget.ids.lbl_cancion.text = display
        for i, item in enumerate(self.song_items):
            item.set_activo(i == self.indice_actual)

    # ── CONTROLES ────────────────────────────────────────────────────────────

    def reproducir(self):
        if not self.lista_musica:
            self._set_status('BIBLIOTECA VACÍA')
            return
        if self.en_pausa and self.sonido_actual:
            self.sonido_actual.play()
            self.en_pausa = False
            self._set_status('▶ REPRODUCIENDO')
            self.root_widget.ids.orb.is_playing = True
            return
        self._cargar_y_play()

    def reproducir_indice(self, indice):
        self.indice_actual = indice
        self.en_pausa = False
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self._cargar_y_play()

    def _cargar_y_play(self):
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None

        ruta = self.lista_musica[self.indice_actual]
        if not os.path.isabs(ruta):
            ruta = os.path.join(self.carpeta_musica, ruta)

        if not os.path.exists(ruta):
            self._set_status('▶ MODO DEMO')
            self._actualizar_ui_cancion()
            self.root_widget.ids.orb.is_playing = True
            return

        self.sonido_actual = SoundLoader.load(ruta)
        if self.sonido_actual:
            self.sonido_actual.volume = self.root_widget.ids.vol_slider.value
            self.sonido_actual.bind(on_stop=self._on_fin)
            self.sonido_actual.play()
            self.en_pausa = False
            self._set_status('▶ REPRODUCIENDO')
            self._actualizar_ui_cancion()
            self.root_widget.ids.orb.is_playing = True
        else:
            self._set_status('ERROR: FORMATO NO SOPORTADO')

    def pausar(self):
        if self.sonido_actual and not self.en_pausa:
            self.sonido_actual.stop()
            self.en_pausa = True
            self._set_status('⏸ EN PAUSA')
            self.root_widget.ids.orb.is_playing = False

    def detener(self):
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self.en_pausa = False
        self._set_status('⏹ DETENIDO')
        self.root_widget.ids.orb.is_playing = False
        self.root_widget.ids.prog_widget.progress = 0

    def siguiente(self):
        if not self.lista_musica:
            return
        self.indice_actual = (self.indice_actual + 1) % len(self.lista_musica)
        self.en_pausa = False
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self._cargar_y_play()

    def anterior(self):
        if not self.lista_musica:
            return
        self.indice_actual = (self.indice_actual - 1) % len(self.lista_musica)
        self.en_pausa = False
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self._cargar_y_play()

    def _on_fin(self, *args):
        Clock.schedule_once(lambda dt: self.siguiente(), 0.5)

    def _tick_progreso(self, dt):
        if self.sonido_actual and self.sonido_actual.state == 'play':
            dur = self.sonido_actual.length
            pos = self.sonido_actual.get_pos()
            if dur and dur > 0:
                self.root_widget.ids.prog_widget.progress = pos / dur
                self.root_widget.ids.lbl_tiempo.text    = self._fmt(pos)
                self.root_widget.ids.lbl_duracion.text  = self._fmt(dur)

    def seek(self, progress):
        if self.sonido_actual and self.sonido_actual.length:
            self.sonido_actual.seek(progress * self.sonido_actual.length)

    def cambiar_volumen(self, slider, val):
        if self.sonido_actual:
            self.sonido_actual.volume = val

    @staticmethod
    def _fmt(s):
        s = int(s)
        return f'{s//60}:{s%60:02d}'

    # ── VOZ ──────────────────────────────────────────────────────────────────

    def toggle_microfono(self):
        self.mic_activo = not self.mic_activo
        if self.mic_activo:
            self.root_widget.ids.btn_mic.text = '🎙  J: ESCUCHANDO'
            self._set_mic_ui(True, 'INICIANDO...')
            if ANDROID:
                self._iniciar_reconocimiento()
            else:
                self._set_mic_ui(True, 'SIMULANDO ESCUCHA')
        else:
            self.root_widget.ids.btn_mic.text = '🎙  ACTIVAR J'
            self._set_mic_ui(False, 'MICRÓFONO INACTIVO')
            if ANDROID:
                self._detener_reconocimiento()

    def _set_mic_ui(self, activo, texto):
        lbl  = self.root_widget.ids.lbl_mic_status
        lbl2 = self.root_widget.ids.lbl_mic_comando
        lbl.text  = texto
        lbl.color = (0.3, 0.7, 1.0, 1) if activo else (0.45, 0.45, 0.45, 1)
        if activo:
            lbl2.text  = 'habla con J: música, preguntas, órdenes'
            lbl2.color = (0.2, 0.6, 1.0, 0.9)
        else:
            lbl2.text  = 'di cualquier cosa a J'
            lbl2.color = (0.3, 0.3, 0.5, 0.8)

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
                try:
                    self._recognizer.stopListening()
                    self._recognizer.destroy()
                except Exception:
                    pass
                self._recognizer = None

            PythonActivity   = autoclass('org.kivy.android.PythonActivity')
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            Intent           = autoclass('android.content.Intent')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')

            activity = PythonActivity.mActivity
            self._recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            self._voice_listener = JVoiceListener(self)
            self._recognizer.setRecognitionListener(self._voice_listener)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es")
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "es")
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
            intent.putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500)
            intent.putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 300)
            intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE,
                            activity.getPackageName())
            self._recognizer.startListening(intent)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e):
                self._set_mic_ui(False, f'MIC ERROR: {err[:28]}'), 0)
            Clock.schedule_once(lambda dt:
                setattr(self, 'mic_activo', False), 0)

    def _detener_reconocimiento(self):
        if not self._recognizer:
            return
        rec = self._recognizer
        self._recognizer = None
        try:
            Handler = autoclass('android.os.Handler')
            Looper  = autoclass('android.os.Looper')
            def _stop():
                try:
                    rec.stopListening(); rec.destroy()
                except Exception:
                    pass
            Handler(Looper.getMainLooper()).post(_Runnable(_stop))
        except Exception:
            pass

    def _on_voice_error(self, error):
        if error in (6, 7) and self.mic_activo:
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 1.0)
        else:
            self._set_mic_ui(False, f'VOZ ERROR: {error}')
            self.mic_activo = False

    # ── LLM (GROQ) ───────────────────────────────────────────────────────────

    def procesar_comando_voz(self, texto: str):
        t = texto.lower().strip()
        self._set_mic_ui(True, f'"{texto[:24]}"')

        if not GROQ_API_KEY or GROQ_API_KEY == "TU_API_KEY_AQUI":
            self._procesar_comando_simple(t)
            return

        self._set_status('J PROCESANDO...')
        self._procesando_llm = True
        threading.Thread(
            target=self._llamar_groq, args=(texto,), daemon=True
        ).start()

        if ANDROID and self.mic_activo:
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 4.5)

    def _llamar_groq(self, texto_usuario):
        try:
            payload = json.dumps({
                'model':    GROQ_MODEL,
                'messages': [
                    {'role': 'system',  'content': self._build_system_prompt()},
                    {'role': 'user',    'content': texto_usuario},
                ],
                'max_tokens':  80,
                'temperature': 0.65,
            }).encode('utf-8')

            req = urllib.request.Request(
                GROQ_URL, data=payload, method='POST',
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type':  'application/json',
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data      = json.loads(resp.read().decode('utf-8'))
                respuesta = data['choices'][0]['message']['content'].strip()
                Clock.schedule_once(
                    lambda dt, r=respuesta: self._on_respuesta_llm(r), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self._fallback_sin_red(texto_usuario), 0)

    def _on_respuesta_llm(self, respuesta):
        self._procesando_llm = False
        match = re.search(r'\[CMD:(\w+)\]', respuesta)
        accion = match.group(1) if match else None
        texto_limpio = re.sub(r'\[CMD:\w+\]\s*', '', respuesta).strip()

        self._hablar(texto_limpio)
        if accion:
            Clock.schedule_once(lambda dt, a=accion: self._ejecutar_accion(a), 0.3)

    def _fallback_sin_red(self, texto):
        self._procesando_llm = False
        self._set_status('J: SIN CONEXIÓN')
        self._procesar_comando_simple(texto.lower())

    def _ejecutar_accion(self, accion):
        mapa = {
            'reproducir': self.reproducir,
            'pausar':     self.pausar,
            'detener':    self.detener,
            'siguiente':  self.siguiente,
            'anterior':   self.anterior,
            'subir_vol':  lambda: setattr(
                self.root_widget.ids.vol_slider, 'value',
                min(self.root_widget.ids.vol_slider.value + 0.15, 1.0)),
            'bajar_vol':  lambda: setattr(
                self.root_widget.ids.vol_slider, 'value',
                max(self.root_widget.ids.vol_slider.value - 0.15, 0.0)),
        }
        fn = mapa.get(accion)
        if fn:
            fn()

    def _build_system_prompt(self):
        n      = len(self.lista_musica)
        cancion = '—'
        if self.lista_musica:
            cancion = os.path.basename(
                self.lista_musica[self.indice_actual]).rsplit('.', 1)[0]
        estado = ('reproduciendo' if (self.sonido_actual and not self.en_pausa)
                  else 'en pausa' if self.en_pausa else 'detenido')

        return f"""Eres J, un asistente de IA personal sofisticado y conciso, como Jarvis de Iron Man.
Respondes SIEMPRE en español. Máximo 1 oración corta. Sin emojis. Tono directo y confiado.

Controlas un reproductor de música. Cuando el usuario pida una acción musical,
incluye al INICIO de tu respuesta la etiqueta:
[CMD:reproducir] [CMD:pausar] [CMD:detener] [CMD:siguiente] [CMD:anterior]
[CMD:subir_vol] [CMD:bajar_vol]

Estado actual: biblioteca={n} canciones | canción={cancion} | estado={estado}

Para preguntas generales (clima, noticias, etc.) responde brevemente con lo que sabes."""

    def _procesar_comando_simple(self, texto):
        CMDS = {
            'reproducir': ['play','reproduce','toca','pon','inicia','música','musica','empieza'],
            'pausar':     ['pausa','pause','para','espera','suspende'],
            'detener':    ['stop','detén','deten','silencio','apaga','detener'],
            'siguiente':  ['siguiente','next','adelante','salta','otra','avanza','proxima'],
            'anterior':   ['anterior','atrás','atras','back','regresa','vuelve','previa'],
            'subir_vol':  ['sube','más alto','mas alto','más volumen','mas volumen'],
            'bajar_vol':  ['baja','más bajo','mas bajo','menos volumen'],
        }
        RESPUESTAS = {
            'reproducir': 'Reproduciendo.',
            'pausar':     'En pausa.',
            'detener':    'Detenido.',
            'siguiente':  'Siguiente pista.',
            'anterior':   'Pista anterior.',
            'subir_vol':  'Subiendo volumen.',
            'bajar_vol':  'Bajando volumen.',
        }
        accion = next((cmd for cmd, palabras in CMDS.items()
                       if any(p in texto for p in palabras)), None)
        if accion:
            self._ejecutar_accion(accion)
            self._hablar(RESPUESTAS[accion])
        else:
            self._hablar('No entendí la orden.')

        if ANDROID and self.mic_activo:
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 2.0)

    # ── PERMISOS ─────────────────────────────────────────────────────────────

    def _pedir_permisos(self, dt):
        try:
            from android.permissions import request_permissions, Permission
            VERSION = autoclass('android.os.Build$VERSION')
            if VERSION.SDK_INT >= 33:
                perms = ['android.permission.READ_MEDIA_AUDIO', Permission.RECORD_AUDIO]
            else:
                perms = [Permission.READ_EXTERNAL_STORAGE, Permission.RECORD_AUDIO]
            request_permissions(perms, self._on_permisos_granted)
        except Exception as e:
            self._set_status(f'PERM: {str(e)[:20]}')
            Clock.schedule_once(self.cargar_biblioteca, 0.3)

    def _on_permisos_granted(self, permissions, results):
        Clock.schedule_once(self.cargar_biblioteca, 0.3)

    # ── UTILS ────────────────────────────────────────────────────────────────

    def _set_status(self, texto: str):
        self.root_widget.ids.lbl_status.text = texto

    def _set_j_response(self, texto: str):
        self.root_widget.ids.lbl_j_response.text = f'J: {texto}'


if __name__ == '__main__':
    J_App().run()
