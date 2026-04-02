import streamlit as st
import pandas as pd
import random
import sqlite3
from datetime import datetime
import re

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Pádel",
    page_icon="🎾",
    layout="wide"
)

# ============================================
# CONEXIÓN A BASE DE DATOS (VERSIÓN SIMPLIFICADA)
# ============================================

# Definir la ruta de la base de datos
DB_PATH = 'padel.db'

def get_db_connection():
    """Obtiene una conexión a la base de datos SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Habilitar foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        st.error(f"Error de conexión a BD: {e}")
        return None

def init_database():
    """Inicializa la base de datos creando las tablas si no existen"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Tabla de jugadores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jugadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                nivel TEXT NOT NULL,
                partidos INTEGER DEFAULT 0,
                puntos_favor INTEGER DEFAULT 0,
                puntos_contra INTEGER DEFAULT 0,
                victorias INTEGER DEFAULT 0,
                derrotas INTEGER DEFAULT 0,
                diferencia INTEGER DEFAULT 0,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de partidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS partidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                j1 TEXT NOT NULL,
                j2 TEXT NOT NULL,
                j3 TEXT NOT NULL,
                j4 TEXT NOT NULL,
                pareja1 TEXT NOT NULL,
                pareja2 TEXT NOT NULL,
                activo BOOLEAN DEFAULT 1,
                puntos_pareja1 INTEGER DEFAULT 0,
                puntos_pareja2 INTEGER DEFAULT 0,
                ganadores TEXT,
                resultado TEXT
            )
        ''')
        
        # Tabla de historial
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partido_id INTEGER,
                fecha TEXT,
                pareja1 TEXT,
                pareja2 TEXT,
                resultado TEXT,
                ganadores TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error inicializando BD: {e}")
        return False

# Inicializar BD
if not init_database():
    st.error("No se pudo inicializar la base de datos")

# ============================================
# FUNCIONES DE BASE DE DATOS
# ============================================

def cargar_jugadores():
    """Carga todos los jugadores de la BD"""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nombre, nivel, partidos, puntos_favor, puntos_contra, 
                   victorias, derrotas, diferencia 
            FROM jugadores 
            ORDER BY puntos_favor DESC
        ''')
        jugadores = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jugadores
    except Exception as e:
        st.error(f"Error cargando jugadores: {e}")
        conn.close()
        return []

def guardar_jugador(nombre, nivel):
    """Guarda un nuevo jugador en la BD"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO jugadores (nombre, nivel, partidos, puntos_favor, puntos_contra, 
                                  victorias, derrotas, diferencia)
            VALUES (?, ?, 0, 0, 0, 0, 0, 0)
        ''', (nombre, nivel))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False
    except Exception as e:
        st.error(f"Error guardando jugador: {e}")
        conn.close()
        return False

def eliminar_jugador(nombre):
    """Elimina un jugador de la BD"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jugadores WHERE nombre = ?", (nombre,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error eliminando jugador: {e}")
        conn.close()
        return False

def crear_partido(j1, j2, j3, j4, pareja1, pareja2):
    """Crea un nuevo partido en la BD"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO partidos (j1, j2, j3, j4, pareja1, pareja2, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (j1, j2, j3, j4, pareja1, pareja2))
        partido_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return partido_id
    except Exception as e:
        st.error(f"Error creando partido: {e}")
        conn.close()
        return None

def cargar_partido(partido_id):
    """Carga un partido específico por ID"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo,
                   puntos_pareja1, puntos_pareja2, ganadores, resultado
            FROM partidos 
            WHERE id = ?
        ''', (partido_id,))
        partido = cursor.fetchone()
        conn.close()
        return dict(partido) if partido else None
    except Exception as e:
        st.error(f"Error cargando partido: {e}")
        conn.close()
        return None

def cargar_partidos_activos():
    """Carga todos los partidos activos"""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo,
                   puntos_pareja1, puntos_pareja2
            FROM partidos 
            WHERE activo = 1
            ORDER BY fecha DESC
        ''')
        partidos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return partidos
    except Exception as e:
        st.error(f"Error cargando partidos activos: {e}")
        conn.close()
        return []

def actualizar_puntaje(partido_id, puntos_pareja1, puntos_pareja2):
    """Actualiza los puntos en la BD"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE partidos 
            SET puntos_pareja1 = ?, puntos_pareja2 = ?
            WHERE id = ?
        ''', (puntos_pareja1, puntos_pareja2, partido_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando puntaje: {e}")
        conn.close()
        return False

def finalizar_partido(partido_id, puntos_pareja1, puntos_pareja2, ganadores):
    """Finaliza un partido y actualiza estadísticas"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Obtener datos del partido
        cursor.execute('SELECT * FROM partidos WHERE id = ?', (partido_id,))
        partido = dict(cursor.fetchone())
        
        # Actualizar partido
        resultado = f"{puntos_pareja1} - {puntos_pareja2}"
        cursor.execute('''
            UPDATE partidos 
            SET activo = 0, puntos_pareja1 = ?, puntos_pareja2 = ?, 
                ganadores = ?, resultado = ?
            WHERE id = ?
        ''', (puntos_pareja1, puntos_pareja2, ganadores, resultado, partido_id))
        
        # Guardar en historial
        cursor.execute('''
            INSERT INTO historial (partido_id, fecha, pareja1, pareja2, resultado, ganadores)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (partido_id, partido['fecha'], partido['pareja1'], partido['pareja2'], resultado, ganadores))
        
        # Actualizar estadísticas de jugadores
        if puntos_pareja1 > puntos_pareja2:
            ganadores_lista = [partido['j1'], partido['j2']]
            perdedores_lista = [partido['j3'], partido['j4']]
            puntos_ganadores = puntos_pareja1
            puntos_perdedores = puntos_pareja2
        else:
            ganadores_lista = [partido['j3'], partido['j4']]
            perdedores_lista = [partido['j1'], partido['j2']]
            puntos_ganadores = puntos_pareja2
            puntos_perdedores = puntos_pareja1
        
        for nombre in ganadores_lista:
            actualizar_estadisticas_jugador(nombre, puntos_ganadores, puntos_perdedores, True)
        
        for nombre in perdedores_lista:
            actualizar_estadisticas_jugador(nombre, puntos_perdedores, puntos_ganadores, False)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error finalizando partido: {e}")
        conn.close()
        return False

def actualizar_estadisticas_jugador(nombre, puntos_favor, puntos_contra, es_ganador):
    """Actualiza estadísticas de un jugador"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        if es_ganador:
            cursor.execute('''
                UPDATE jugadores 
                SET partidos = partidos + 1,
                    victorias = victorias + 1,
                    puntos_favor = puntos_favor + ?,
                    puntos_contra = puntos_contra + ?,
                    diferencia = (puntos_favor + ?) - (puntos_contra + ?)
                WHERE nombre = ?
            ''', (puntos_favor, puntos_contra, puntos_favor, puntos_contra, nombre))
        else:
            cursor.execute('''
                UPDATE jugadores 
                SET partidos = partidos + 1,
                    derrotas = derrotas + 1,
                    puntos_favor = puntos_favor + ?,
                    puntos_contra = puntos_contra + ?,
                    diferencia = (puntos_favor + ?) - (puntos_contra + ?)
                WHERE nombre = ?
            ''', (puntos_favor, puntos_contra, puntos_favor, puntos_contra, nombre))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando estadísticas: {e}")
        conn.close()
        return False

# ============================================
# FUNCIONES PARA PUNTUACIÓN DE PÁDEL
# ============================================

def convertir_puntos_tenis(puntos):
    """Convierte puntos numéricos a notación de tenis/pádel"""
    if puntos == 0:
        return "0"
    elif puntos == 1:
        return "15"
    elif puntos == 2:
        return "30"
    elif puntos == 3:
        return "40"
    else:
        return "Juego"

def calcular_estado_punto(puntos1, puntos2):
    """Calcula el estado actual del punto en notación de tenis"""
    if puntos1 >= 4 and puntos1 - puntos2 >= 2:
        return "game_won_1"
    elif puntos2 >= 4 and puntos2 - puntos1 >= 2:
        return "game_won_2"
    
    if puntos1 >= 3 and puntos2 >= 3 and puntos1 == puntos2:
        return "deuce"
    
    if puntos1 >= 3 and puntos2 >= 3:
        if puntos1 > puntos2:
            return "advantage_1"
        elif puntos2 > puntos1:
            return "advantage_2"
    
    return "normal"

# ============================================
# INTERFAZ DE USUARIO
# ============================================

st.title("🎾 Partidos de Señoras")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📝 Nuevo Jugador")
    
    with st.form("alta_jugador", clear_on_submit=True):
        nombre = st.text_input("Nombre")
        nivel = st.selectbox("Nivel", ["Panda", "Manco", "Muy Muy"])
        
        if st.form_submit_button("Registrar"):
            if nombre:
                if guardar_jugador(nombre, nivel):
                    st.success(f"✅ {nombre} registrado!")
                    st.rerun()
                else:
                    st.error("❌ El nombre ya existe")
    
    st.markdown("---")
    st.caption("💾 Los datos se guardan automáticamente")

# Pestañas
tab1, tab2, tab3 = st.tabs(["👥 Jugadores", "🎯 Partidos", "🏆 Puntuación"])

# TAB 1: Jugadores
with tab1:
    jugadores = cargar_jugadores()
    
    if jugadores:
        st.subheader(f"Jugadores ({len(jugadores)})")
        
        for j in jugadores:
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1, 1, 1, 1])
            with col1:
                st.write(f"**{j['nombre']}**")
            with col2:
                st.write(f"Nivel: {j['nivel']}")
            with col3:
                st.write(f"🎾 {j['partidos']}")
            with col4:
                st.write(f"✅ {j['victorias']}")
            with col5:
                st.write(f"❌ {j['derrotas']}")
            with col6:
                st.write(f"⚡ {j['puntos_favor']}-{j['puntos_contra']}")
        
        with st.expander("Eliminar jugador"):
            st.warning("⚠️ Al eliminar un jugador, también se borrarán todos sus partidos")
            nombre = st.selectbox("Seleccionar", [j['nombre'] for j in jugadores])
            if st.button("Eliminar Jugador"):
                if eliminar_jugador(nombre):
                    st.success(f"✅ Jugador {nombre} eliminado")
                    st.rerun()
    else:
        st.info("No hay jugadores. Agrega desde el menú lateral.")

# TAB 2: Partidos
with tab2:
    col1, col2 = st.columns(2)
    jugadores = cargar_jugadores()
    
    with col1:
        st.subheader("Nuevo Partido")
        
        if len(jugadores) >= 4:
            nombres = [j['nombre'] for j in jugadores]
            
            # Selección por parejas
            st.write("**Formar parejas:**")
            
            col_p1, col_p2 = st.columns(2)
            
            with col_p1:
                st.markdown("**Pareja 1**")
                jugador1_p1 = st.selectbox("Jugador 1", nombres, key="p1_j1")
                opciones_j2 = [n for n in nombres if n != jugador1_p1]
                jugador2_p1 = st.selectbox("Jugador 2", opciones_j2, key="p1_j2")
            
            with col_p2:
                st.markdown("**Pareja 2**")
                jugadores_usados = [jugador1_p1, jugador2_p1]
                opciones_p2 = [n for n in nombres if n not in jugadores_usados]
                jugador1_p2 = st.selectbox("Jugador 3", opciones_p2, key="p2_j1")
                opciones_j4 = [n for n in opciones_p2 if n != jugador1_p2]
                jugador2_p2 = st.selectbox("Jugador 4", opciones_j4, key="p2_j2")
            
            if st.button("Crear Partido", type="primary"):
                pareja1 = f"{jugador1_p1} y {jugador2_p1}"
                pareja2 = f"{jugador1_p2} y {jugador2_p2}"
                partido_id = crear_partido(jugador1_p1, jugador2_p1, jugador1_p2, jugador2_p2, pareja1, pareja2)
                if partido_id:
                    st.success("✅ Partido creado correctamente!")
                    st.rerun()
        else:
            st.warning(f"Necesitas 4 jugadores (tienes {len(jugadores)})")
    
    with col2:
        st.subheader("Partidos Activos")
        activos = cargar_partidos_activos()
        
        if activos:
            for p in activos:
                with st.container():
                    st.write(f"**Partido #{p['id']}**")
                    st.write(f"🏸 {p['pareja1']} vs {p['pareja2']}")
                    if p['puntos_pareja1'] is not None:
                        st.write(f"📊 Puntaje actual: {p['puntos_pareja1']} - {p['puntos_pareja2']}")
                    st.divider()
        else:
            st.info("No hay partidos activos")

# TAB 3: Puntuación
with tab3:
    st.header("🏆 Puntuación de Partidos - Sistema 15-30-40")
    st.markdown("---")
    
    partidos_activos = cargar_partidos_activos()
    
    if partidos_activos:
        opciones_partido = []
        for p in partidos_activos:
            puntos1 = p['puntos_pareja1'] if p['puntos_pareja1'] is not None else 0
            puntos2 = p['puntos_pareja2'] if p['puntos_pareja2'] is not None else 0
            puntaje_tenis1 = convertir_puntos_tenis(puntos1)
            puntaje_tenis2 = convertir_puntos_tenis(puntos2)
            opciones_partido.append(f"#{p['id']} - {p['pareja1']} vs {p['pareja2']} [{puntaje_tenis1}-{puntaje_tenis2}]")
        
        partido_seleccionado = st.selectbox("Selecciona el partido", opciones_partido, key="puntaje_partido")
        
        match = re.search(r'#(\d+)', partido_seleccionado)
        if match:
            partido_id = int(match.group(1))
            partido = cargar_partido(partido_id)
            
            if partido:
                puntos_actuales1 = partido['puntos_pareja1'] if partido['puntos_pareja1'] is not None else 0
                puntos_actuales2 = partido['puntos_pareja2'] if partido['puntos_pareja2'] is not None else 0
                
                st.markdown("---")
                
                # Mostrar parejas
                col1, col2, col3 = st.columns([2, 1, 2])
                
                with col1:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                        <h3>🏸 {partido['pareja1']}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<h2 style='text-align: center; padding-top: 30px;'>VS</h2>", unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                        <h3>🏸 {partido['pareja2']}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Mostrar marcador
                puntaje_tenis1 = convertir_puntos_tenis(puntos_actuales1)
                puntaje_tenis2 = convertir_puntos_tenis(puntos_actuales2)
                estado = calcular_estado_punto(puntos_actuales1, puntos_actuales2)
                
                st.markdown(f"""
                <div style="text-align: center; margin: 30px 0;">
                    <div style="display: inline-block; background-color: #2c3e50; color: white; padding: 20px 40px; border-radius: 20px;">
                        <span style="font-size: 48px; font-weight: bold;">{puntaje_tenis1}</span>
                        <span style="font-size: 36px; margin: 0 20px;">-</span>
                        <span style="font-size: 48px; font-weight: bold;">{puntaje_tenis2}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Mostrar estado especial
                if estado == "deuce":
                    st.info("🏐 ¡DEUCE! Se necesita ventaja de 2 puntos")
                elif estado == "advantage_1":
                    st.success(f"🎾 VENTAJA para {partido['pareja1']}")
                elif estado == "advantage_2":
                    st.success(f"🎾 VENTAJA para {partido['pareja2']}")
                elif estado in ["game_won_1", "game_won_2"]:
                    st.balloons()
                    ganador = partido['pareja1'] if estado == "game_won_1" else partido['pareja2']
                    st.success(f"🏆 ¡{ganador} ha ganado el JUEGO! 🏆")
                
                st.markdown("---")
                
                # Botones de control
                if estado not in ["game_won_1", "game_won_2"]:
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button(f"🏸 +1 PUNTO - {partido['pareja1']}", use_container_width=True, type="primary"):
                            if actualizar_puntaje(partido_id, puntos_actuales1 + 1, puntos_actuales2):
                                st.rerun()
                    
                    with col_btn2:
                        if st.button(f"🏸 +1 PUNTO - {partido['pareja2']}", use_container_width=True, type="primary"):
                            if actualizar_puntaje(partido_id, puntos_actuales1, puntos_actuales2 + 1):
                                st.rerun()
                    
                    # Botones secundarios
                    col_reset1, col_reset2, col_reset3 = st.columns(3)
                    with col_reset2:
                        if st.button("🔄 REINICIAR MARCADOR", use_container_width=True):
                            if actualizar_puntaje(partido_id, 0, 0):
                                st.rerun()
                
                else:
                    # Botón para finalizar partido
                    if st.button("✅ FINALIZAR PARTIDO", type="primary", use_container_width=True):
                        ganador = partido['pareja1'] if puntos_actuales1 > puntos_actuales2 else partido['pareja2']
                        if finalizar_partido(partido_id, puntos_actuales1, puntos_actuales2, ganador):
                            st.success(f"✅ Partido finalizado! Ganó {ganador}")
                            st.rerun()
    else:
        st.info("No hay partidos activos. Crea un partido primero en la pestaña 'Partidos'")
