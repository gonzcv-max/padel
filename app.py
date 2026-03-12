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
    conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    return conn

def init_database():
    """Inicializa la base de datos creando las tablas si no existen"""
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
    
    # Tabla de historial (vista de partidos finalizados)
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

# Inicializar BD al inicio
init_database()

# ============================================
# FUNCIONES DE BASE DE DATOS
# ============================================

def cargar_jugadores():
    """Carga todos los jugadores de la BD"""
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

def guardar_jugador(nombre, nivel):
    """Guarda un nuevo jugador en la BD"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO jugadores (nombre, nivel, partidos, puntos_favor, puntos_contra, 
                                  victorias, derrotas, diferencia)
            VALUES (?, ?, 0, 0, 0, 0, 0, 0)
        ''', (nombre, nivel))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def eliminar_jugador(nombre):
    """Elimina un jugador de la BD (los partidos relacionados se borran por CASCADE)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jugadores WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()

def crear_partido(j1, j2, j3, j4, pareja1, pareja2):
    """Crea un nuevo partido en la BD"""
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

def cargar_partido(partido_id):
    """Carga un partido específico por ID"""
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

def cargar_partidos_activos():
    """Carga todos los partidos activos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, fecha, j1, j2, j3, j4, pareja1, pareja2, activo
        FROM partidos 
        WHERE activo = 1
        ORDER BY fecha DESC
    ''')
    partidos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return partidos

def cargar_todos_partidos(offset=0, limit=100, filtro=""):
    """
    Carga todos los partidos con paginación y filtro opcional
    """
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

def actualizar_partido(partido_id, j1, j2, j3, j4, pareja1, pareja2):
    """Actualiza un partido existente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE partidos 
        SET j1 = ?, j2 = ?, j3 = ?, j4 = ?, pareja1 = ?, pareja2 = ?
        WHERE id = ?
    ''', (j1, j2, j3, j4, pareja1, pareja2, partido_id))
    conn.commit()
    conn.close()

def eliminar_partido(partido_id):
    """Elimina un partido y su historial (por CASCADE)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Eliminar el partido (el historial se elimina automáticamente por CASCADE)
    cursor.execute("DELETE FROM partidos WHERE id = ?", (partido_id,))
    
    conn.commit()
    conn.close()

def eliminar_historial_completo():
    """Elimina todo el historial de partidos (solo historial, no los partidos)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Eliminar todos los registros de historial
    cursor.execute("DELETE FROM historial")
    
    conn.commit()
    conn.close()

def eliminar_historial_por_partido(partido_id):
    """Elimina el historial de un partido específico"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM historial WHERE partido_id = ?", (partido_id,))
    
    conn.commit()
    conn.close()

def finalizar_partido(partido_id, puntos_pareja1, puntos_pareja2, ganadores):
    """Finaliza un partido y actualiza estadísticas"""
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

def actualizar_estadisticas_jugador(nombre, puntos_favor, puntos_contra, es_ganador):
    """Actualiza estadísticas de un jugador"""
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

def cargar_historial(offset=0, limit=30, filtro=""):
    """
    Carga el historial de partidos con paginación
    """
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

def obtener_estadisticas_globales():
    """Obtiene estadísticas globales"""
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

# ============================================
# FUNCIONES DE PAGINACIÓN
# ============================================
def paginador(total_items, items_por_pagina, key_prefix):
    """
    Crea controles de paginación
    """
    total_paginas = (total_items - 1) // items_por_pagina + 1 if total_items > 0 else 1
    
    # Inicializar página actual si no existe
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
    
    # Selector de página
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 Jugadores", "🎯 Partidos", "📊 Clasificación", "📜 Historial", "✏️ Editar Partido", "🗑️ Borrar Partido/Historial"])

# TAB 1: Lista de jugadores
with tab1:
    jugadores = cargar_jugadores()
    
    if jugadores:
        st.subheader(f"Jugadores ({len(jugadores)})")
        
        # Mostrar jugadores en formato tabla
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
        
        # Eliminar jugador
        with st.expander("Eliminar jugador"):
            st.warning("⚠️ Al eliminar un jugador, también se borrarán todos sus partidos e historial")
            nombre = st.selectbox("Seleccionar", [j['nombre'] for j in jugadores])
            if st.button("Eliminar Jugador"):
                eliminar_jugador(nombre)
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
            
            # Selección rápida de los que menos jugaron
            if st.button("🎲 Seleccionar los que menos jugaron"):
                # Ordenar por partidos jugados (menor a mayor)
                menos_jugados = sorted(jugadores, key=lambda x: x['partidos'])
                
                # Tomar los 4 primeros (los que menos jugaron)
                seleccionados = [j['nombre'] for j in menos_jugados[:4]]
                
                # Guardar en session_state para mantener la selección
                st.session_state.seleccion_rapida = seleccionados
                st.rerun()
            
            # Selección por parejas
            st.write("**Formar parejas:**")
            
            col_p1, col_p2 = st.columns(2)
            
            # Obtener valores por defecto si existe selección rápida
            seleccion_defecto = st.session_state.get('seleccion_rapida', [])
            
            with col_p1:
                st.markdown("**Pareja 1**")
                
                # Jugador 1 de pareja 1
                default_p1_j1 = seleccion_defecto[0] if len(seleccion_defecto) > 0 and seleccion_defecto[0] in nombres else nombres[0]
                jugador1_p1 = st.selectbox("Jugador 1", nombres, index=nombres.index(default_p1_j1), key="p1_j1")
                
                # Jugador 2 de pareja 1
                opciones_j2 = [n for n in nombres if n != jugador1_p1]
                default_p1_j2 = seleccion_defecto[1] if len(seleccion_defecto) > 1 and seleccion_defecto[1] in opciones_j2 else opciones_j2[0]
                jugador2_p1 = st.selectbox("Jugador 2", opciones_j2, index=opciones_j2.index(default_p1_j2) if default_p1_j2 in opciones_j2 else 0, key="p1_j2")
            
            with col_p2:
                st.markdown("**Pareja 2**")
                jugadores_usados = [jugador1_p1, jugador2_p1]
                opciones_p2 = [n for n in nombres if n not in jugadores_usados]
                
                # Jugador 1 de pareja 2
                default_p2_j1 = seleccion_defecto[2] if len(seleccion_defecto) > 2 and seleccion_defecto[2] in opciones_p2 else opciones_p2[0]
                jugador1_p2 = st.selectbox("Jugador 3", opciones_p2, index=opciones_p2.index(default_p2_j1) if default_p2_j1 in opciones_p2 else 0, key="p2_j1")
                
                # Jugador 2 de pareja 2
                opciones_j4 = [n for n in opciones_p2 if n != jugador1_p2]
                default_p2_j2 = seleccion_defecto[3] if len(seleccion_defecto) > 3 and seleccion_defecto[3] in opciones_j4 else opciones_j4[0]
                jugador2_p2 = st.selectbox("Jugador 4", opciones_j4, index=opciones_j4.index(default_p2_j2) if default_p2_j2 in opciones_j4 else 0, key="p2_j2")
            
            if st.button("Crear Partido", type="primary"):
                pareja1 = f"{jugador1_p1} y {jugador2_p1}"
                pareja2 = f"{jugador1_p2} y {jugador2_p2}"
                
                crear_partido(jugador1_p1, jugador2_p1, jugador1_p2, jugador2_p2, pareja1, pareja2)
                
                # Limpiar selección rápida después de crear
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
                    st.write(f"🏸 {p['pareja1']}")
                    st.write(f"🏸 {p['pareja2']}")
                    
                    # Formulario para resultado
                    with st.form(key=f"resultado_{p['id']}"):
                        st.write("**Ingresa los puntos:**")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**{p['pareja1']}**")
                            puntos1 = st.number_input("Puntos", min_value=0, max_value=50, value=0, key=f"p1_{p['id']}")
                        with col_b:
                            st.write(f"**{p['pareja2']}**")
                            puntos2 = st.number_input("Puntos", min_value=0, max_value=50, value=0, key=f"p2_{p['id']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col2:
                            if st.form_submit_button("✅ Finalizar"):
                                if puntos1 != puntos2:
                                    # Determinar ganadores
                                    if puntos1 > puntos2:
                                        ganadores = f"{p['j1']} y {p['j2']}"
                                        ganadores_lista = [p['j1'], p['j2']]
                                        perdedores_lista = [p['j3'], p['j4']]
                                        puntos_ganadores = puntos1
                                        puntos_perdedores = puntos2
                                    else:
                                        ganadores = f"{p['j3']} y {p['j4']}"
                                        ganadores_lista = [p['j3'], p['j4']]
                                        perdedores_lista = [p['j1'], p['j2']]
                                        puntos_ganadores = puntos2
                                        puntos_perdedores = puntos1
                                    
                                    # Finalizar partido
                                    finalizar_partido(p['id'], puntos1, puntos2, ganadores)
                                    
                                    # Actualizar estadísticas
                                    for nombre in ganadores_lista:
                                        actualizar_estadisticas_jugador(nombre, puntos_ganadores, puntos_perdedores, True)
                                    
                                    for nombre in perdedores_lista:
                                        actualizar_estadisticas_jugador(nombre, puntos_perdedores, puntos_ganadores, False)
                                    
                                    st.success("✅ Partido finalizado!")
                                    st.rerun()
                                else:
                                    st.error("❌ Los puntos no pueden ser iguales. Somos Spartans")
                    st.divider()
        else:
            st.info("No hay partidos activos")

# TAB 3: Clasificación
with tab3:
    jugadores = cargar_jugadores()
    
    if jugadores:
        st.subheader("🏆 Clasificación General")
        
        # Opciones de ordenamiento
        orden = st.radio(
            "Ordenar por:",
            ["Puntos a favor", "Victorias", "Diferencia", "Partidos jugados"],
            horizontal=True
        )
        
        # Ordenar según selección
        if orden == "Puntos a favor":
            clasificacion = sorted(jugadores, key=lambda x: x['puntos_favor'], reverse=True)
        elif orden == "Victorias":
            clasificacion = sorted(jugadores, key=lambda x: x['victorias'], reverse=True)
        elif orden == "Diferencia":
            clasificacion = sorted(jugadores, key=lambda x: x['diferencia'], reverse=True)
        else:  # Partidos jugados
            clasificacion = sorted(jugadores, key=lambda x: x['partidos'], reverse=True)
        
        # Mostrar tabla de clasificación
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
        
        # Top 3
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
        
        # Mejor diferencia
        st.markdown("---")
        st.subheader("⭐ Mejor diferencia")
        mejor_diff = sorted(jugadores, key=lambda x: x['diferencia'], reverse=True)[0]
        st.write(f"**{mejor_diff['nombre']}** - Diferencia: +{mejor_diff['diferencia']}")
        
    else:
        st.info("No hay datos para mostrar")

# TAB 4: Historial
with tab4:
    st.subheader("📜 Historial de Partidos")
    
    # Filtro de búsqueda
    filtro_historial = st.text_input("🔍 Buscar en historial (por pareja, resultado o ganadores)", key="filtro_historial")
    
    # Configuración de paginación
    items_por_pagina = 20
    
    # Obtener historial paginado
    offset = (st.session_state.get('historial_pagina', 1) - 1) * items_por_pagina
    historial, total_historial = cargar_historial(offset, items_por_pagina, filtro_historial)
    
    if historial:
        # Mostrar total de registros
        st.write(f"**Total de partidos en historial: {total_historial}**")
        
        # Botón para limpiar todo el historial
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h2:
            with st.expander("⚠️ Limpiar todo el historial"):
                st.warning("Esta acción eliminará TODO el historial de partidos")
                st.warning("Los partidos seguirán existiendo, solo se borra el registro histórico")
                confirmar_historial = st.checkbox("Entiendo que esto no se puede deshacer")
                if confirmar_historial:
                    if st.button("🗑️ LIMPIAR HISTORIAL COMPLETO", type="primary"):
                        eliminar_historial_completo()
                        st.success("✅ Historial limpiado correctamente!")
                        st.rerun()
        
        st.markdown("---")
        
        # Paginador
        pagina_actual = paginador(total_historial, items_por_pagina, "historial")
        
        # Mostrar historial
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
        
        # Estadísticas globales
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

# TAB 5: Editar Partido
with tab5:
    st.subheader("✏️ Editar Partido")
    
    # Cargar partidos activos para editar
    partidos_activos = cargar_partidos_activos()
    
    if partidos_activos:
        # Selector de partido
        opciones_partido = [f"Partido #{p['id']} - {p['pareja1']} vs {p['pareja2']}" for p in partidos_activos]
        partido_seleccionado = st.selectbox("Selecciona el partido a editar", opciones_partido)
        
        # Obtener ID del partido seleccionado
        partido_id = int(partido_seleccionado.split('#')[1].split(' ')[0])
        partido = cargar_partido(partido_id)
        
        if partido:
            st.markdown("---")
            st.write("**Editar jugadores del partido:**")
            
            jugadores = cargar_jugadores()
            nombres = [j['nombre'] for j in jugadores]
            
            # Verificar que todos los jugadores del partido existen
            jugadores_partido = [partido['j1'], partido['j2'], partido['j3'], partido['j4']]
            jugadores_faltantes = [j for j in jugadores_partido if j not in nombres]
            
            if jugadores_faltantes:
                st.warning(f"⚠️ Los siguientes jugadores ya no existen en la base de datos: {', '.join(jugadores_faltantes)}")
                st.info("Deberás reemplazarlos por jugadores activos.")
            
            # Formulario de edición con selección por parejas
            col_edit1, col_edit2 = st.columns(2)
            
            with col_edit1:
                st.markdown("**Pareja 1 (actualizar)**")
                # Jugador 1 de pareja 1
                default_j1 = partido['j1'] if partido['j1'] in nombres else (nombres[0] if nombres else "")
                jugador1_p1_edit = st.selectbox(
                    "Jugador 1", 
                    nombres, 
                    index=nombres.index(default_j1) if default_j1 in nombres else 0,
                    key="edit_p1_j1"
                )
                
                # Jugador 2 de pareja 1
                opciones_j2 = [n for n in nombres if n != jugador1_p1_edit]
                default_j2 = partido['j2'] if partido['j2'] in opciones_j2 else (opciones_j2[0] if opciones_j2 else "")
                jugador2_p1_edit = st.selectbox(
                    "Jugador 2", 
                    opciones_j2,
                    index=opciones_j2.index(default_j2) if default_j2 in opciones_j2 else 0,
                    key="edit_p1_j2"
                )
            
            with col_edit2:
                st.markdown("**Pareja 2 (actualizar)**")
                jugadores_usados = [jugador1_p1_edit, jugador2_p1_edit]
                opciones_p2 = [n for n in nombres if n not in jugadores_usados]
                
                # Jugador 1 de pareja 2
                default_j3 = partido['j3'] if partido['j3'] in opciones_p2 else (opciones_p2[0] if opciones_p2 else "")
                jugador1_p2_edit = st.selectbox(
                    "Jugador 3", 
                    opciones_p2,
                    index=opciones_p2.index(default_j3) if default_j3 in opciones_p2 else 0,
                    key="edit_p2_j1"
                )
                
                # Jugador 2 de pareja 2
                opciones_j4 = [n for n in opciones_p2 if n != jugador1_p2_edit]
                default_j4 = partido['j4'] if partido['j4'] in opciones_j4 else (opciones_j4[0] if opciones_j4 else "")
                jugador2_p2_edit = st.selectbox(
                    "Jugador 4", 
                    opciones_j4,
                    index=opciones_j4.index(default_j4) if default_j4 in opciones_j4 else 0,
                    key="edit_p2_j2"
                )
            
            # Botón para guardar cambios
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn2:
                if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                    # Verificar que hay 4 jugadores distintos
                    jugadores_seleccionados = {jugador1_p1_edit, jugador2_p1_edit, jugador1_p2_edit, jugador2_p2_edit}
                    
                    if len(jugadores_seleccionados) == 4:
                        # Crear nombres de parejas
                        pareja1_nueva = f"{jugador1_p1_edit} y {jugador2_p1_edit}"
                        pareja2_nueva = f"{jugador1_p2_edit} y {jugador2_p2_edit}"
                        
                        # Actualizar partido
                        actualizar_partido(
                            partido_id, 
                            jugador1_p1_edit, 
                            jugador2_p1_edit, 
                            jugador1_p2_edit, 
                            jugador2_p2_edit,
                            pareja1_nueva,
                            pareja2_nueva
                        )
                        
                        st.success("✅ Partido actualizado correctamente!")
                        st.rerun()
                    else:
                        st.error("❌ Todos los jugadores deben ser diferentes")
            
            # Mostrar información del partido
            with st.expander("Ver información completa del partido"):
                st.json({
                    "ID": partido['id'],
                    "Fecha": partido['fecha'],
                    "Pareja 1 original": partido['pareja1'],
                    "Pareja 2 original": partido['pareja2'],
                    "Estado": "Activo" if partido['activo'] else "Finalizado"
                })
    
    else:
        st.info("No hay partidos activos para editar")

# TAB 6: Borrar Partido/Historial
with tab6:
    st.subheader("🗑️ Borrar Partido o Historial")
    
    # Opciones de borrado
    opcion_borrado = st.radio(
        "¿Qué quieres borrar?",
        ["Partido específico", "Historial completo", "Borrar todo (partidos e historial)"],
        horizontal=True
    )
    
    if opcion_borrado == "Partido específico":
        st.warning("⚠️ Esta acción eliminará permanentemente el partido y su historial asociado")
        
        # Filtro de búsqueda para partidos
        filtro_partido = st.text_input("🔍 Buscar partido (por ID, pareja o jugador)", key="filtro_partido")
        
        # Configuración de paginación
        items_por_pagina = 20
        
        # Obtener partidos paginados
        offset = (st.session_state.get('partidos_pagina', 1) - 1) * items_por_pagina
        todos_partidos, total_partidos = cargar_todos_partidos(offset, items_por_pagina, filtro_partido)
        
        if todos_partidos:
            # Mostrar total de partidos
            st.write(f"**Total de partidos: {total_partidos}**")
            
            # Paginador
            pagina_actual = paginador(total_partidos, items_por_pagina, "partidos")
            
            # Crear opciones con formato mejorado
            opciones_partido = []
            for p in todos_partidos:
                estado = "🟢 Activo" if p['activo'] else "🔴 Finalizado"
                fecha = p['fecha'][:16] if p['fecha'] else "Fecha desconocida"
                resultado = f" - {p['resultado']}" if p['resultado'] else ""
                opciones_partido.append(
                    f"{estado} - #{p['id']:04d} [{fecha}] - {p['pareja1']} vs {p['pareja2']}{resultado}"
                )
            
            # Selector de partido
            partido_seleccionado = st.selectbox(
                "Selecciona el partido a borrar", 
                opciones_partido,
                key="selector_partido"
            )
            
            if partido_seleccionado:
                # Extraer ID con regex mejorado
                match = re.search(r'#(\d+):?', partido_seleccionado)
                if match:
                    partido_id = int(match.group(1))
                    partido = cargar_partido(partido_id)
                    
                    if partido:
                        # Mostrar información detallada
                        st.markdown("---")
                        st.write("**Detalles del partido a borrar:**")
                        
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.write(f"📅 Fecha: {partido['fecha']}")
                            st.write(f"🏸 Pareja 1: {partido['pareja1']}")
                            st.write(f"🏸 Pareja 2: {partido['pareja2']}")
                        
                        with col_info2:
                            if partido['resultado']:
                                st.write(f"📊 Resultado: {partido['resultado']}")
                                st.write(f"🏆 Ganadores: {partido['ganadores']}")
                            st.write(f"📌 Estado: {'Activo' if partido['activo'] else 'Finalizado'}")
                        
                        st.markdown("---")
                        
                        # Confirmación de borrado
                        col_confirm1, col_confirm2, col_confirm3 = st.columns(3)
                        with col_confirm2:
                            # Checkbox de confirmación
                            confirmar = st.checkbox("Entiendo que esta acción no se puede deshacer")
                            
                            if confirmar:
                                if st.button("🗑️ BORRAR PARTIDO", type="primary", use_container_width=True):
                                    eliminar_partido(partido_id)
                                    st.success(f"✅ Partido #{partido_id} eliminado correctamente!")
                                    # Resetear página después de borrar
                                    st.session_state['partidos_pagina'] = 1
                                    st.rerun()
        else:
            if filtro_partido:
                st.info(f"No hay partidos que coincidan con '{filtro_partido}'")
            else:
                st.info("No hay partidos registrados")
    
    elif opcion_borrado == "Historial completo":
        st.warning("⚠️ Esta acción eliminará TODO el historial de partidos")
        st.info("Los partidos seguirán existiendo, solo se borra el registro histórico")
        
        historial, total_historial = cargar_historial(0, 1)  # Solo para ver el total
        
        if total_historial > 0:
            st.write(f"**Registros en historial: {total_historial}**")
            
            # Mostrar preview
            with st.expander("Ver preview del historial"):
                historial_preview, _ = cargar_historial(0, 10)
                for h in historial_preview:
                    st.write(f"- {h['fecha'][:16]}: {h['pareja1']} vs {h['pareja2']} ({h['resultado']})")
            
            # Confirmación
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h2:
                confirmar_historial = st.checkbox("Confirmo que quiero borrar TODO el historial")
                
                if confirmar_historial:
                    if st.button("🗑️ LIMPIAR HISTORIAL COMPLETO", type="primary", use_container_width=True):
                        eliminar_historial_completo()
                        st.success("✅ Historial limpiado correctamente!")
                        st.rerun()
        else:
            st.info("No hay historial para borrar")
    
    else:  # Borrar todo
        st.error("⚠️⚠️⚠️ ATENCIÓN: Esta acción eliminará TODOS los partidos y TODO el historial ⚠️⚠️⚠️")
        st.warning("La base de datos quedará vacía")
        
        todos_partidos, total_partidos = cargar_todos_partidos(0, 1000)  # Cargar todos para contar
        
        if total_partidos > 0:
            st.write(f"**Partidos a eliminar: {total_partidos}**")
            
            # Mostrar lista de partidos que se borrarán
            with st.expander("Ver preview de partidos que serán eliminados"):
                for p in todos_partidos[:20]:  # Mostrar solo los primeros 20
                    estado = "Activo" if p['activo'] else "Finalizado"
                    st.write(f"- #{p['id']}: {p['fecha'][:16]} - {p['pareja1']} vs {p['pareja2']} ({estado})")
                if total_partidos > 20:
                    st.write(f"... y {total_partidos - 20} partidos más")
            
            # Doble confirmación
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t2:
                confirmar1 = st.checkbox("Entiendo que esto borrará TODOS los partidos")
                confirmar2 = st.checkbox("Entiendo que NO se puede recuperar")
                
                if confirmar1 and confirmar2:
                    if st.button("💀 BORRAR TODO", type="primary", use_container_width=True):
                        # Borrar todos los partidos (el historial se borra por CASCADE)
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM partidos")
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ Todo ha sido eliminado correctamente!")
                        st.rerun()
        else:
            st.info("No hay partidos para borrar")