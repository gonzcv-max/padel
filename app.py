import streamlit as st
import pandas as pd
import random
import sqlite3
from datetime import datetime
import json
import os
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
def get_db_connection():
    """Obtiene una conexión a la base de datos SQLite"""
    conn = sqlite3.connect('padel.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa la base de datos creando las tablas si no existen"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Habilitar foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
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
                puntos_pareja1 INTEGER,
                puntos_pareja2 INTEGER,
                ganadores TEXT,
                resultado TEXT,
                FOREIGN KEY (j1) REFERENCES jugadores(nombre) ON DELETE CASCADE,
                FOREIGN KEY (j2) REFERENCES jugadores(nombre) ON DELETE CASCADE,
                FOREIGN KEY (j3) REFERENCES jugadores(nombre) ON DELETE CASCADE,
                FOREIGN KEY (j4) REFERENCES jugadores(nombre) ON DELETE CASCADE
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
                ganadores TEXT,
                FOREIGN KEY (partido_id) REFERENCES partidos(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error inicializando la base de datos: {e}")
        return False

# Inicializar BD
if not init_database():
    st.error("No se pudo inicializar la base de datos")

# ============================================
# FUNCIONES DE BASE DE DATOS
# ============================================

def cargar_jugadores():
    """Carga todos los jugadores de la BD"""
    try:
        conn = get_db_connection()
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
        return []

def guardar_jugador(nombre, nivel):
    """Guarda un nuevo jugador en la BD"""
    try:
        conn = get_db_connection()
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
        return False
    except Exception as e:
        st.error(f"Error guardando jugador: {e}")
        return False

def eliminar_jugador(nombre):
    """Elimina un jugador de la BD"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jugadores WHERE nombre = ?", (nombre,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error eliminando jugador: {e}")
        return False

def crear_partido(j1, j2, j3, j4, pareja1, pareja2):
    """Crea un nuevo partido en la BD"""
    try:
        conn = get_db_connection()
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
        return None

def cargar_partido(partido_id):
    """Carga un partido específico por ID"""
    try:
        conn = get_db_connection()
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
        return None

def cargar_partidos_activos():
    """Carga todos los partidos activos"""
    try:
        conn = get_db_connection()
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
        return []

def cargar_todos_partidos(offset=0, limit=100, filtro=""):
    """Carga todos los partidos con paginación y filtro opcional"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo,
                   puntos_pareja1, puntos_pareja2, ganadores, resultado
            FROM partidos 
        '''
        
        params = []
        
        if filtro:
            query += ''' WHERE id LIKE ? OR pareja1 LIKE ? OR pareja2 LIKE ? OR 
                        j1 LIKE ? OR j2 LIKE ? OR j3 LIKE ? OR j4 LIKE ?
                     '''
            filtro_param = f'%{filtro}%'
            params = [filtro_param] * 7
        
        query += " ORDER BY fecha DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        partidos = [dict(row) for row in cursor.fetchall()]
        
        # Obtener total de partidos para paginación
        cursor.execute("SELECT COUNT(*) as total FROM partidos")
        total = cursor.fetchone()['total']
        
        conn.close()
        return partidos, total
    except Exception as e:
        st.error(f"Error cargando todos los partidos: {e}")
        return [], 0

def actualizar_partido(partido_id, j1, j2, j3, j4, pareja1, pareja2):
    """Actualiza un partido existente"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE partidos 
            SET j1 = ?, j2 = ?, j3 = ?, j4 = ?, pareja1 = ?, pareja2 = ?
            WHERE id = ?
        ''', (j1, j2, j3, j4, pareja1, pareja2, partido_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando partido: {e}")
        return False

def eliminar_partido(partido_id):
    """Elimina un partido y su historial (por CASCADE)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM partidos WHERE id = ?", (partido_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error eliminando partido: {e}")
        return False

def eliminar_historial_completo():
    """Elimina todo el historial de partidos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM historial")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error limpiando historial: {e}")
        return False

def actualizar_puntaje_tenis(partido_id, puntos_pareja1, puntos_pareja2):
    """Actualiza los puntos en la BD"""
    try:
        conn = get_db_connection()
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
        return False

def finalizar_partido(partido_id, puntos_pareja1, puntos_pareja2, ganadores):
    """Finaliza un partido y actualiza estadísticas"""
    try:
        conn = get_db_connection()
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
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error finalizando partido: {e}")
        return False

def finalizar_partido_tenis(partido_id, puntos_pareja1, puntos_pareja2, ganadores, ganadores_lista, perdedores_lista):
    """Finaliza el partido y actualiza estadísticas con sistema tenis"""
    try:
        conn = get_db_connection()
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
        st.error(f"Error finalizando partido tenis: {e}")
        return False

def actualizar_estadisticas_jugador(nombre, puntos_favor, puntos_contra, es_ganador):
    """Actualiza estadísticas de un jugador"""
    try:
        conn = get_db_connection()
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
        return False

def cargar_historial(offset=0, limit=30, filtro=""):
    """Carga el historial de partidos con paginación"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT fecha, pareja1, pareja2, resultado, ganadores
            FROM historial 
        '''
        
        params = []
        
        if filtro:
            query += ''' WHERE pareja1 LIKE ? OR pareja2 LIKE ? OR ganadores LIKE ? 
                        OR resultado LIKE ?
                     '''
            filtro_param = f'%{filtro}%'
            params = [filtro_param] * 4
        
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        historial = [dict(row) for row in cursor.fetchall()]
        
        # Obtener total para paginación
        cursor.execute("SELECT COUNT(*) as total FROM historial")
        total = cursor.fetchone()['total']
        
        conn.close()
        return historial, total
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        return [], 0

def obtener_estadisticas_globales():
    """Obtiene estadísticas globales"""
    try:
        conn = get_db_connection()
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
        return 0, 0, 0

# ============================================
# FUNCIONES PARA PUNTUACIÓN DE PÁDEL (15-30-40-JUEGO)
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
    # Si alguien ya ganó
    if puntos1 >= 4 and puntos1 - puntos2 >= 2:
        return "game_won_1"
    elif puntos2 >= 4 and puntos2 - puntos1 >= 2:
        return "game_won_2"
    
    # Deuce (40-40)
    if puntos1 >= 3 and puntos2 >= 3 and puntos1 == puntos2:
        return "deuce"
    
    # Ventaja
    if puntos1 >= 3 and puntos2 >= 3:
        if puntos1 > puntos2:
            return "advantage_1"
        elif puntos2 > puntos1:
            return "advantage_2"
    
    return "normal"

# ============================================
# FUNCIONES DE PAGINACIÓN
# ============================================

def paginador(total_items, items_por_pagina, key_prefix):
    """Crea controles de paginación"""
    total_paginas = (total_items - 1) // items_por_pagina + 1 if total_items > 0 else 1
    
    if f'{key_prefix}_pagina' not in st.session_state:
        st.session_state[f'{key_prefix}_pagina'] = 1
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ Primera", key=f"{key_prefix}_first"):
            st.session_state[f'{key_prefix}_pagina'] = 1
            st.rerun()
    
    with col2:
        if st.button("◀️ Anterior", key=f"{key_prefix}_prev"):
            if st.session_state[f'{key_prefix}_pagina'] > 1:
                st.session_state[f'{key_prefix}_pagina'] -= 1
                st.rerun()
    
    with col3:
        st.write(f"Página {st.session_state[f'{key_prefix}_pagina']} de {total_paginas}")
    
    with col4:
        if st.button("Siguiente ▶️", key=f"{key_prefix}_next"):
            if st.session_state[f'{key_prefix}_pagina'] < total_paginas:
                st.session_state[f'{key_prefix}_pagina'] += 1
                st.rerun()
    
    with col5:
        if st.button("⏭️ Última", key=f"{key_prefix}_last"):
            st.session_state[f'{key_prefix}_pagina'] = total_paginas
            st.rerun()
    
    if total_paginas > 1:
        pagina = st.number_input(
            "Ir a página", 
            min_value=1, 
            max_value=total_paginas, 
            value=st.session_state[f'{key_prefix}_pagina'],
            key=f"{key_prefix}_goto"
        )
        if pagina != st.session_state[f'{key_prefix}_pagina']:
            st.session_state[f'{key_prefix}_pagina'] = pagina
            st.rerun()
    
    return st.session_state[f'{key_prefix}_pagina']

# ============================================
# INTERFAZ DE USUARIO
# ============================================

# Título
st.title("🎾 Partidos de Señoras")
st.markdown("---")

# Sidebar para dar de alta jugadores
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
    st.caption("💾 Los datos se guardan automáticamente en la base de datos")

# Pestañas
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "👥 Jugadores", "🎯 Partidos", "🏆 Puntuación", "📊 Clasificación", 
    "📜 Historial", "✏️ Editar Partido", "🗑️ Borrar"
])

# TAB 1: Lista de jugadores
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
            st.warning("⚠️ Al eliminar un jugador, también se borrarán todos sus partidos e historial")
            nombre = st.selectbox("Seleccionar", [j['nombre'] for j in jugadores])
            if st.button("Eliminar Jugador"):
                if eliminar_jugador(nombre):
                    st.success(f"✅ Jugador {nombre} eliminado")
                    st.rerun()
    else:
        st.info("No hay jugadores. Agrega desde el menú lateral.")

# TAB 2: Crear partidos
with tab2:
    col1, col2 = st.columns(2)
    jugadores = cargar_jugadores()
    
    with col1:
        st.subheader("Nuevo Partido")
        
        if len(jugadores) >= 4:
            nombres = [j['nombre'] for j in jugadores]
            
            if st.button("🎲 Seleccionar los que menos jugaron"):
                menos_jugados = sorted(jugadores, key=lambda x: x['partidos'])
                seleccionados = [j['nombre'] for j in menos_jugados[:4]]
                st.session_state.seleccion_rapida = seleccionados
                st.rerun()
            
            st.write("**Formar parejas:**")
            
            col_p1, col_p2 = st.columns(2)
            seleccion_defecto = st.session_state.get('seleccion_rapida', [])
            
            with col_p1:
                st.markdown("**Pareja 1**")
                default_p1_j1 = seleccion_defecto[0] if len(seleccion_defecto) > 0 and seleccion_defecto[0] in nombres else nombres[0]
                jugador1_p1 = st.selectbox("Jugador 1", nombres, index=nombres.index(default_p1_j1), key="p1_j1")
                
                opciones_j2 = [n for n in nombres if n != jugador1_p1]
                default_p1_j2 = seleccion_defecto[1] if len(seleccion_defecto) > 1 and seleccion_defecto[1] in opciones_j2 else opciones_j2[0]
                jugador2_p1 = st.selectbox("Jugador 2", opciones_j2, index=opciones_j2.index(default_p1_j2) if default_p1_j2 in opciones_j2 else 0, key="p1_j2")
            
            with col_p2:
                st.markdown("**Pareja 2**")
                jugadores_usados = [jugador1_p1, jugador2_p1]
                opciones_p2 = [n for n in nombres if n not in jugadores_usados]
                
                default_p2_j1 = seleccion_defecto[2] if len(seleccion_defecto) > 2 and seleccion_defecto[2] in opciones_p2 else opciones_p2[0]
                jugador1_p2 = st.selectbox("Jugador 3", opciones_p2, index=opciones_p2.index(default_p2_j1) if default_p2_j1 in opciones_p2 else 0, key="p2_j1")
                
                opciones_j4 = [n for n in opciones_p2 if n != jugador1_p2]
                default_p2_j2 = seleccion_defecto[3] if len(seleccion_defecto) > 3 and seleccion_defecto[3] in opciones_j4 else opciones_j4[0]
                jugador2_p2 = st.selectbox("Jugador 4", opciones_j4, index=opciones_j4.index(default_p2_j2) if default_p2_j2 in opciones_j4 else 0, key="p2_j2")
            
            if st.button("Crear Partido", type="primary"):
                pareja1 = f"{jugador1_p1} y {jugador2_p1}"
                pareja2 = f"{jugador1_p2} y {jugador2_p2}"
                partido_id = crear_partido(jugador1_p1, jugador2_p1, jugador1_p2, jugador2_p2, pareja1, pareja2)
                if partido_id:
                    if 'seleccion_rapida' in st.session_state:
                        del st.session_state.seleccion_rapida
                    st.success("✅ Partido creado correctamente!")
                    st.rerun()
        else:
            st.warning(f"Necesitas 4 jugadores (tienes {len(jugadores)}) ponte pilas!!!")
    
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

# TAB 3: Puntuación con sistema 15-30-40-JUEGO
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
                
                if estado == "deuce":
                    st.info("🏐 ¡DEUCE! Se necesita ventaja de 2 puntos")
                elif estado == "advantage_1":
                    st.success(f"🎾 VENTAJA para {partido['pareja1']}")
                elif estado == "advantage_2":
                    st.success(f"🎾 VENTAJA para {partido['pareja2']}")
                elif estado == "game_won_1":
                    st.balloons()
                    st.success(f"🏆 ¡{partido['pareja1']} ha ganado el JUEGO! 🏆")
                elif estado == "game_won_2":
                    st.balloons()
                    st.success(f"🏆 ¡{partido['pareja2']} ha ganado el JUEGO! 🏆")
                
                st.markdown("---")
                
                if estado in ["game_won_1", "game_won_2"]:
                    st.warning("⚠️ Este juego ya ha terminado. Debes finalizar el partido o crear uno nuevo.")
                    
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f2:
                        if st.button("✅ FINALIZAR PARTIDO", type="primary", use_container_width=True):
                            if puntos_actuales1 > puntos_actuales2:
                                ganadores = partido['pareja1']
                                ganadores_lista = [partido['j1'], partido['j2']]
                                perdedores_lista = [partido['j3'], partido['j4']]
                            else:
                                ganadores = partido['pareja2']
                                ganadores_lista = [partido['j3'], partido['j4']]
                                perdedores_lista = [partido['j1'], partido['j2']]
                            
                            if finalizar_partido_tenis(partido_id, puntos_actuales1, puntos_actuales2, 
                                                      ganadores, ganadores_lista, perdedores_lista):
                                st.success(f"✅ Partido finalizado! Ganó {ganadores}")
                                st.rerun()
                else:
                    st.subheader("➕ Sumar punto")
                    
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                    
                    with col_btn1:
                        if st.button(f"🏸 +1 PUNTO\n{partido['pareja1']}", use_container_width=True, type="primary"):
                            if actualizar_puntaje_tenis(partido_id, puntos_actuales1 + 1, puntos_actuales2):
                                st.rerun()
                    
                    with col_btn2:
                        if st.button(f"🏸 +1 PUNTO\n{partido['pareja2']}", use_container_width=True, type="primary"):
                            if actualizar_puntaje_tenis(partido_id, puntos_actuales1, puntos_actuales2 + 1):
                                st.rerun()
                    
                    with col_btn3:
                        if st.button("➖ RESTAR\n1 punto", use_container_width=True):
                            if puntos_actuales1 > 0 or puntos_actuales2 > 0:
                                st.session_state['mostrar_restar_tenis'] = True
                            else:
                                st.warning("No hay puntos para restar")
                    
                    with col_btn4:
                        if st.button("🔄 REINICIAR\nmarcador", use_container_width=True):
                            st.session_state['mostrar_reiniciar_tenis'] = True
                    
                    if st.session_state.get('mostrar_restar_tenis', False):
                        st.markdown("---")
                        st.subheader("➖ Restar punto")
                        col_r1, col_r2, col_r3 = st.columns(3)
                        
                        with col_r1:
                            if st.button(f"➖ Restar a\n{partido['pareja1']}", use_container_width=True):
                                if puntos_actuales1 > 0:
                                    if actualizar_puntaje_tenis(partido_id, puntos_actuales1 - 1, puntos_actuales2):
                                        st.session_state['mostrar_restar_tenis'] = False
                                        st.rerun()
                                else:
                                    st.error("No se puede restar más puntos")
                        
                        with col_r2:
                            if st.button(f"➖ Restar a\n{partido['pareja2']}", use_container_width=True):
                                if puntos_actuales2 > 0:
                                    if actualizar_puntaje_tenis(partido_id, puntos_actuales1, puntos_actuales2 - 1):
                                        st.session_state['mostrar_restar_tenis'] = False
                                        st.rerun()
                                else:
                                    st.error("No se puede restar más puntos")
                        
                        with col_r3:
                            if st.button("❌ Cancelar", use_container_width=True):
                                st.session_state['mostrar_restar_tenis'] = False
                                st.rerun()
                    
                    if st.session_state.get('mostrar_reiniciar_tenis', False):
                        st.markdown("---")
                        st.warning("⚠️ ¿Estás segura de que quieres reiniciar el marcador a 0-0?")
                        col_rec1, col_rec2, col_rec3 = st.columns(3)
                        
                        with col_rec2:
                            col_rr1, col_rr2 = st.columns(2)
                            with col_rr1:
                                if st.button("✅ Sí, reiniciar", use_container_width=True):
                                    if actualizar_puntaje_tenis(partido_id, 0, 0):
                                        st.session_state['mostrar_reiniciar_tenis'] = False
                                        st.rerun()
                            with col_rr2:
                                if st.button("❌ No, cancelar", use_container_width=True):
                                    st.session_state['mostrar_reiniciar_tenis'] = False
                                    st.rerun()
                    
                    with st.expander("ℹ️ ¿Cómo funciona la puntuación?"):
                        st.markdown("""
                        **Sistema de puntuación del pádel/tenis:**
                        - 1er punto = **15**
                        - 2do punto = **30**  
                        - 3er punto = **40**
                        - 4to punto = **JUEGO** (si hay ventaja de 2 puntos)
                        
                        **Reglas especiales:**
                        - **DEUCE**: Cuando ambos llegan a 40-40
                        - **VENTAJA**: Se necesita 1 punto después del Deuce para ganar
                        - **JUEGO**: Se gana con ventaja de 2 puntos
                        """)
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
    
    filtro_historial = st.text_input("🔍 Buscar en historial", key="filtro_historial")
    items_por_pagina = 20
    
    offset = (st.session_state.get('historial_pagina', 1) - 1) * items_por_pagina
    historial, total_historial = cargar_historial(offset, items_por_pagina, filtro_historial)
    
    if historial:
        st.write(f"**Total de partidos en historial: {total_historial}**")
        
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h2:
            with st.expander("⚠️ Limpiar todo el historial"):
                st.warning("Esta acción eliminará TODO el historial de partidos")
                if st.button("🗑️ LIMPIAR HISTORIAL COMPLETO", type="primary"):
                    if eliminar_historial_completo():
                        st.success("✅ Historial limpiado correctamente!")
                        st.rerun()
        
        st.markdown("---")
        pagina_actual = paginador(total_historial, items_por_pagina, "historial")
        
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
        if filtro_historial:
            st.info(f"No hay resultados para '{filtro_historial}'")
        else:
            st.info("No hay partidos finalizados aún")

# TAB 6: Editar Partido
with tab6:
    st.subheader("✏️ Editar Partido")
    
    partidos_activos = cargar_partidos_activos()
    
    if partidos_activos:
        opciones_partido = [f"Partido #{p['id']} - {p['pareja1']} vs {p['pareja2']}" for p in partidos_activos]
        partido_seleccionado = st.selectbox("Selecciona el partido a editar", opciones_partido)
        
        partido_id = int(partido_seleccionado.split('#')[1].split(' ')[0])
        partido = cargar_partido(partido_id)
        
        if partido:
            st.markdown("---")
            st.write("**Editar jugadores del partido:**")
            
            jugadores = cargar_jugadores()
            nombres = [j['nombre'] for j in jugadores]
            
            col_edit1, col_edit2 = st.columns(2)
            
            with col_edit1:
                st.markdown("**Pareja 1**")
                default_j1 = partido['j1'] if partido['j1'] in nombres else nombres[0]
                jugador1_p1 = st.selectbox("Jugador 1", nombres, index=nombres.index(default_j1), key="edit1")
                
                opciones_j2 = [n for n in nombres if n != jugador1_p1]
                default_j2 = partido['j2'] if partido['j2'] in opciones_j2 else opciones_j2[0]
                jugador2_p1 = st.selectbox("Jugador 2", opciones_j2, index=opciones_j2.index(default_j2), key="edit2")
            
            with col_edit2:
                st.markdown("**Pareja 2**")
                usados = [jugador1_p1, jugador2_p1]
                opciones_p2 = [n for n in nombres if n not in usados]
                default_j3 = partido['j3'] if partido['j3'] in opciones_p2 else opciones_p2[0]
                jugador1_p2 = st.selectbox("Jugador 3", opciones_p2, index=opciones_p2.index(default_j3), key="edit3")
                
                opciones_j4 = [n for n in opciones_p2 if n != jugador1_p2]
                default_j4 = partido['j4'] if partido['j4'] in opciones_j4 else opciones_j4[0]
                jugador2_p2 = st.selectbox("Jugador 4", opciones_j4, index=opciones_j4.index(default_j4), key="edit4")
            
            if st.button("💾 Guardar Cambios", type="primary"):
                pareja1 = f"{jugador1_p1} y {jugador2_p1}"
                pareja2 = f"{jugador1_p2} y {jugador2_p2}"
                if actualizar_partido(partido_id, jugador1_p1, jugador2_p1, jugador1_p2, jugador2_p2, pareja1, pareja2):
                    st.success("✅ Partido actualizado!")
                    st.rerun()
    else:
        st.info("No hay partidos activos para editar")

# TAB 7: Borrar
with tab7:
    st.subheader("🗑️ Borrar Partido")
    
    filtro_partido = st.text_input("🔍 Buscar partido", key="filtro_borrar")
    items_por_pagina = 20
    
    offset = (st.session_state.get('borrar_pagina', 1) - 1) * items_por_pagina
    todos_partidos, total_partidos = cargar_todos_partidos(offset, items_por_pagina, filtro_partido)
    
    if todos_partidos:
        st.write(f"**Total: {total_partidos} partidos**")
        
        pagina_actual = paginador(total_partidos, items_por_pagina, "borrar")
        
        opciones_partido = []
        for p in todos_partidos:
            estado = "🟢" if p['activo'] else "🔴"
            fecha = p['fecha'][:16] if p['fecha'] else "Sin fecha"
            resultado = f" - {p['resultado']}" if p['resultado'] else ""
            opciones_partido.append(f"{estado} #{p['id']:04d} [{fecha}] - {p['pareja1']} vs {p['pareja2']}{resultado}")
        
        partido_borrar = st.selectbox("Selecciona el partido a borrar", opciones_partido)
        
        match = re.search(r'#(\d+):?', partido_borrar)
        if match:
            partido_id = int(match.group(1))
            partido = cargar_partido(partido_id)
            
            if partido:
                st.markdown("---")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"📅 Fecha: {partido['fecha']}")
                    st.write(f"🏸 Pareja 1: {partido['pareja1']}")
                with col_info2:
                    if partido['resultado']:
                        st.write(f"📊 Resultado: {partido['resultado']}")
                    st.write(f"📌 Estado: {'Activo' if partido['activo'] else 'Finalizado'}")
                
                st.markdown("---")
                
                col_borrar1, col_borrar2, col_borrar3 = st.columns(3)
                with col_borrar2:
                    confirmar = st.checkbox("Confirmar eliminación permanente")
                    if confirmar:
                        if st.button("🗑️ BORRAR PARTIDO", type="primary"):
                            if eliminar_partido(partido_id):
                                st.success(f"✅ Partido #{partido_id} eliminado!")
                                st.rerun()
    else:
        if filtro_partido:
            st.info(f"No hay partidos que coincidan con '{filtro_partido}'")
        else:
            st.info("No hay partidos registrados")
