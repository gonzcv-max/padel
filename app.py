import streamlit as st
import pandas as pd
import random
from datetime import datetime
import json

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Pádel",
    page_icon="🎾",
    layout="wide"
)

# Inicializar el estado de la sesión
if 'jugadores' not in st.session_state:
    st.session_state.jugadores = []
if 'partidos' not in st.session_state:
    st.session_state.partidos = []
if 'contador_id' not in st.session_state:
    st.session_state.contador_id = 1

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
            if nombre and nombre not in [j['nombre'] for j in st.session_state.jugadores]:
                st.session_state.jugadores.append({
                    'nombre': nombre,
                    'nivel': nivel,
                    'partidos': 0
                })
                st.success(f"✅ {nombre} registrado!")
                st.rerun()
            else:
                st.error("Nombre inválido o ya existe")

# Pestañas
tab1, tab2, tab3 = st.tabs(["👥 Jugadores", "🎯 Partidos", "📊 Estadísticas"])

# TAB 1: Lista de jugadores
with tab1:
    if st.session_state.jugadores:
        st.subheader(f"Jugadores ({len(st.session_state.jugadores)})")
        
        for j in st.session_state.jugadores:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{j['nombre']}**")
            with col2:
                st.write(f"Nivel: {j['nivel']}")
            with col3:
                st.write(f"🎾 {j['partidos']}")
        
        # Eliminar jugador
        with st.expander("Eliminar jugador"):
            nombre = st.selectbox("Seleccionar", [j['nombre'] for j in st.session_state.jugadores])
            if st.button("Eliminar"):
                st.session_state.jugadores = [j for j in st.session_state.jugadores if j['nombre'] != nombre]
                st.rerun()
    else:
        st.info("No hay jugadores. Agrega desde el menú lateral.")

# TAB 2: Crear partidos
with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Nuevo Partido")
        
        if len(st.session_state.jugadores) >= 4:
            nombres = [j['nombre'] for j in st.session_state.jugadores]
            
            # Selección rápida de los que menos jugaron
            if st.button("🎲 Seleccionar los que menos jugaron"):
                menos_jugados = sorted(st.session_state.jugadores, key=lambda x: x['partidos'])[:4]
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
                partido = {
                    'id': st.session_state.contador_id,
                    'fecha': datetime.now().strftime("%d/%m %H:%M"),
                    'j1': seleccion[0],
                    'j2': seleccion[1],
                    'j3': seleccion[2],
                    'j4': seleccion[3],
                    'pareja1': f"{seleccion[0]} y {seleccion[1]}",
                    'pareja2': f"{seleccion[2]} y {seleccion[3]}",
                    'activo': True
                }
                st.session_state.partidos.append(partido)
                st.session_state.contador_id += 1
                if 'seleccion' in st.session_state:
                    del st.session_state.seleccion
                st.rerun()
        else:
            st.warning(f"Necesitas 4 jugadores (tienes {len(st.session_state.jugadores)})")
    
    with col2:
        st.subheader("Partidos Activos")
        activos = [p for p in st.session_state.partidos if p['activo']]
        
        if activos:
            for p in activos:
                with st.container():
                    st.write(f"**Partido #{p['id']}** - {p['fecha']}")
                    st.write(f"🏸 {p['pareja1']}")
                    st.write(f"🏸 {p['pareja2']}")
                    
                    if st.button(f"✅ Finalizar #{p['id']}"):
                        p['activo'] = False
                        # Sumar partidos a los jugadores
                        for nombre in [p['j1'], p['j2'], p['j3'], p['j4']]:
                            for j in st.session_state.jugadores:
                                if j['nombre'] == nombre:
                                    j['partidos'] += 1
                        st.rerun()
                    st.divider()
        else:
            st.info("No hay partidos activos")

# TAB 3: Estadísticas
with tab3:
    if st.session_state.jugadores:
        st.subheader("Partidos por jugador")
        
        # Ordenar por partidos jugados
        ranking = sorted(st.session_state.jugadores, key=lambda x: x['partidos'], reverse=True)
        
        # Mostrar ranking
        for i, j in enumerate(ranking, 1):
            barra = "█" * j['partidos']
            st.write(f"{i}. **{j['nombre']}**: {barra} ({j['partidos']} partidos)")
        
        # Totales
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Jugadores", len(st.session_state.jugadores))
        with col2:
            total = sum(j['partidos'] for j in st.session_state.jugadores)
            st.metric("Total Partidos", total//4 if total>0 else 0)
        with col3:
            if st.session_state.jugadores:
                prom = sum(j['partidos'] for j in st.session_state.jugadores) / len(st.session_state.jugadores)
                st.metric("Promedio", round(prom, 1))
        
        # Recomendación
        st.markdown("---")
        st.subheader("Próximos a jugar")
        menos_jugados = sorted(st.session_state.jugadores, key=lambda x: x['partidos'])[:4]
        st.write("Estos son los que menos han jugado:")
        for j in menos_jugados:
            st.write(f"- {j['nombre']} ({j['partidos']} partidos)")
    else:
        st.info("No hay datos para mostrar")
