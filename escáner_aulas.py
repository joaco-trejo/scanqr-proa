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
COLOR_AZUL_PROA = "#0A3B74"     # Azul oficial ProA
COLOR_ROJO_PROA = "#E31B23"     # Rojo oficial ProA
COLOR_BORDE = "#D0D7DE"         # Bordes sutiles

# Estados de alerta para el escáner
COLOR_EXITO_BG = "#D4EDDA"
COLOR_EXITO_FG = "#155724"
COLOR_ERROR_BG = "#F8D7DA"
COLOR_ERROR_FG = "#721C24"

# --- Configuración de la Base de Datos SQLite ---
DB_NAME = "examenes.db" # se guarda el nombre del archivo en una variable

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

def guardar_estudiante_db(datos):
    """Guarda o actualiza un estudiante en la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO estudiantes 
            (dni, nombre, apellido, localidad, colegio, curso, aula_asignada, fecha_registro, qr_path)
            VALUES (:dni, :nombre, :apellido, :localidad, :colegio, :curso, :aula_asignada, :fecha_registro, :qr_path)
        ''', datos)
        conn.commit()
        return True, "Estudiante guardado exitosamente."
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

def generar_y_guardar_imagen_qr(datos_qr_text, dni):
    """Genera la imagen del QR y la guarda localmente."""
    if not os.path.exists("qrcodes"):
        os.makedirs("qrcodes")
    
    filename = f"qrcodes/qr_{dni}.png"
    
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
    img.save(filename)
    
    return filename

# --- Clases de la Interfaz Gráfica (GUI) ---

class FormularioEstudiante(tk.Toplevel):
    """Ventana secundaria para el ingreso de datos del estudiante."""
    def __init__(self, parent):
        
        super().__init__(parent)
        self.color_fondo_ventana_datos = "#9bb5f8"
        self.title("Ingresar Nuevo Estudiante - Generar QR")
        self.geometry("560x700+100+0")
        self.configure(bg=COLOR_FONDO)
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
        frame = tk.Frame(parent, bg=self.color_fondo_ventana_datos)
        frame.pack(fill="x", pady=5)
        
        lbl = tk.Label(frame, text=label_text, font=("Arial", 10,"bold","italic"), bg=self.color_fondo_ventana_datos, width=25, anchor="e")
        lbl.pack(side="left")
        
        entry = tk.Entry(frame, font=("Arial", 10))
        entry.pack(side="left", fill="x", expand=True)
        # Guardamos la referencia de la entrada dinámicamente en la clase
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

        # 1. Generar el contenido estructurado del QR (JSON)
        datos_qr_text = generar_datos_qr_estructurados(nombre, apellido, dni, aula)

        # 2. Generar y guardar la imagen del QR
        try:
            self.qr_generado_path = generar_y_guardar_imagen_qr(datos_qr_text, dni)
        except Exception as e:
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
            "qr_path": self.qr_generado_path
        }

        # 4. Guardar en SQLite
        exito, msg = guardar_estudiante_db(datos_estudiante_db)
        if exito:
            self.mostrar_previsualizacion_qr()
            self.btn_compartir.configure(state="normal")
            messagebox.showinfo("Éxito", f"Estudiante {nombre} guardado y QR generado.")
        else:
            messagebox.showerror("Error DB", msg)

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
    """Ventana del escáner (Adaptada para leer QR estructurado)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.color_fondo_ventana_escaner = "#9bb5f8"
        self.title("Control de Exámenes - Escáner de Aulas")
        self.geometry("700x650+100+0")
        self.resizable(False, False)
        self.configure(bg=self.color_fondo_ventana_escaner)
        self.iconbitmap("assets/PROAico.ico")
        self.transient(parent)
        self.grab_set()

        # --- UI - Título principal ---
        self.lbl_titulo = tk.Label(
            self, 
            text="Escanee su código QR de examen", 
            font=("Arial", 16, "bold"), 
            bg=self.color_fondo_ventana_escaner, 
            fg="#333333"
        )
        self.lbl_titulo.pack(pady=15)

        # --- UI - Feed de cámara ---
        self.lbl_video = tk.Label(self, bg="black", width=350, height=290)
        self.lbl_video.pack(pady=10)

        # --- UI - Resultado Detallado ---
        frame_resultados = tk.LabelFrame(self, text=" Datos Detectados ", font=("Arial", 11, "bold"), bg=self.color_fondo_ventana_escaner, pady=10, padx=10)
        frame_resultados.pack(pady=10, padx=20, fill="x")

        self.lbl_estudiante = tk.Label(frame_resultados, text="Esperando lectura...", font=("Arial", 12), bg=self.color_fondo_ventana_escaner, anchor="w")
        self.lbl_estudiante.pack(fill="x")

        # Resultado principal del Aula (grande y claro)
        self.lbl_aula = tk.Label(
            self, 
            text="AULA: --", 
            font=("Arial", 22, "bold"), 
            bg=self.color_fondo_ventana_escaner, 
            fg="#4a5568",
            width=30,
            height=2,
            relief="solid",
            bd=1
        )
        self.lbl_aula.pack(pady=20)

        # --- Lógica de la Cámara y QR ---
        self.cap = cv2.VideoCapture(0)
        self.detector = cv2.QRCodeDetector()
        self.escaneo_activo = True

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

        self.actualizar_camara()

        # Asegurar liberación de cámara si se cierra esta ventana con la X
        self.protocol("WM_DELETE_WINDOW", self.liberar_y_cerrar)

    def actualizar_camara(self):
        ret, frame = self.cap.read()
        
        if ret:
            if self.escaneo_activo:
                # data contendrá el string JSON si encuentra un QR
                data, bbox, _ = self.detector.detectAndDecode(frame)
                
                if data:
                    self.mostrar_resultado_estructurado(data)

            frame_reducido = cv2.resize(frame, (350, 290))
            cv2image = cv2.cvtColor(frame_reducido, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.lbl_video.imgtk = imgtk
            self.lbl_video.configure(image=imgtk)
        
        self.ventana_bucle = self.after(15, self.actualizar_camara)

    def mostrar_resultado_estructurado(self, contenido_qr_raw):
        """Parsea el JSON del QR y actualiza la UI."""
        self.escaneo_activo = False
        
        try:
            # 1. Intentamos parsear el contenido como JSON
            datos = json.loads(contenido_qr_raw)
            
            # 2. Extraemos los campos que definimos en la generación
            nombre_completo = datos.get("nombre_completo", "Desconocido")
            dni = datos.get("dni", "--")
            aula = datos.get("aula", "NO ASIGNADA")

            # 3. Actualizamos la UI
            self.lbl_estudiante.configure(text=f"Estudiante: {nombre_completo}\nDNI: {dni}")
            self.lbl_aula.configure(
                text=f"AULA ASIGNADA:\n{aula}", 
                bg="#c6f6d5", # Verde suave
                fg="#22543d"
            )
            
        except json.JSONDecodeError:
            # El QR no contiene datos válidos para este sistema
            self.lbl_estudiante.configure(text="Error de Lectura:")
            self.lbl_aula.configure(
                text=f"CÓDIGO QR NO VÁLIDO\nO CORRUPTO",
                bg="#fed7d7", # Rojo suave
                fg="#822727"
            )
        
        self.btn_reiniciar.pack(pady=5)

    def reiniciar_escaneo(self):
        self.escaneo_activo = True
        self.lbl_estudiante.configure(text="Esperando lectura...")
        self.lbl_aula.configure(
            text="AULA: Esperando...", 
            bg=self.color_fondo_ventana_escaner, 
            fg="#4a5568"
        )
        self.btn_reiniciar.pack_forget()

    def liberar_y_cerrar(self):
        """Apaga la cámara y cierra solo esta ventana secundaria."""
        if self.cap.isOpened():
            self.cap.release()
        self.after_cancel(self.ventana_bucle) # Cancelar el bucle after
        self.destroy()

# --- Ventana Principal (Menú) ---

class MenuPrincipal:
    def __init__(self, ventana):
        self.ventana = ventana
        color_fondo = "#b7d0f7"
        self.ventana.title("Panel de Control de Exámenes - Gestión Integral")
        self.ventana.geometry("700x500+100+0")
        self.ventana.configure(bg=color_fondo)
        self.ventana.resizable(False, False)
        self.ventana.iconbitmap("assets/PROAico.ico")

        # --- Título principal ---
        self.lbl_titulo = tk.Label(
            ventana, 
            text="PANEL DE CONTROL (Exámenes y Aulas)", 
            font=("Candara", 20, "bold"), 
            bg=color_fondo, 
            fg="#7D0606"
        )
        self.lbl_titulo.pack(pady=20)

        # --- Contenedor de Botones ---
        frame_botones = tk.Frame(ventana, bg=color_fondo, borderwidth=3, relief="groove", pady=20)
        frame_botones.pack(pady=10)

        # Imágenes de los botones (Rutas adaptadas a assets)
        self.img_boton1 = Image.open("assets/nuevo_estudiante.png")
        self.img_boton1 = self.img_boton1.resize((100, 100))
        self.img_boton1 = ImageTk.PhotoImage(self.img_boton1)
        
        self.img_boton2 = Image.open("assets/codigo_qr.png")
        self.img_boton2 = self.img_boton2.resize((100, 100))
        self.img_boton2 = ImageTk.PhotoImage(self.img_boton2)
        
        self.btn_1 = tk.Button(
            frame_botones, 
            text="Ingresar Nuevo Estudiante\n- Generar QR -", 
            font=("Arial", 14, "bold", "italic"),
            bg="#3182ce", # Azul
            fg="white",
            command=self.abrir_formulario,
            image=self.img_boton1,
            compound=tk.TOP,
            width=270,
            height=160,
            relief="raised",
            bd=3,
            cursor="hand2"
        )
        self.btn_1.pack(side="left", padx=25)
        
        self.btn_2 = tk.Button(
            frame_botones, 
            text="Abrir Escáner\nde Aula", 
            font=("Arial", 14, "bold", "italic"),
            bg="#c29e28", # Naranja
            fg="white",
            command=self.abrir_escaner,
            image=self.img_boton2,
            compound=tk.TOP,
            width=270,
            height=160,
            relief="raised",
            bd=3,
            cursor="hand2"
        )
        self.btn_2.pack(side="left", padx=25)
    
        # ---- Logo de la Institución (Ruta adaptada a assets) ---- #
        img_logo = Image.open("assets/PROA LOGO1.png")
        img_logo = img_logo.resize((150, 160))
        img_logo = ImageTk.PhotoImage(img_logo)
        self.lbl_logo = tk.Label(ventana, image=img_logo, bg=color_fondo)
        self.lbl_logo.image = img_logo # Mantener referencia
        self.lbl_logo.pack(pady=10)


    def abrir_formulario(self):
        """Abre la ventana secundaria del formulario."""
        FormularioEstudiante(self.ventana)

    def abrir_escaner(self):
        """Abre la ventana secundaria del escáner."""
        BuscadorAulaApp(self.ventana)

# --- Ejecución Principal ---
if __name__ == "__main__":
    # 1. Asegurar que la DB y carpetas existen
    inicializar_base_de_datos()
    
    # 2. Iniciar la aplicación
    root = tk.Tk()
    app = MenuPrincipal(root)
    root.mainloop()