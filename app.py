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
if 'historial_partidos' not in st.session_state:
    st.session_state.historial_partidos = []

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
                    'partidos': 0,
                    'puntos_favor': 0,  # Puntos ganados
                    'puntos_contra': 0,  # Puntos recibidos
                    'victorias': 0,
                    'derrotas': 0,
                    'diferencia': 0
                })
                st.success(f"✅ {nombre} registrado!")
                st.rerun()
            else:
                st.error("Nombre inválido o ya existe")

# Pestañas
tab1, tab2, tab3, tab4 = st.tabs(["👥 Jugadores", "🎯 Partidos", "📊 Clasificación", "📜 Historial"])

# TAB 1: Lista de jugadores
with tab1:
    if st.session_state.jugadores:
        st.subheader(f"Jugadores ({len(st.session_state.jugadores)})")
        
        # Mostrar jugadores en formato tabla
        for j in st.session_state.jugadores:
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
                    'activo': True,
                    'resultado': None
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
                    
                    # Formulario para resultado
                    with st.form(key=f"resultado_{p['id']}"):
                        st.write("**Ingresa los puntos de cada juego:**")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**{p['pareja1']}**")
                            puntos_pareja1 = st.number_input("Puntos", min_value=0, max_value=50, value=0, key=f"p1_{p['id']}")
                        with col_b:
                            st.write(f"**{p['pareja2']}**")
                            puntos_pareja2 = st.number_input("Puntos", min_value=0, max_value=50, value=0, key=f"p2_{p['id']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col2:
                            if st.form_submit_button("✅ Finalizar Partido"):
                                if puntos_pareja1 != puntos_pareja2:
                                    p['activo'] = False
                                    p['resultado'] = {
                                        'pareja1': puntos_pareja1,
                                        'pareja2': puntos_pareja2
                                    }
                                    
                                    # Determinar ganadores y perdedores
                                    if puntos_pareja1 > puntos_pareja2:
                                        ganadores = [p['j1'], p['j2']]
                                        perdedores = [p['j3'], p['j4']]
                                        puntos_ganadores = puntos_pareja1
                                        puntos_perdedores = puntos_pareja2
                                    else:
                                        ganadores = [p['j3'], p['j4']]
                                        perdedores = [p['j1'], p['j2']]
                                        puntos_ganadores = puntos_pareja2
                                        puntos_perdedores = puntos_pareja1
                                    
                                    # Actualizar estadísticas
                                    for nombre in ganadores:
                                        for j in st.session_state.jugadores:
                                            if j['nombre'] == nombre:
                                                j['partidos'] += 1
                                                j['victorias'] += 1
                                                j['puntos_favor'] += puntos_ganadores
                                                j['puntos_contra'] += puntos_perdedores
                                                j['diferencia'] = j['puntos_favor'] - j['puntos_contra']
                                    
                                    for nombre in perdedores:
                                        for j in st.session_state.jugadores:
                                            if j['nombre'] == nombre:
                                                j['partidos'] += 1
                                                j['derrotas'] += 1
                                                j['puntos_favor'] += puntos_perdedores
                                                j['puntos_contra'] += puntos_ganadores
                                                j['diferencia'] = j['puntos_favor'] - j['puntos_contra']
                                    
                                    # Guardar en historial
                                    st.session_state.historial_partidos.append({
                                        'fecha': p['fecha'],
                                        'pareja1': p['pareja1'],
                                        'pareja2': p['pareja2'],
                                        'resultado': f"{puntos_pareja1} - {puntos_pareja2}",
                                        'ganadores': ' y '.join(ganadores)
                                    })
                                    
                                    st.success("✅ Partido finalizado!")
                                    st.rerun()
                                else:
                                    st.error("❌ Los puntos no pueden ser iguales")
                    st.divider()
        else:
            st.info("No hay partidos activos")

# TAB 3: Clasificación
with tab3:
    if st.session_state.jugadores:
        st.subheader("🏆 Clasificación General")
        
        # Opciones de ordenamiento
        orden = st.radio(
            "Ordenar por:",
            ["Puntos a favor", "Victorias", "Diferencia", "Partidos jugados"],
            horizontal=True
        )
        
        # Ordenar según selección
        if orden == "Puntos a favor":
            clasificacion = sorted(st.session_state.jugadores, key=lambda x: x['puntos_favor'], reverse=True)
        elif orden == "Victorias":
            clasificacion = sorted(st.session_state.jugadores, key=lambda x: x['victorias'], reverse=True)
        elif orden == "Diferencia":
            clasificacion = sorted(st.session_state.jugadores, key=lambda x: x['diferencia'], reverse=True)
        else:  # Partidos jugados
            clasificacion = sorted(st.session_state.jugadores, key=lambda x: x['partidos'], reverse=True)
        
        # Mostrar tabla de clasificación
        data = []
        for i, j in enumerate(clasificacion, 1):
            data.append({
                'Pos': i,
                'Jugador': j['nombre'],
                'Nivel': j['nivel'],
                'Puntos Favor': j['puntos_favor'],
                'Puntos Contra': j['puntos_contra'],
                'Diferencia': j['diferencia'],
                'Victorias': j['victorias'],
                'Derrotas': j['derrotas'],
                'Partidos': j['partidos']
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Top 3 destacados por puntos
        st.markdown("---")
        st.subheader("🥇 Máximos anotadores")
        top_puntos = sorted(st.session_state.jugadores, key=lambda x: x['puntos_favor'], reverse=True)[:3]
        
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
        
        # Gráfico de puntos
        st.markdown("---")
        st.subheader("📊 Puntos a favor por jugador")
        
        # Crear gráfico de barras simple
        for j in clasificacion[:10]:  # Top 10
            barra = "█" * (j['puntos_favor'] // 3)  # Escala para que no sea muy larga
            st.write(f"{j['nombre']}: {barra} ({j['puntos_favor']} pts)")
        
        # Mejor diferencia
        st.markdown("---")
        st.subheader("⭐ Mejor diferencia de puntos")
        mejor_diferencia = sorted(st.session_state.jugadores, key=lambda x: x['diferencia'], reverse=True)[0]
        st.write(f"**{mejor_diferencia['nombre']}** - Diferencia: +{mejor_diferencia['diferencia']}")
        
    else:
        st.info("No hay datos para mostrar")

# TAB 4: Historial
with tab4:
    st.subheader("📜 Historial de Partidos")
    
    if st.session_state.historial_partidos:
        # Mostrar historial en orden inverso (más reciente primero)
        for partido in reversed(st.session_state.historial_partidos[-30:]):  # Últimos 30
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 2])
                with col1:
                    st.write(f"**{partido['fecha']}**")
                with col2:
                    st.write(f"{partido['pareja1']} vs {partido['pareja2']}")
                with col3:
                    st.write(f"📊 {partido['resultado']}")
                st.write(f"🏆 Ganadores: {partido['ganadores']}")
                st.divider()
        
        # Estadísticas globales
        st.markdown("---")
        st.subheader("📈 Resumen Global")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Partidos", len(st.session_state.historial_partidos))
        with col2:
            total_puntos = sum(j['puntos_favor'] for j in st.session_state.jugadores)
            st.metric("Total Puntos", total_puntos)
        with col3:
            if st.session_state.jugadores:
                max_puntos = max(j['puntos_favor'] for j in st.session_state.jugadores)
                st.metric("Máximo Puntos", max_puntos)
    else:
        st.info("No hay partidos finalizados aún")
