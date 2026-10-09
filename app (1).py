import streamlit as st
import sqlite3
import pandas as pd
import time
from datetime import date
import re

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (NEGRO & AMARILLO)
# ---------------------------------------------------------
st.set_page_config(
    page_title="YSIVAMOS - Fitness Tracker",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de CSS Personalizado para Tema Negro/Amarillo de Alto Contraste
st.markdown("""
<style>
    /* Estilos Generales de la App */
    .stApp {
        background-color: #0E0E0E;
        color: #F5F5F5;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #161616;
        border-right: 1px solid #282828;
    }

    /* Títulos e Headers */
    h1, h2, h3, h4 {
        color: #FFD700 !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }

    /* Botones Principales (Amarillo Neón / Texto Negro Bold) */
    div.stButton > button:first-child {
        background: #FFD700 !important;
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 12px rgba(255, 215, 0, 0.2);
    }
    div.stButton > button:first-child:hover {
        background: #FFC400 !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(255, 215, 0, 0.4);
    }

    /* Inputs y Campos de Texto */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #FFD700 !important;
        box-shadow: 0 0 0 1px #FFD700 !important;
    }

    /* Tarjetas y Contenedores */
    .css-card {
        background-color: #181818;
        border: 1px solid #282828;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Tablas de Pandas / Dataframes */
    [data-testid="stDataFrame"] {
        background-color: #181818;
        border: 1px solid #2D2D2D;
        border-radius: 8px;
    }

    /* Métrica Destacada */
    [data-testid="stMetricValue"] {
        color: #FFD700 !important;
        font-size: 2.2rem !important;
        font-weight: 800;
    }

    /* Alertas / Informaciones */
    .stAlert {
        background-color: #1A1A1A;
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. BASE DE DATOS Y AUTENTICACIÓN
# ---------------------------------------------------------
conn = sqlite3.connect("fitness_app.db", check_same_thread=False)
c = conn.cursor()

# Tablas de Usuarios, Registros y Nutrición
c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, status TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS registro_entrenamiento 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, fecha TEXT, bloque TEXT, ejercicio TEXT, peso REAL, reps INT, rpe INT)''')

c.execute('''CREATE TABLE IF NOT EXISTS registro_nutricion 
             (user_email TEXT, fecha TEXT, proteinas REAL, carbos REAL, grasas REAL, agua REAL, PRIMARY KEY (user_email, fecha))''')
conn.commit()

# Manejo de Estado de Sesión Persistente
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'auth_stage' not in st.session_state:
    st.session_state['auth_stage'] = 'login' # login, verify, set_password
if 'temp_email' not in st.session_state:
    st.session_state['temp_email'] = ""

# ----------------- BASE DE DATOS DE EJERCICIOS Y TÉCNICA -----------------
RUTINAS = {
    "⚡ Día 1: Upper (Torso - Fuerza)": [
        "Press Inclinado con Mancuernas",
        "Jalón al Pecho Agarre Abierto",
        "Press Militar con Mancuernas Sentado",
        "Remo Bajo en Polea Agarre Neutro/Triángulo",
        "Superset: Rosca en Polea + Tríceps Cuerda"
    ],
    "⚡ Día 2: Lower (Pierna - Fuerza)": [
        "Sentadilla Libre con Barra",
        "Leg Press 45°",
        "Sillón Extensor",
        "Camilla Flexora",
        "Elevación de Talones / Pantorrilla Sentado",
        "Plancha Abdominal (Core)"
    ],
    "⚡ Día 4: Push (Empuje - Hipertrofia)": [
        "Supino Inclinado o Plano (Barra/Mancuernas)",
        "Crossover en Polea Alta",
        "Elevaciones Laterales con Mancuernas",
        "Desarrollo de Hombros en Máquina o Mancuernas",
        "Tríceps Francés con Mancuerna/Anilla",
        "Tríceps en Polea con Cuerda"
    ],
    "⚡ Día 5: Pull (Tirón - Hipertrofia)": [
        "Jalón Neutro (Triángulo)",
        "Remo Unilateral con Mancuerna",
        "Crucifijo Inverso en Máquina (Hombro Posterior)",
        "Encogimiento de Hombros con Mancuernas (Trapézio)",
        "Rosca Directa en Polea con Barra Recta",
        "Rosca Alternada con Mancuernas"
    ],
    "⚡ Día 6: Legs (Pierna 2 - Cadena Posterior)": [
        "Leg Press 45°",
        "Camilla Flexora",
        "Sillón Extensor",
        "Máquina de Aducción de Cadera",
        "Máquina de Abducción de Cadera",
        "Pantorrilla en Leg Press o Sentado"
    ]
}

# ---------------------------------------------------------
# 3. MÓDULO DE LOGIN Y AUTENTICACIÓN
# ---------------------------------------------------------
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>⚡ YSIVAMOS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #AAAAAA;'>Tu Plataforma de Entrenamiento y Nutrición</p>", unsafe_allow_html=True)
        st.divider()

        if st.session_state['auth_stage'] == 'login':
            st.subheader("Iniciar Sesión / Registro")
            email_input = st.text_input("Correo Electrónico", placeholder="tu@email.com")
            
            st.markdown("**O ingresa de forma rápida con:**")
            col_g, col_e = st.columns(2)
            with col_g:
                if st.button("🌐 Entrar con Google"):
                    # Simulación de auth directo con Google
                    st.session_state['user'] = "usuario_google@gmail.com"
                    st.rerun()

            with col_e:
                if st.button("📩 Enviar Código OTP"):
                    if re.match(r"[^@]+@[^@]+\.[^@]+", email_input):
                        st.session_state['temp_email'] = email_input
                        st.session_state['auth_stage'] = 'verify'
                        st.success("¡Código de verificación enviado a tu correo! (Código de prueba: 123456)")
                        st.rerun()
                    else:
                        st.error("Por favor, ingresa un correo válido.")

            st.divider()
            st.markdown("### ¿Ya tienes contraseña?")
            pass_input = st.text_input("Contraseña", type="password")
            if st.button("Ingresar con Contraseña"):
                c.execute("SELECT email FROM usuarios WHERE email=? AND password=?", (email_input, pass_input))
                user = c.fetchone()
                if user:
                    st.session_state['user'] = user[0]
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos.")

        elif st.session_state['auth_stage'] == 'verify':
            st.subheader(f"Verificar Correo: {st.session_state['temp_email']}")
            code_input = st.text_input("Ingresa el código de 6 dígitos", placeholder="123456")
            
            if st.button("Verificar Código"):
                if code_input == "123456": # Código de prueba simulado
                    c.execute("INSERT OR IGNORE INTO usuarios (email, status) VALUES (?, ?)", (st.session_state['temp_email'], "activo"))
                    conn.commit()
                    st.session_state['auth_stage'] = 'set_password'
                    st.rerun()
                else:
                    st.error("Código incorrecto. Prueba con 123456")

        elif st.session_state['auth_stage'] == 'set_password':
            st.subheader("Define tu Contraseña (Opcional)")
            new_pass = st.text_input("Nueva Contraseña", type="password")
            
            if st.button("Guardar Contraseña e Ingresar"):
                if new_pass:
                    c.execute("UPDATE usuarios SET password=? WHERE email=?", (new_pass, st.session_state['temp_email']))
                    conn.commit()
                st.session_state['user'] = st.session_state['temp_email']
                st.session_state['auth_stage'] = 'login'
                st.rerun()

# ---------------------------------------------------------
# 4. APLICACIÓN PRINCIPAL (POST-LOGIN)
# ---------------------------------------------------------
if not st.session_state['user']:
    login_screen()
else:
    # Sidebar de Usuario y Navegación
    st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state['user']}`")
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state['user'] = None
        st.session_state['auth_stage'] = 'login'
        st.rerun()

    st.sidebar.divider()
    opcion = st.sidebar.radio("Navegación", ["🏋️ Entrenamiento", "⏱️ Temporizador", "🥗 Nutrición", "📈 Sobrecarga Progresiva"])

    # ----------------- 1. REGISTRO DE ENTRENAMIENTO -----------------
    if opcion == "🏋️ Entrenamiento":
        st.markdown("# 🏋️ Registro de Rutina Diaria")
        
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.markdown("<div class='css-card'>", unsafe_allow_html=True)
            bloque_sel = st.selectbox("Selecciona la sesión de hoy:", list(RUTINAS.keys()))
            ejercicio_sel = st.selectbox("Selecciona el Ejercicio:", RUTINAS[bloque_sel])
            
            col_p, col_r = st.columns(2)
            with col_p:
                peso = st.number_input("Carga Utilizada (kg)", min_value=0.0, value=20.0, step=0.5)
            with col_r:
                reps = st.number_input("Repeticiones", min_value=1, value=10, step=1)
                
            rpe = st.select_slider("Esfuerzo Percibido (RPE)", options=list(range(1, 11)), value=8)
            
            if st.button("💾 Guardar Serie", use_container_width=True):
                fecha_actual = str(date.today())
                c.execute("INSERT INTO registro_entrenamiento (user_email, fecha, bloque, ejercicio, peso, reps, rpe) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (st.session_state['user'], fecha_actual, bloque_sel, ejercicio_sel, peso, reps, rpe))
                conn.commit()
                st.success(f"¡Serie registrada! {ejercicio_sel} -> {peso} kg x {reps} reps")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='css-card'>", unsafe_allow_html=True)
            st.subheader("💡 Guía de Técnica")
            st.info("💡 Mantén la escápula retraída, rango de movimiento completo y controla la bajada en 2-3 segundos.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()
        st.subheader("📋 Series Registradas Hoy")
        df_hoy = pd.read_sql_query(f"SELECT bloque, ejercicio, peso, reps, rpe FROM registro_entrenamiento WHERE user_email='{st.session_state['user']}' AND fecha='{date.today()}'", conn)
        if not df_hoy.empty:
            st.dataframe(df_hoy, use_container_width=True)
        else:
            st.info("Aún no has registrado series el día de hoy.")

    # ----------------- 2. TEMPORIZADOR DE DESCANSO -----------------
    elif opcion == "⏱️ Temporizador":
        st.markdown("# ⏱️ Cronómetro Inter-Series")
        col_t1, col_t2, col_t3 = st.columns(3)
        tiempo_seg = 0
        if col_t1.button("60s (Accesorios)"):
            tiempo_seg = 60
        if col_t2.button("90s (Hipertrofia)"):
            tiempo_seg = 90
        if col_t3.button("120s (Fuerza)"):
            tiempo_seg = 120

        if tiempo_seg > 0:
            placeholder = st.empty()
            for i in range(tiempo_seg, -1, -1):
                mins, secs = divmod(i, 60)
                placeholder.markdown(f"<h1 style='text-align: center; font-size: 5rem; color: #FFD700;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
                time.sleep(1)
            st.balloons()
            st.success("🔔 ¡Tiempo cumplido! A por la siguiente serie.")

    # ----------------- 3. CONTROL DE NUTRICIÓN -----------------
    elif opcion == "🥗 Nutrición":
        st.markdown("# 🥗 Control de Macros Diarios")
        col1, col2, col3 = st.columns(3)
        with col1:
            prot = st.number_input("Proteínas (g)", min_value=0, value=175)
        with col2:
            carbs = st.number_input("Carbohidratos (g)", min_value=0, value=180)
        with col3:
            grasas = st.number_input("Grasas (g)", min_value=0, value=80)

        calorias = (prot * 4) + (carbs * 4) + (grasas * 9)
        st.metric("Total Calorías Diarias", f"{calorias} kcal")

        agua = st.slider("Agua (Litros)", 0.0, 5.0, 2.5, step=0.25)

        if st.button("Guardar Macros de Hoy", use_container_width=True):
            fecha_actual = str(date.today())
            c.execute("INSERT OR REPLACE INTO registro_nutricion VALUES (?, ?, ?, ?, ?, ?)",
                      (st.session_state['user'], fecha_actual, prot, carbs, grasas, agua))
            conn.commit()
            st.success("¡Macros guardados con éxito!")

    # ----------------- 4. SOBRECARGA PROGRESIVA -----------------
    elif opcion == "📈 Sobrecarga Progresiva":
        st.markdown("# 📈 Evolución de Cargas")
        df_progresos = pd.read_sql_query(f"SELECT fecha, ejercicio, peso, reps FROM registro_entrenamiento WHERE user_email='{st.session_state['user']}'", conn)

        if not df_progresos.empty:
            ejercicio_sel = st.selectbox("Selecciona un Ejercicio para analizar:", df_progresos["ejercicio"].unique())
            df_filtrado = df_progresos[df_progresos["ejercicio"] == ejercicio_sel]

            st.line_chart(df_filtrado.set_index("fecha")["peso"])
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("Aún no hay registros de fuerza en tu cuenta.")
