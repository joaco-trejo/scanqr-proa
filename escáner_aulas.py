import tkinter as tk
from tkinter import messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import sqlite3
import qrcode
import json # Para estructurar los datos dentro del QR
import os
from datetime import datetime

# ==========================================
# PALETA DE COLORES UI/UX INSTITUCIONAL (PROA)
# ==========================================
COLOR_FONDO = "#F5F7FA"         # Lienzo general
COLOR_TARJETA = "#FFFFFF"       # Contenedores y tarjetas elevadas
COLOR_TEXTO = "#101820"         # Texto principal (Deep Navy)
COLOR_AZUL_PROA = "#022B5A"     # Azul oficial ProA
COLOR_ROJO_PROA = "#E31B23"     # Rojo oficial ProA
COLOR_BORDE = "#D0D7DE"         # Bordes sutiles

# Estados de alerta para el escáner
COLOR_EXITO_BG = "#D4EDDA"
COLOR_EXITO_FG = "#155724"
COLOR_ERROR_BG = "#F8D7DA"
COLOR_ERROR_FG = "#721C24"
COLOR_AVISO_BG = "#FFF3CD"      # Advertencia (ej: QR con datos desactualizados)
COLOR_AVISO_FG = "#856404"

# --- Configuración de la Base de Datos SQLite ---
DB_NAME = "examenes.db" # se guarda el nombre del archivo en una variable
QR_DIR = "qrcodes"      # carpeta donde se guardan las imágenes QR

# Validación del DNI: solo dígitos, entre 7 y 8 (ajustar si hace falta)
DNI_MIN_DIGITOS = 7
DNI_MAX_DIGITOS = 8

# Cámara del escáner
INDICE_CAMARA = 0            # 0 = cámara por defecto de la computadora
FALLOS_MAXIMOS_LECTURA = 60  # lecturas seguidas sin imagen antes de avisar (~1 segundo)

def inicializar_base_de_datos():
    """Crea la tabla de estudiantes si no existe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Definimos la tabla con todos los campos solicitados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estudiantes (
            dni TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            localidad TEXT,
            colegio TEXT,
            curso TEXT,
            aula_asignada TEXT NOT NULL,
            fecha_registro TEXT,
            qr_path TEXT)
    ''') # Ruta a la imagen del QR generada
    conn.commit()
    conn.close()

def estudiante_existe(dni):
    """Devuelve True si ya hay un estudiante registrado con ese DNI."""
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.execute("SELECT 1 FROM estudiantes WHERE dni = ?", (dni,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def buscar_estudiante_por_dni(dni):
    """Devuelve un diccionario con los datos reales del estudiante, o None si no existe."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # permite acceder a las columnas por nombre
    try:
        fila = conn.execute(
            "SELECT dni, nombre, apellido, curso, aula_asignada FROM estudiantes WHERE dni = ?",
            (dni,)
        ).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()

def guardar_estudiante_db(datos, actualizar=False):
    """Inserta un estudiante nuevo o, si actualizar=True, actualiza el existente.

    No muestra ventanas: la decisión de sobrescribir la toma quien llama.
    Devuelve (exito, mensaje). La transacción se confirma (commit) solo si
    todo salió bien; ante cualquier error se revierte.
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        with conn:  # commit automático si no hay error, rollback si lo hay
            if actualizar:
                conn.execute("""
                    UPDATE estudiantes
                    SET nombre = :nombre,
                        apellido = :apellido,
                        localidad = :localidad,
                        colegio = :colegio,
                        curso = :curso,
                        aula_asignada = :aula_asignada,
                        fecha_registro = :fecha_registro,
                        qr_path = :qr_path
                    WHERE dni = :dni
                """, datos)
                return True, "Estudiante actualizado exitosamente."

            conn.execute("""
                INSERT INTO estudiantes
                (dni, nombre, apellido, localidad, colegio, curso, aula_asignada, fecha_registro, qr_path)
                VALUES (:dni, :nombre, :apellido, :localidad, :colegio, :curso, :aula_asignada, :fecha_registro, :qr_path)
            """, datos)
            return True, "Estudiante guardado exitosamente."
    except sqlite3.IntegrityError:
        return False, f"El DNI {datos['dni']} ya está registrado."
    except sqlite3.Error as e:
        return False, f"Error al guardar: {e}"
    finally:
        conn.close()

# --- Funciones de Generación de QR ---

def generar_datos_qr_estructurados(nombre, apellido, dni, aula):
    """Crea un string JSON para el contenido del QR."""
    # Estructuramos solo los datos clave para el escáner rápido
    datos = {
        "dni": dni,
        "nombre_completo": f"{nombre} {apellido}",
        "aula": aula
    }
    return json.dumps(datos) # Convertimos el diccionario a un string JSON

def ruta_qr_estudiante(dni):
    """Ruta definitiva de la imagen QR de un estudiante."""
    return f"{QR_DIR}/qr_{dni}.png"

def generar_y_guardar_imagen_qr(datos_qr_text, ruta_destino):
    """Genera la imagen del QR y la guarda en ruta_destino."""
    carpeta = os.path.dirname(ruta_destino)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    # Configuración de la generación del QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L, # Corrección de errores leve para mayor rapidez
        box_size=10,
        border=4,
    )
    qr.add_data(datos_qr_text)
    qr.make(fit=True)

    img = qr.make_image(fill_color=COLOR_TEXTO, back_color="white")
    img.save(ruta_destino)

    return ruta_destino

def borrar_archivo_si_existe(ruta):
    """Elimina un archivo temporal sin fallar si no está."""
    try:
        os.remove(ruta)
    except OSError:
        pass

def interpretar_qr(contenido_raw):
    """Interpreta el texto leído de un QR.

    Devuelve {"dni": ..., "aula": ...} si el QR trae un DNI, o None si no es
    un QR del sistema (no es JSON, no es un objeto JSON o no tiene "dni").

    Los datos reales del estudiante (nombre y aula) se consultan en la base
    de datos; el "aula" del QR solo se usa para detectar QR desactualizados.
    """
    try:
        datos = json.loads(contenido_raw)
    except (ValueError, RecursionError):  # JSONDecodeError es un ValueError
        return None

    if not isinstance(datos, dict):
        return None

    dni = str(datos.get("dni") or "").strip()
    if not dni:
        return None

    aula = str(datos.get("aula") or "").strip()
    return {"dni": dni, "aula": aula}

# --- Clases de la Interfaz Gráfica (GUI) ---

class FormularioEstudiante(tk.Toplevel):
    """Ventana secundaria para el ingreso de datos del estudiante."""
    def __init__(self, parent):
        
        super().__init__(parent)
        self.color_fondo_ventana_datos = "#9bb5f8"
        self.title("Ingresar Nuevo Estudiante - Generar QR")
        self.geometry("560x700+100+0")
        self.configure(bg=COLOR_FONDO)
        self.resizable(0,0)
        self.transient(parent) # Hace que esta ventana dependa de la principal
        self.iconbitmap("assets/PROAico.ico")

        # --- Variables de control ---
        self.qr_generado_path = None

        # --- UI - Formulario ---
        frame_form = tk.LabelFrame(
                    self, text=" Datos del Estudiante ", font=("Arial", 11, "bold"), 
                    bg=COLOR_TARJETA, fg=COLOR_AZUL_PROA, bd=1, relief="solid", pady=10, padx=15)
        frame_form.pack(pady=15, padx=20, fill="both", expand=True)

        self.crear_campo(frame_form, "DNI (Identificación):", "dni_entry")
        self.crear_campo(frame_form, "Nombre:", "nombre_entry")
        self.crear_campo(frame_form, "Apellido:", "apellido_entry")
        self.crear_campo(frame_form, "Localidad:", "localidad_entry")
        self.crear_campo(frame_form, "Colegio:", "colegio_entry")
        self.crear_campo(frame_form, "Curso:", "curso_entry")
        self.crear_campo(frame_form, "Aula Asignada (EJ: A-01):", "aula_entry")

        # Imagen en botón para generar QR (Ruta adaptada a assets)
        img_guardar = Image.open("assets/guardar.png")
        img_guardar = img_guardar.resize((30, 30))
        self.img_guardar = ImageTk.PhotoImage(img_guardar)

        # --- UI - Botones ---
        self.btn_guardar = tk.Button(
            self, text=" Guardar y Generar QR", font=("Arial", 11, "bold"),bg=COLOR_ROJO_PROA, 
            fg="white", activebackground="#C0161C", # Efecto al hacer clic
            activeforeground="white", command=self.procesar_datos,image=self.img_guardar,compound=tk.LEFT,padx=15,pady=8,bd=0,cursor="hand2")
        
        self.btn_guardar.pack(pady=10)

        # --- UI - Previsualización del QR ---
        self.lbl_qr_preview = tk.Label(self, text="El QR generado aparecerá aquí", bg="#a6ccfc", width=50, height=15, relief="solid", bd=2)
        self.lbl_qr_preview.pack(pady=10)

        # Imagen de compartir/guardar QR (Ruta adaptada a assets)
        img_compartir = Image.open("assets/compartir.png")
        img_compartir = img_compartir.resize((30, 30))
        self.img_compartir = ImageTk.PhotoImage(img_compartir)
        
        self.btn_compartir = tk.Button(
            self,
            text=" Compartir / Guardar Imagen QR",
            font=("Arial", 10, "bold"),
            command=self.compartir_qr,
            image=self.img_compartir,
            compound=tk.LEFT,
            padx=12,
            pady=6,
            bg=COLOR_AZUL_PROA,
            fg="white",
            activebackground="#072A54",
            activeforeground="white",
            bd=0,
            cursor="hand2",
            state="disabled"
        )
        
        self.btn_compartir.pack(pady=15) # Reemplaza a .place()
        
        self.grab_set() # Hace que esta ventana sea modal

    def crear_campo(self, parent, label_text, entry_name):
        """Helper para crear campos de entrada etiquetados."""
        frame = tk.Frame(parent, bg=COLOR_TARJETA)
        frame.pack(fill="x", pady=4)
        
        lbl = tk.Label(frame, text=label_text, font=("Arial", 9,"bold","italic"), bg=COLOR_TARJETA, fg=COLOR_TEXTO, width=22, anchor="w")
        lbl.pack(side="left")
        
        entry = tk.Entry(frame, font=("Arial", 10), bg="#FAFAFA", 
        fg=COLOR_TEXTO, relief="solid", bd=1)

        entry.pack(side="left", fill="x", expand=True)

        # Se guarda la referencia de la entrada dinámicamente en la clase
        setattr(self, entry_name, entry)

    def procesar_datos(self):
        """Valida, guarda en DB y genera el QR."""
        # Recuperar datos
        dni = self.dni_entry.get().strip()
        nombre = self.nombre_entry.get().strip()
        apellido = self.apellido_entry.get().strip()
        aula = self.aula_entry.get().strip()
        
        # Validación básica (Campos obligatorios)
        if not all([dni, nombre, apellido, aula]):
            messagebox.showwarning("Faltan Datos", "Por favor completa DNI, Nombre, Apellido y Aula.")
            return

        # Validación del formato del DNI (solo dígitos y largo esperado)
        if not (dni.isascii() and dni.isdigit() and DNI_MIN_DIGITOS <= len(dni) <= DNI_MAX_DIGITOS):
            messagebox.showwarning(
                "DNI inválido",
                f"El DNI debe contener solo números ({DNI_MIN_DIGITOS} u {DNI_MAX_DIGITOS} dígitos)."
            )
            return

        # 1. Ver si el DNI ya existe y, en ese caso, pedir confirmación
        #    ANTES de tocar cualquier archivo o dato.
        try:
            actualizar = estudiante_existe(dni)
        except sqlite3.Error as e:
            messagebox.showerror("Error DB", f"No se pudo consultar la base de datos: {e}")
            return

        if actualizar:
            confirmar = messagebox.askyesno(
                "DNI existente",
                f"El DNI {dni} ya está registrado.\n"
                "¿Querés actualizar sus datos?"
            )
            if not confirmar:
                return  # No se modificó nada (ni base ni QR)

        # 2. Generar el QR en un archivo temporal (no pisa el QR actual todavía)
        ruta_final = ruta_qr_estudiante(dni)
        ruta_temporal = f"{QR_DIR}/qr_{dni}.tmp.png"
        datos_qr_text = generar_datos_qr_estructurados(nombre, apellido, dni, aula)

        try:
            generar_y_guardar_imagen_qr(datos_qr_text, ruta_temporal)
        except Exception as e:
            borrar_archivo_si_existe(ruta_temporal)
            messagebox.showerror("Error QR", f"No se pudo generar la imagen del QR: {e}")
            return

        # 3. Preparar datos completos para la DB
        datos_estudiante_db = {
            "dni": dni,
            "nombre": nombre,
            "apellido": apellido,
            "localidad": self.localidad_entry.get().strip(),
            "colegio": self.colegio_entry.get().strip(),
            "curso": self.curso_entry.get().strip(),
            "aula_asignada": aula,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "qr_path": ruta_final
        }

        # 4. Guardar en SQLite
        exito, msg = guardar_estudiante_db(datos_estudiante_db, actualizar)

        if not exito:
            # Si falló la base, no queda ningún QR huérfano ni se pisa el anterior
            borrar_archivo_si_existe(ruta_temporal)
            messagebox.showerror("Error DB", msg)
            return

        # 5. La base ya está guardada: ahora sí reemplazamos el QR definitivo
        try:
            os.replace(ruta_temporal, ruta_final)
        except OSError as e:
            borrar_archivo_si_existe(ruta_temporal)
            messagebox.showerror(
                "Error QR",
                f"El estudiante se guardó, pero no se pudo guardar la imagen del QR: {e}"
            )
            return

        self.qr_generado_path = ruta_final
        self.mostrar_previsualizacion_qr()
        self.btn_compartir.configure(state="normal")
        messagebox.showinfo("Éxito", f"{msg}\nQR generado para {nombre}.")


    def mostrar_previsualizacion_qr(self):
        """Muestra el QR recién generado en la interfaz."""
        if self.qr_generado_path and os.path.exists(self.qr_generado_path):
            img = Image.open(self.qr_generado_path)
            img = img.resize((220, 220)) # Redimensionar para la vista
            imgtk = ImageTk.PhotoImage(image=img)
            self.lbl_qr_preview.imgtk = imgtk
            self.lbl_qr_preview.configure(image=imgtk, text="",width=220, height=220)

    def compartir_qr(self):
        """Permite guardar una copia del QR en otra ubicación."""
        if self.qr_generado_path:
            # Preguntar dónde guardar la copia
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("Imagen PNG", "*.png")],
                title="Guardar una copia del QR para enviar",
                initialfile=os.path.basename(self.qr_generado_path)
            )
            if filename:
                import shutil
                shutil.copy2(self.qr_generado_path, filename)
                messagebox.showinfo("Copia Guardada", "Se ha guardado una copia del QR.")

class BuscadorAulaApp(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg=COLOR_FONDO)
        self.title("Control de Exámenes - Escáner de Aulas")
        self.geometry("680x640+100+0")
        self.resizable(False, False)
        self.iconbitmap("assets/PROAico.ico")
        self.transient(parent)
        frame_camara = tk.Frame(self, bg=COLOR_TEXTO, bd=2, relief="solid")
        frame_camara.pack(pady=5)
        self.grab_set()

        # --- UI - Título principal ---
        self.lbl_titulo = tk.Label(
            self, 
            text="Escanee su código QR de examen", 
            font=("Arial", 16, "bold"), 
            bg=COLOR_FONDO, 
            fg="#333333"
        )
        self.lbl_titulo.pack(pady=15)

        # --- UI - Feed de cámara ---
        # Imagen negra de 460x360: mantiene el tamaño del recuadro cuando no hay
        # video y permite mostrar un mensaje de aviso encima.
        self.img_placeholder = ImageTk.PhotoImage(Image.new("RGB", (460, 360), "black"))
        self.lbl_video = tk.Label(
            frame_camara,
            image=self.img_placeholder,
            text="",
            compound="center",
            font=("Arial", 13, "bold"),
            fg="white",
            bg="black",
            width=460,
            height=360
        )
        self.lbl_video.pack()

        # --- UI - Resultado Detallado ---
        frame_resultados = tk.LabelFrame(self, text=" Datos Detectados ", font=("Arial", 11, "bold"), bg=COLOR_FONDO, pady=10, padx=10)
        frame_resultados.pack(pady=10, padx=20, fill="x")

        self.lbl_estudiante = tk.Label(
            frame_resultados,
            text="Esperando lectura...",
            font=("Arial", 12),
            bg=COLOR_FONDO,
            anchor="w",
            justify="left",
            wraplength=600  # si el texto es largo, baja de línea en vez de cortarse
        )
        self.lbl_estudiante.pack(fill="x")

        # Resultado principal del Aula (grande y claro)
        self.lbl_aula = tk.Label(
            self, 
            text="AULA: --", 
            font=("Arial", 22, "bold"), 
            bg=COLOR_FONDO, 
            fg="#4a5568",
            width=30,
            height=2,
            relief="solid",
            bd=1
        )
        self.lbl_aula.pack(pady=20)

        # --- Estado de la cámara y del detector de QR ---
        self.cap = None
        self.ventana_bucle = None
        self.fallos_lectura = 0
        self.detector = cv2.QRCodeDetector()
        self.escaneo_activo = False  # se activa recién cuando la cámara abre bien

        self.btn_reiniciar = tk.Button(
            self, 
            text="Escanear otro código", 
            font=("Arial", 12, "bold"),
            bg="#3182ce", 
            fg="white",
            command=self.reiniciar_escaneo,
            padx=10,
            pady=5
        )

        self.btn_reintentar_camara = tk.Button(
            self,
            text="Reintentar cámara",
            font=("Arial", 12, "bold"),
            bg=COLOR_AZUL_PROA,
            fg="white",
            command=self.iniciar_camara,
            padx=10,
            pady=5
        )

        # Asegurar liberación de cámara si se cierra esta ventana con la X
        self.protocol("WM_DELETE_WINDOW", self.liberar_y_cerrar)

        self.iniciar_camara()

    # ------------------------------------------------------------------
    # Cámara
    # ------------------------------------------------------------------
    def iniciar_camara(self):
        """Abre la cámara. Si no se puede, avisa y ofrece reintentar."""
        self.detener_camara()  # por si quedó una abierta (caso "Reintentar")
        self.fallos_lectura = 0

        self.cap = cv2.VideoCapture(INDICE_CAMARA)
        if not self.cap.isOpened():
            self.camara_no_disponible(
                "No se detectó ninguna cámara.\n"
                "Conectala y presioná «Reintentar cámara»."
            )
            return

        # La cámara abrió bien: limpiar avisos y empezar a escanear
        self.btn_reintentar_camara.pack_forget()
        self.lbl_video.configure(text="")
        self.reiniciar_escaneo()
        self.actualizar_camara()

    def detener_camara(self):
        """Cancela el bucle de video y libera la cámara (es seguro llamarlo varias veces)."""
        if self.ventana_bucle is not None:
            self.after_cancel(self.ventana_bucle)
            self.ventana_bucle = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def camara_no_disponible(self, mensaje):
        """Deja la ventana en estado 'sin cámara' con un aviso claro para el usuario."""
        self.escaneo_activo = False
        self.detener_camara()

        self.lbl_video.configure(image=self.img_placeholder, text=mensaje)
        self.lbl_video.imgtk = self.img_placeholder
        self.lbl_estudiante.configure(text="Cámara no disponible.")
        self.lbl_aula.configure(text="SIN CÁMARA", bg=COLOR_ERROR_BG, fg=COLOR_ERROR_FG)
        self.btn_reiniciar.pack_forget()
        self.btn_reintentar_camara.pack(pady=5)

        messagebox.showwarning("Cámara no disponible", mensaje, parent=self)

    def actualizar_camara(self):
        if self.cap is None:
            return

        ret, frame = self.cap.read()

        if not ret or frame is None:
            # Sin imagen: si pasa muchas veces seguidas, la cámara se desconectó
            self.fallos_lectura += 1
            if self.fallos_lectura >= FALLOS_MAXIMOS_LECTURA:
                self.camara_no_disponible(
                    "Se perdió la señal de la cámara.\n"
                    "Revisá la conexión y presioná «Reintentar cámara»."
                )
                return
        else:
            self.fallos_lectura = 0

            if self.escaneo_activo:
                # data contendrá el string JSON si encuentra un QR
                try:
                    data, bbox, _ = self.detector.detectAndDecode(frame)
                except cv2.error:
                    data = ""  # OpenCV puede fallar con algún fotograma: lo ignoramos
                
                if data:
                    self.mostrar_resultado_estructurado(data)

            frame_reducido = cv2.resize(frame, (460, 360))
            cv2image = cv2.cvtColor(frame_reducido, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.lbl_video.imgtk = imgtk
            self.lbl_video.configure(image=imgtk)
        
        self.ventana_bucle = self.after(15, self.actualizar_camara)

    # ------------------------------------------------------------------
    # Resultado del escaneo
    # ------------------------------------------------------------------
    def mostrar_resultado(self, texto_estudiante, texto_aula, bg, fg):
        """Muestra un resultado en pantalla y habilita escanear otro código."""
        self.lbl_estudiante.configure(text=texto_estudiante)
        self.lbl_aula.configure(text=texto_aula, bg=bg, fg=fg)
        self.btn_reiniciar.pack(pady=5)

    def mostrar_resultado_estructurado(self, contenido_qr_raw):
        self.escaneo_activo = False

        # 1. ¿El QR tiene el formato esperado?
        datos_qr = interpretar_qr(contenido_qr_raw)
        if datos_qr is None:
            self.mostrar_resultado(
                "Resultado de Lectura: formato no reconocido.",
                "CÓDIGO QR NO VÁLIDO",
                COLOR_ERROR_BG, COLOR_ERROR_FG
            )
            return

        dni = datos_qr["dni"]
        dni_visible = dni if len(dni) <= 20 else dni[:20] + "…"

        # 2. Los datos reales se consultan en la base de datos (no se confía en el QR)
        try:
            estudiante = buscar_estudiante_por_dni(dni)
        except sqlite3.Error as e:
            self.mostrar_resultado(
                f"No se pudo consultar la base de datos: {e}",
                "ERROR DE BASE DE DATOS",
                COLOR_ERROR_BG, COLOR_ERROR_FG
            )
            return

        # 3. DNI que no está registrado
        if estudiante is None:
            self.mostrar_resultado(
                f"El DNI {dni_visible} no figura en la base de datos.",
                "ESTUDIANTE NO REGISTRADO",
                COLOR_ERROR_BG, COLOR_ERROR_FG
            )
            return

        # 4. Estudiante registrado: mostrar el aula que figura HOY en la base
        nombre_completo = f"{estudiante['nombre']} {estudiante['apellido']}"
        aula_actual = estudiante["aula_asignada"]
        texto_estudiante = f"Estudiante: {nombre_completo} | DNI: {estudiante['dni']}"

        aula_qr = datos_qr["aula"]
        if aula_qr and aula_qr != aula_actual:
            # El QR es viejo: el aula cambió después de imprimirlo
            self.mostrar_resultado(
                texto_estudiante + f" | El QR indica aula {aula_qr} (desactualizado)",
                f"AULA ASIGNADA: {aula_actual}",
                COLOR_AVISO_BG, COLOR_AVISO_FG
            )
        else:
            self.mostrar_resultado(
                texto_estudiante,
                f"AULA ASIGNADA: {aula_actual}",
                COLOR_EXITO_BG, COLOR_EXITO_FG
            )

    def reiniciar_escaneo(self):
        self.escaneo_activo = True
        self.lbl_estudiante.configure(text="Esperando lectura...")
        self.lbl_aula.configure(
            text="AULA: Esperando...", 
            bg=COLOR_FONDO, 
            fg=COLOR_TEXTO
        )
        self.btn_reiniciar.pack_forget()

    def liberar_y_cerrar(self):
        """Apaga la cámara y cierra solo esta ventana secundaria."""
        self.detener_camara()
        self.destroy()

# --- Ventana Principal (Menú) ---

class MenuPrincipal:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Sistema ProA - Control de Exámenes y Aulas")
        # CAMBIO: Ancho ampliado a 920px para que entren las 4 tarjetas cómodamente
        self.ventana.geometry("920x500+100+0")
        self.ventana.configure(bg=COLOR_FONDO)
        self.ventana.resizable(False, False)
        self.ventana.iconbitmap("assets/PROAico.ico")

        # Título principal
        self.lbl_titulo = tk.Label(
            ventana, 
            text="PANEL DE CONTROL (Exámenes y Aulas)", 
            font=("Candara", 20, "bold"), 
            bg=COLOR_FONDO, 
            fg=COLOR_AZUL_PROA
        )
        self.lbl_titulo.pack(pady=10)

        # Contenedor principal de tarjetas
        frame_tarjeta = tk.Frame(ventana, bg=COLOR_TARJETA, bd=1, relief="solid", pady=25, padx=15)
        frame_tarjeta.pack(pady=8, padx=10)

        # Cargar imágenes reducidas a un tamaño uniforme (65x65)
        self.img_boton1 = ImageTk.PhotoImage(Image.open("assets/nuevo_estudiante.png").resize((65, 65)))
        self.img_boton2 = ImageTk.PhotoImage(Image.open("assets/codigo_qr.png").resize((65, 65)))
        # Mantenemos las imágenes existentes como fallback visual si no tienes íconos específicos aún
        self.img_excel = self.img_boton1  
        self.img_lista = self.img_boton2  

        # --- BOTÓN 1: Exportar Lista ---
        self.btn_exportar = tk.Button(
            frame_tarjeta, 
            text="\nExportar Lista\na Excel / CSV", # '\n' crea el margen con la imagen
            font=("Arial", 10, "bold"),
            bg="#5B7065", # Tono oliva/verde institucional
            fg="white",
            activebackground="#46574E",
            activeforeground="white",
            command=self.exportar_excel,
            image=self.img_excel,
            compound=tk.TOP,
            width=190,
            height=140,
            bd=0,
            cursor="hand2"
        )
        self.btn_exportar.pack(side="left", padx=8)

        # --- BOTÓN 2: Ver / Ordenar ---
        self.btn_ver = tk.Button(
            frame_tarjeta, 
            text="\nVer / Ordenar\nEstudiantes", 
            font=("Arial", 10, "bold"),
            bg="#6C5B7B", # Tono púrpura/violeta
            fg="white",
            activebackground="#544661",
            activeforeground="white",
            command=self.ver_estudiantes,
            image=self.img_lista,
            compound=tk.TOP,
            width=190,
            height=140,
            bd=0,
            cursor="hand2"
        )
        self.btn_ver.pack(side="left", padx=8)

        # --- BOTÓN 3: Nuevo Estudiante ---
        self.btn_1 = tk.Button(
            frame_tarjeta, 
            text="\nNuevo Estudiante\n- Generar QR -", 
            font=("Arial", 10, "bold"),
            bg=COLOR_AZUL_PROA,
            fg="white",
            activebackground="#072A54",
            activeforeground="white",
            command=self.abrir_formulario,
            image=self.img_boton1,
            compound=tk.TOP,
            width=190,
            height=140,
            bd=0,
            cursor="hand2"
        )
        self.btn_1.pack(side="left", padx=8)
        
        # --- BOTÓN 4: Escáner ---
        self.btn_2 = tk.Button(
            frame_tarjeta, 
            text="\nAbrir Escáner\nde Aula", 
            font=("Arial", 10, "bold"),
            bg="#C09038", # Tono ocre/dorado
            fg="white", 
            activebackground="#9E752A",
            activeforeground="white",
            command=self.abrir_escaner,
            image=self.img_boton2,
            compound=tk.TOP,
            width=190,
            height=140,
            bd=0,
            cursor="hand2"
        )
        self.btn_2.pack(side="left", padx=8)
    
        # Logo institucional inferior
        img_logo = Image.open("assets/PROA LOGO1.png")
        img_logo = img_logo.resize((130, 140))
        img_logo = ImageTk.PhotoImage(img_logo)
        self.lbl_logo = tk.Label(ventana, image=img_logo, bg=COLOR_FONDO)
        self.lbl_logo.image = img_logo
        self.lbl_logo.pack(pady=24)

        # FRAME MARCO INFERIOR 
        marco_inf=tk.Label(ventana, bg=COLOR_AZUL_PROA, width=920, height=50)
        marco_inf.pack()
    def abrir_formulario(self):
        """Abre la ventana secundaria del formulario."""
        FormularioEstudiante(self.ventana)

    def abrir_escaner(self):
        """Abre la ventana secundaria del escáner."""
        BuscadorAulaApp(self.ventana)

    def exportar_excel(self):
        """Función para exportar la base de datos a Excel / CSV."""
        # TODO: Implementar la lógica con pandas o csv
        messagebox.showinfo("Exportar", "Función de exportación a Excel / CSV en desarrollo.")

    def ver_estudiantes(self):
        """Función para abrir la vista de tabla con lista de estudiantes."""
        # TODO: Implementar ventana de tabla (Treeview)
        messagebox.showinfo("Ver Estudiantes", "Función de visualización y ordenamiento en desarrollo.")

# --- Ejecución Principal ---
if __name__ == "__main__":
    # 1. Asegurar que la DB y carpetas existen
    inicializar_base_de_datos()
    
    # 2. Iniciar la aplicación
    root = tk.Tk()
    app = MenuPrincipal(root)
    root.mainloop()