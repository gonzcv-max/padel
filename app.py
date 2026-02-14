import streamlit as st
import pandas as pd
import random
import sqlite3
from datetime import datetime
import json
import os

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
            FOREIGN KEY (j1) REFERENCES jugadores(nombre),
            FOREIGN KEY (j2) REFERENCES jugadores(nombre),
            FOREIGN KEY (j3) REFERENCES jugadores(nombre),
            FOREIGN KEY (j4) REFERENCES jugadores(nombre)
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
            FOREIGN KEY (partido_id) REFERENCES partidos(id)
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
    """Elimina un jugador de la BD"""
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

def cargar_historial(limite=30):
    """Carga el historial de partidos"""
    conn = get_db_connection()
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
# INTERFAZ DE USUARIO
# ============================================

# Título
st.title("🎾 Gestión de Partidos de Pádel")
st.markdown("---")

# Sidebar para dar de alta jugadores
with st.sidebar:
    st.header("📝 Nuevo Jugador")
    
    with st.form("alta_jugador", clear_on_submit=True):
        nombre = st.text_input("Nombre")
        nivel = st.selectbox("Nivel", ["Principiante", "Intermedio", "Avanzado"])
        
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
tab1, tab2, tab3, tab4 = st.tabs(["👥 Jugadores", "🎯 Partidos", "📊 Clasificación", "📜 Historial"])

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
            nombre = st.selectbox("Seleccionar", [j['nombre'] for j in jugadores])
            if st.button("Eliminar"):
                eliminar_jugador(nombre)
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
                menos_jugados = sorted(jugadores, key=lambda x: x['partidos'])[:4]
                st.session_state.seleccion = [j['nombre'] for j in menos_jugados]
                st.rerun()
            
            # Selección manual
            st.write("Selecciona 4 jugadores:")
            seleccion = []
            for i in range(4):
                opciones = [n for n in nombres if n not in seleccion]
                if opciones:
                    default = None
                    if 'seleccion' in st.session_state and i < len(st.session_state.seleccion):
                        default = st.session_state.seleccion[i] if st.session_state.seleccion[i] in opciones else opciones[0]
                    jugador = st.selectbox(f"Jugador {i+1}", opciones, key=f"j{i}", index=opciones.index(default) if default in opciones else 0)
                    seleccion.append(jugador)
            
            if st.button("Crear Partido", type="primary"):
                # Mezclar para formar parejas
                random.shuffle(seleccion)
                pareja1 = f"{seleccion[0]} y {seleccion[1]}"
                pareja2 = f"{seleccion[2]} y {seleccion[3]}"
                
                crear_partido(seleccion[0], seleccion[1], seleccion[2], seleccion[3], pareja1, pareja2)
                
                if 'seleccion' in st.session_state:
                    del st.session_state.seleccion
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
                                    st.error("❌ Los puntos no pueden ser iguales")
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
        st.info("No hay partidos finalizados aún")
