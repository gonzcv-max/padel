import streamlit as st
import pandas as pd
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
# CONEXIÓN A BASE DE DATOS
# ============================================

DB_PATH = 'padel.db'

def get_db_connection():
    """Obtiene una conexión a la base de datos SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
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
                puntos_set1 INTEGER DEFAULT 0,
                puntos_set2 INTEGER DEFAULT 0,
                modo_muerte BOOLEAN DEFAULT 0,
                ganadores TEXT,
                resultado TEXT
            )
        ''')
        
        # Verificar y agregar columnas faltantes
        cursor.execute("PRAGMA table_info(partidos)")
        columnas = [columna[1] for columna in cursor.fetchall()]
        
        if 'puntos_set1' not in columnas:
            cursor.execute("ALTER TABLE partidos ADD COLUMN puntos_set1 INTEGER DEFAULT 0")
        
        if 'puntos_set2' not in columnas:
            cursor.execute("ALTER TABLE partidos ADD COLUMN puntos_set2 INTEGER DEFAULT 0")
        
        if 'modo_muerte' not in columnas:
            cursor.execute("ALTER TABLE partidos ADD COLUMN modo_muerte BOOLEAN DEFAULT 0")
        
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

init_database()

# ============================================
# FUNCIONES DE BASE DE DATOS
# ============================================

def cargar_jugadores():
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
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO partidos (j1, j2, j3, j4, pareja1, pareja2, activo, puntos_set1, puntos_set2, modo_muerte)
            VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, 0)
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
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo,
                   puntos_pareja1, puntos_pareja2, puntos_set1, puntos_set2, 
                   modo_muerte, ganadores, resultado
            FROM partidos 
            WHERE id = ?
        ''', (partido_id,))
        partido = cursor.fetchone()
        conn.close()
        if partido:
            return dict(partido)
        return None
    except Exception as e:
        st.error(f"Error cargando partido: {e}")
        conn.close()
        return None

def cargar_partidos_activos():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo,
                   puntos_pareja1, puntos_pareja2, puntos_set1, puntos_set2, modo_muerte
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

def cargar_todos_partidos():
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo,
                   puntos_pareja1, puntos_pareja2, resultado, ganadores
            FROM partidos 
            ORDER BY fecha DESC
        ''')
        partidos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return partidos
    except Exception as e:
        st.error(f"Error cargando todos los partidos: {e}")
        conn.close()
        return []

def eliminar_partido(partido_id):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM historial WHERE partido_id = ?", (partido_id,))
        cursor.execute("DELETE FROM partidos WHERE id = ?", (partido_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error eliminando partido: {e}")
        conn.close()
        return False

def actualizar_puntos_set(partido_id, puntos_set1, puntos_set2):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE partidos 
            SET puntos_set1 = ?, puntos_set2 = ?
            WHERE id = ?
        ''', (puntos_set1, puntos_set2, partido_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando puntos: {e}")
        conn.close()
        return False

def actualizar_modo_muerte(partido_id, modo_muerte):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE partidos 
            SET modo_muerte = ?
            WHERE id = ?
        ''', (modo_muerte, partido_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando modo muerte: {e}")
        conn.close()
        return False

def actualizar_puntos_partido(partido_id, puntos_pareja1, puntos_pareja2):
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
        st.error(f"Error actualizando puntos: {e}")
        conn.close()
        return False

def finalizar_partido(partido_id, puntos_pareja1, puntos_pareja2, ganadores):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM partidos WHERE id = ?', (partido_id,))
        partido = dict(cursor.fetchone())
        
        resultado = f"{puntos_pareja1} - {puntos_pareja2}"
        cursor.execute('''
            UPDATE partidos 
            SET activo = 0, puntos_pareja1 = ?, puntos_pareja2 = ?, 
                ganadores = ?, resultado = ?
            WHERE id = ?
        ''', (puntos_pareja1, puntos_pareja2, ganadores, resultado, partido_id))
        
        cursor.execute('''
            INSERT INTO historial (partido_id, fecha, pareja1, pareja2, resultado, ganadores)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (partido_id, partido['fecha'], partido['pareja1'], partido['pareja2'], resultado, ganadores))
        
        if puntos_pareja1 > puntos_pareja2:
            ganadores_lista = [partido['j1'], partido['j2']]
            perdedores_lista = [partido['j3'], partido['j4']]
        else:
            ganadores_lista = [partido['j3'], partido['j4']]
            perdedores_lista = [partido['j1'], partido['j2']]
        
        for nombre in ganadores_lista:
            actualizar_estadisticas_jugador(nombre, puntos_pareja1 if puntos_pareja1 > puntos_pareja2 else puntos_pareja2, 
                                          puntos_pareja2 if puntos_pareja1 > puntos_pareja2 else puntos_pareja1, True)
        
        for nombre in perdedores_lista:
            actualizar_estadisticas_jugador(nombre, puntos_pareja2 if puntos_pareja1 > puntos_pareja2 else puntos_pareja1,
                                          puntos_pareja1 if puntos_pareja1 > puntos_pareja2 else puntos_pareja2, False)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error finalizando partido: {e}")
        conn.close()
        return False

def actualizar_estadisticas_jugador(nombre, puntos_favor, puntos_contra, es_ganador):
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

def cargar_historial(limite=50):
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha, pareja1, pareja2, resultado, ganadores
            FROM historial 
            ORDER BY id DESC 
            LIMIT ?
        ''', (limite,))
        historial = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return historial
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        conn.close()
        return []

def obtener_estadisticas_globales():
    conn = get_db_connection()
    if conn is None:
        return 0, 0, 0
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as total FROM partidos WHERE activo = 0')
        total_partidos = cursor.fetchone()['total']
        cursor.execute('SELECT SUM(puntos_favor) as total FROM jugadores')
        total_puntos = cursor.fetchone()['total'] or 0
        cursor.execute('SELECT MAX(puntos_favor) as max FROM jugadores')
        max_puntos = cursor.fetchone()['max'] or 0
        conn.close()
        return total_partidos, total_puntos, max_puntos
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {e}")
        conn.close()
        return 0, 0, 0

# ============================================
# FUNCIONES PARA PUNTUACIÓN
# ============================================

def convertir_puntos_tenis(puntos):
    if puntos == 0:
        return "0"
    elif puntos == 1:
        return "15"
    elif puntos == 2:
        return "30"
    elif puntos == 3:
        return "40"
    else:
        return "Ventaja"

def procesar_punto(puntos1, puntos2, ganador, modo_muerte=False):
    """Procesa un punto según las reglas del pádel"""
    if ganador == 1:
        puntos1 += 1
    else:
        puntos2 += 1
    
    # Si está en modo muerte súbita, el primer punto después de 40-40 gana
    if modo_muerte and (puntos1 >= 3 or puntos2 >= 3):
        if puntos1 > puntos2 and puntos1 >= 3:
            return 0, 0, True, 1
        elif puntos2 > puntos1 and puntos2 >= 3:
            return 0, 0, True, 2
    
    # Si alguien llegó a 40 y tiene ventaja de 2, gana el juego
    if puntos1 >= 4 and puntos1 - puntos2 >= 2:
        return 0, 0, True, 1
    elif puntos2 >= 4 and puntos2 - puntos1 >= 2:
        return 0, 0, True, 2
    
    return puntos1, puntos2, False, 0

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👥 Jugadores", "🎯 Partidos", "🏆 Puntuación", "📊 Clasificación", "📜 Historial", "🗑️ Borrar Partido"
])

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
                    if p.get('puntos_pareja1') is not None:
                        st.write(f"📊 Marcador: {p.get('puntos_pareja1', 0)} - {p.get('puntos_pareja2', 0)}")
                    st.divider()
        else:
            st.info("No hay partidos activos")

# TAB 3: Puntuación
with tab3:
    st.header("🏆 Puntuación de Partidos")
    st.markdown("---")
    
    partidos_activos = cargar_partidos_activos()
    
    if partidos_activos:
        opciones_partido = []
        for p in partidos_activos:
            opciones_partido.append(f"#{p['id']} - {p['pareja1']} vs {p['pareja2']}")
        
        partido_seleccionado = st.selectbox("Selecciona el partido", opciones_partido, key="puntaje_partido")
        
        match = re.search(r'#(\d+)', partido_seleccionado)
        if match:
            partido_id = int(match.group(1))
            partido = cargar_partido(partido_id)
            
            if partido:
                puntos_set1 = partido.get('puntos_set1', 0) or 0
                puntos_set2 = partido.get('puntos_set2', 0) or 0
                puntos_partido1 = partido.get('puntos_pareja1', 0) or 0
                puntos_partido2 = partido.get('puntos_pareja2', 0) or 0
                modo_muerte = partido.get('modo_muerte', 0) or 0
                
                st.markdown("---")
                
                col1, col2, col3 = st.columns([2, 1, 2])
                
                with col1:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                        <h3>🏸 {partido['pareja1']}</h3>
                        <h1 style="font-size: 48px;">{puntos_partido1}</h1>
                        <p style="font-size: 32px;">[{convertir_puntos_tenis(puntos_set1)}]</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<h2 style='text-align: center; padding-top: 60px;'>VS</h2>", unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                        <h3>🏸 {partido['pareja2']}</h3>
                        <h1 style="font-size: 48px;">{puntos_partido2}</h1>
                        <p style="font-size: 32px;">[{convertir_puntos_tenis(puntos_set2)}]</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Mostrar modo actual si está en Deuce
                if puntos_set1 == 3 and puntos_set2 == 3:
                    if modo_muerte:
                        st.info("💀 Modo MUERTE SÚBITA activado - ¡El próximo punto gana el juego!")
                    else:
                        st.info("🏐 DEUCE (40-40) - Elige modo de juego:")
                        
                        col_deuce1, col_deuce2 = st.columns(2)
                        with col_deuce1:
                            if st.button("🏸 SUBE - Jugar a ventaja (2 puntos)", use_container_width=True, type="primary"):
                                # Modo normal con ventaja
                                actualizar_modo_muerte(partido_id, 0)
                                st.rerun()
                        
                        with col_deuce2:
                            if st.button("💀 MUERE - Muerte súbita (1 punto)", use_container_width=True, type="primary"):
                                # Modo muerte súbita
                                actualizar_modo_muerte(partido_id, 1)
                                st.rerun()
                
                # Mostrar estado de ventaja si está en modo sube
                elif puntos_set1 > 3 or puntos_set2 > 3:
                    if puntos_set1 > puntos_set2:
                        st.success(f"🎾 VENTAJA para {partido['pareja1']} - ¡Necesita otro punto para ganar!")
                    else:
                        st.success(f"🎾 VENTAJA para {partido['pareja2']} - ¡Necesita otro punto para ganar!")
                
                modo_rapido = st.checkbox("⚡ Modo rápido (ingresar puntos directamente)")
                
                if modo_rapido:
                    st.subheader("Ingresar puntos del partido directamente")
                    col_r1, col_r2 = st.columns(2)
                    
                    with col_r1:
                        puntos_directos1 = st.number_input(f"Puntos {partido['pareja1']}", min_value=0, value=puntos_partido1, key="directo1")
                    with col_r2:
                        puntos_directos2 = st.number_input(f"Puntos {partido['pareja2']}", min_value=0, value=puntos_partido2, key="directo2")
                    
                    if st.button("💾 Guardar puntos", type="primary"):
                        if actualizar_puntos_partido(partido_id, puntos_directos1, puntos_directos2):
                            st.success("✅ Puntos guardados!")
                            st.rerun()
                
                else:
                    st.subheader("Puntuación del juego actual (15-30-40)")
                    
                    # Verificar si alguien ganó el juego
                    juego_terminado = False
                    ganador_juego = None
                    
                    if puntos_set1 >= 4 and puntos_set1 - puntos_set2 >= 2:
                        juego_terminado = True
                        ganador_juego = 1
                    elif puntos_set2 >= 4 and puntos_set2 - puntos_set1 >= 2:
                        juego_terminado = True
                        ganador_juego = 2
                    elif modo_muerte and (puntos_set1 == 4 or puntos_set2 == 4):
                        juego_terminado = True
                        ganador_juego = 1 if puntos_set1 > puntos_set2 else 2
                    
                    if juego_terminado:
                        ganador_nombre = partido['pareja1'] if ganador_juego == 1 else partido['pareja2']
                        st.success(f"🎉 ¡{ganador_nombre} ganó el juego!")
                        col_g1, col_g2 = st.columns(2)
                        with col_g1:
                            if st.button("✅ Sumar punto al marcador", use_container_width=True, type="primary"):
                                if ganador_juego == 1:
                                    actualizar_puntos_partido(partido_id, puntos_partido1 + 1, puntos_partido2)
                                else:
                                    actualizar_puntos_partido(partido_id, puntos_partido1, puntos_partido2 + 1)
                                actualizar_puntos_set(partido_id, 0, 0)
                                actualizar_modo_muerte(partido_id, 0)
                                st.rerun()
                        with col_g2:
                            if st.button("🔄 Continuar sin sumar", use_container_width=True):
                                actualizar_puntos_set(partido_id, 0, 0)
                                actualizar_modo_muerte(partido_id, 0)
                                st.rerun()
                    else:
                        # Botones para sumar puntos
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button(f"🏸 +1 PUNTO - {partido['pareja1']}", use_container_width=True, type="primary"):
                                nuevos_set1, nuevos_set2, juego_ganado, ganador = procesar_punto(
                                    puntos_set1, puntos_set2, 1, modo_muerte
                                )
                                actualizar_puntos_set(partido_id, nuevos_set1, nuevos_set2)
                                if juego_ganado and ganador == 1:
                                    actualizar_puntos_partido(partido_id, puntos_partido1 + 1, puntos_partido2)
                                    actualizar_puntos_set(partido_id, 0, 0)
                                    actualizar_modo_muerte(partido_id, 0)
                                    st.success(f"🎉 ¡Juego ganado!")
                                st.rerun()
                        
                        with col_btn2:
                            if st.button(f"🏸 +1 PUNTO - {partido['pareja2']}", use_container_width=True, type="primary"):
                                nuevos_set1, nuevos_set2, juego_ganado, ganador = procesar_punto(
                                    puntos_set1, puntos_set2, 2, modo_muerte
                                )
                                actualizar_puntos_set(partido_id, nuevos_set1, nuevos_set2)
                                if juego_ganado and ganador == 2:
                                    actualizar_puntos_partido(partido_id, puntos_partido1, puntos_partido2 + 1)
                                    actualizar_puntos_set(partido_id, 0, 0)
                                    actualizar_modo_muerte(partido_id, 0)
                                    st.success(f"🎉 ¡Juego ganado!")
                                st.rerun()
                
                st.markdown("---")
                
                st.subheader("🏁 Finalizar Partido")
                if puntos_partido1 > 0 or puntos_partido2 > 0:
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f2:
                        if st.button("✅ FINALIZAR PARTIDO", type="primary", use_container_width=True):
                            if puntos_partido1 != puntos_partido2:
                                ganador = partido['pareja1'] if puntos_partido1 > puntos_partido2 else partido['pareja2']
                                if finalizar_partido(partido_id, puntos_partido1, puntos_partido2, ganador):
                                    st.success(f"✅ Partido finalizado! Ganó {ganador}")
                                    st.balloons()
                                    st.rerun()
                            else:
                                st.error("❌ No puede haber empate. Debe haber un ganador")
                else:
                    st.info("No se puede finalizar el partido sin puntos")
    else:
        st.info("No hay partidos activos. Crea un partido primero en la pestaña 'Partidos'")

# TAB 4: Clasificación
with tab4:
    jugadores = cargar_jugadores()
    
    if jugadores:
        st.subheader("🏆 Clasificación General")
        
        orden = st.radio(
            "Ordenar por:",
            ["Puntos a favor", "Victorias", "Diferencia", "Partidos jugados"],
            horizontal=True
        )
        
        if orden == "Puntos a favor":
            clasificacion = sorted(jugadores, key=lambda x: x['puntos_favor'], reverse=True)
        elif orden == "Victorias":
            clasificacion = sorted(jugadores, key=lambda x: x['victorias'], reverse=True)
        elif orden == "Diferencia":
            clasificacion = sorted(jugadores, key=lambda x: x['diferencia'], reverse=True)
        else:
            clasificacion = sorted(jugadores, key=lambda x: x['partidos'], reverse=True)
        
        data = []
        for i, j in enumerate(clasificacion, 1):
            data.append({
                'Pos': i,
                'Jugador': j['nombre'],
                'Nivel': j['nivel'],
                'Pts Favor': j['puntos_favor'],
                'Pts Contra': j['puntos_contra'],
                'Dif': j['diferencia'],
                'V': j['victorias'],
                'D': j['derrotas'],
                'PJ': j['partidos']
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🥇 Máximos anotadores")
        top_puntos = sorted(jugadores, key=lambda x: x['puntos_favor'], reverse=True)[:3]
        
        col1, col2, col3 = st.columns(3)
        if len(top_puntos) >= 1:
            with col1:
                st.metric("🥇 1º", top_puntos[0]['nombre'], f"{top_puntos[0]['puntos_favor']} pts")
        if len(top_puntos) >= 2:
            with col2:
                st.metric("🥈 2º", top_puntos[1]['nombre'], f"{top_puntos[1]['puntos_favor']} pts")
        if len(top_puntos) >= 3:
            with col3:
                st.metric("🥉 3º", top_puntos[2]['nombre'], f"{top_puntos[2]['puntos_favor']} pts")
        
        st.markdown("---")
        st.subheader("⭐ Mejor diferencia")
        mejor_diff = sorted(jugadores, key=lambda x: x['diferencia'], reverse=True)[0]
        st.write(f"**{mejor_diff['nombre']}** - Diferencia: +{mejor_diff['diferencia']}")
        
    else:
        st.info("No hay datos para mostrar")

# TAB 5: Historial
with tab5:
    st.subheader("📜 Historial de Partidos")
    
    historial = cargar_historial()
    
    if historial:
        for partido in historial:
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 2])
                with col1:
                    st.write(f"**{partido['fecha'][:16]}**")
                with col2:
                    st.write(f"{partido['pareja1']} vs {partido['pareja2']}")
                with col3:
                    st.write(f"📊 {partido['resultado']}")
                st.write(f"🏆 Ganadores: {partido['ganadores']}")
                st.divider()
        
        st.markdown("---")
        st.subheader("📈 Resumen Global")
        
        total_partidos, total_puntos, max_puntos = obtener_estadisticas_globales()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Partidos", total_partidos)
        with col2:
            st.metric("Total Puntos", total_puntos)
        with col3:
            st.metric("Máximo Puntos", max_puntos)
    else:
        st.info("No hay partidos finalizados aún")

# TAB 6: Borrar Partido
with tab6:
    st.header("🗑️ Borrar Partido")
    st.warning("⚠️ Esta acción eliminará permanentemente el partido y no se puede deshacer")
    st.markdown("---")
    
    todos_partidos = cargar_todos_partidos()
    
    if todos_partidos:
        opciones_partido = []
        for p in todos_partidos:
            estado = "🟢 Activo" if p['activo'] == 1 else "🔴 Finalizado"
            fecha = p['fecha'][:16] if p['fecha'] else "Fecha desconocida"
            resultado = f" - {p['resultado']}" if p['resultado'] else ""
            opciones_partido.append(f"{estado} - #{p['id']} [{fecha}] - {p['pareja1']} vs {p['pareja2']}{resultado}")
        
        partido_seleccionado = st.selectbox(
            "Selecciona el partido que quieres eliminar",
            opciones_partido,
            key="borrar_partido_select"
        )
        
        if partido_seleccionado:
            match = re.search(r'#(\d+)', partido_seleccionado)
            if match:
                partido_id = int(match.group(1))
                partido = cargar_partido(partido_id)
                
                if partido:
                    st.markdown("---")
                    st.subheader("📋 Detalles del partido a eliminar:")
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.write(f"**ID:** #{partido['id']}")
                        st.write(f"**Fecha:** {partido['fecha']}")
                        st.write(f"**Pareja 1:** {partido['pareja1']}")
                        st.write(f"**Pareja 2:** {partido['pareja2']}")
                    with col_d2:
                        st.write(f"**Estado:** {'🟢 Activo' if partido['activo'] == 1 else '🔴 Finalizado'}")
                        if partido['resultado']:
                            st.write(f"**Resultado:** {partido['resultado']}")
                        if partido['ganadores']:
                            st.write(f"**Ganadores:** {partido['ganadores']}")
                    
                    st.markdown("---")
                    st.error("⚠️ ¡ATENCIÓN! Esta acción es irreversible")
                    
                    confirmar_texto = st.text_input("Escribe 'ELIMINAR' para confirmar:", key="confirmar_eliminar")
                    
                    if confirmar_texto == "ELIMINAR":
                        if st.button("🗑️ SÍ, ELIMINAR PARTIDO PERMANENTEMENTE", type="primary", use_container_width=True):
                            if eliminar_partido(partido_id):
                                st.success(f"✅ Partido #{partido_id} eliminado correctamente!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Error al eliminar el partido")
                    elif confirmar_texto:
                        st.info("Escribe 'ELIMINAR' para habilitar el botón de eliminación")
    else:
        st.info("No hay partidos registrados para eliminar")
