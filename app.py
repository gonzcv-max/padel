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
if 'historial' not in st.session_state:
    st.session_state.historial = {}

# Título principal
st.title("🎾 Gestión de Partidos de Pádel")
st.markdown("---")

# Sidebar para dar de alta jugadores
with st.sidebar:
    st.header("📝 Dar de alta jugador")
    
    with st.form("alta_jugador"):
        nombre = st.text_input("Nombre del jugador")
        col1, col2 = st.columns(2)
        with col1:
            nivel = st.selectbox("Nivel", ["Principiante", "Intermedio", "Avanzado"])
        with col2:
            sexo = st.selectbox("Sexo", ["Masculino", "Femenino", "Otro"])
        
        submitted = st.form_submit_button("Registrar jugador")
        
        if submitted and nombre:
            if nombre not in [j['nombre'] for j in st.session_state.jugadores]:
                nuevo_jugador = {
                    'id': len(st.session_state.jugadores) + 1,
                    'nombre': nombre,
                    'nivel': nivel,
                    'sexo': sexo,
                    'fecha_registro': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'partidos_jugados': 0
                }
                st.session_state.jugadores.append(nuevo_jugador)
                st.success(f"✅ {nombre} registrado correctamente!")
            else:
                st.error("❌ Este jugador ya existe")

# Área principal en pestañas
tab1, tab2, tab3, tab4 = st.tabs(["👥 Jugadores", "🎯 Crear Partidos", "📊 Estadísticas", "⚙️ Configuración"])

# Pestaña 1: Lista de jugadores
with tab1:
    st.header("Jugadores registrados")
    
    if st.session_state.jugadores:
        # Mostrar jugadores en una tabla
        df_jugadores = pd.DataFrame(st.session_state.jugadores)
        st.dataframe(
            df_jugadores[['nombre', 'nivel', 'sexo', 'partidos_jugados']],
            use_container_width=True,
            hide_index=True
        )
        
        # Opción para eliminar jugadores
        with st.expander("Eliminar jugador"):
            jugador_a_eliminar = st.selectbox(
                "Seleccionar jugador",
                options=[j['nombre'] for j in st.session_state.jugadores]
            )
            if st.button("Eliminar jugador", type="primary"):
                st.session_state.jugadores = [
                    j for j in st.session_state.jugadores 
                    if j['nombre'] != jugador_a_eliminar
                ]
                st.rerun()
    else:
        st.info("No hay jugadores registrados. Agrega jugadores desde el menú lateral.")

# Pestaña 2: Crear partidos
with tab2:
    st.header("Crear nuevo partido")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Jugadores disponibles")
        if st.session_state.jugadores:
            # Selección de jugadores para el partido
            nombres_jugadores = [j['nombre'] for j in st.session_state.jugadores]
            
            if len(nombres_jugadores) >= 4:
                # Selección manual
                st.write("Selecciona los 4 jugadores:")
                jugador1 = st.selectbox("Jugador 1", nombres_jugadores, key="j1")
                jugador2 = st.selectbox("Jugador 2", [j for j in nombres_jugadores if j != jugador1], key="j2")
                jugador3 = st.selectbox("Jugador 3", [j for j in nombres_jugadores if j not in [jugador1, jugador2]], key="j3")
                jugador4 = st.selectbox("Jugador 4", [j for j in nombres_jugadores if j not in [jugador1, jugador2, jugador3]], key="j4")
                
                # Botón para crear partido
                if st.button("Crear partido", type="primary"):
                    nuevo_partido = {
                        'id': len(st.session_state.partidos) + 1,
                        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'jugadores': [jugador1, jugador2, jugador3, jugador4],
                        'parejas': f"{jugador1} y {jugador2} vs {jugador3} y {jugador4}",
                        'finalizado': False
                    }
                    st.session_state.partidos.append(nuevo_partido)
                    st.success("🎯 Partido creado!")
            else:
                st.warning(f"Se necesitan al menos 4 jugadores. Actualmente hay {len(nombres_jugadores)}.")
        else:
            st.info("No hay jugadores registrados.")
    
    with col2:
        st.subheader("Partidos programados")
        if st.session_state.partidos:
            for partido in st.session_state.partidos:
                with st.container():
                    st.write(f"**Partido {partido['id']}**")
                    st.write(f"📅 {partido['fecha']}")
                    st.write(f"🎾 {partido['parejas']}")
                    
                    if not partido['finalizado']:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button(f"Finalizar partido {partido['id']}", key=f"fin_{partido['id']}"):
                                partido['finalizado'] = True
                                # Actualizar contador de partidos de los jugadores
                                for jugador_nombre in partido['jugadores']:
                                    for jugador in st.session_state.jugadores:
                                        if jugador['nombre'] == jugador_nombre:
                                            jugador['partidos_jugados'] += 1
                                
                                # Guardar en historial
                                fecha = datetime.now().strftime("%Y-%m-%d")
                                if fecha not in st.session_state.historial:
                                    st.session_state.historial[fecha] = []
                                st.session_state.historial[fecha].append(partido)
                                st.rerun()
                    else:
                        st.write("✅ Finalizado")
                    st.divider()
        else:
            st.info("No hay partidos creados.")

# Pestaña 3: Estadísticas
with tab3:
    st.header("Estadísticas")
    
    if st.session_state.jugadores:
        # Gráfico de partidos jugados por persona
        st.subheader("Partidos jugados por persona")
        df_stats = pd.DataFrame(st.session_state.jugadores)
        
        # Ordenar por partidos jugados
        df_stats = df_stats.sort_values('partidos_jugados', ascending=False)
        
        # Mostrar gráfico de barras
        st.bar_chart(df_stats.set_index('nombre')['partidos_jugados'])
        
        # Tabla de estadísticas
        st.subheader("Detalle de jugadores")
        st.dataframe(
            df_stats[['nombre', 'nivel', 'partidos_jugados']],
            use_container_width=True,
            hide_index=True
        )
        
        # Recomendación de próximos partidos
        st.subheader("Recomendación para próximo partido")
        if len(st.session_state.jugadores) >= 4:
            # Ordenar jugadores por partidos jugados (menos partidos primero)
            jugadores_ordenados = sorted(
                st.session_state.jugadores,
                key=lambda x: x['partidos_jugados']
            )
            
            # Seleccionar los 4 que menos han jugado
            recomendados = jugadores_ordenados[:4]
            
            st.write("Jugadores recomendados para el próximo partido (los que menos han jugado):")
            for i, jugador in enumerate(recomendados, 1):
                st.write(f"{i}. {jugador['nombre']} ({jugador['partidos_jugados']} partidos)")
            
            # Sugerir parejas aleatorias
            if st.button("Sugerir parejas aleatorias"):
                jugadores_lista = [j['nombre'] for j in recomendados]
                random.shuffle(jugadores_lista)
                st.success(f"Pareja 1: {jugadores_lista[0]} y {jugadores_lista[1]}")
                st.success(f"Pareja 2: {jugadores_lista[2]} y {jugadores_lista[3]}")
    else:
        st.info("No hay suficientes datos para mostrar estadísticas.")

# Pestaña 4: Configuración
with tab4:
    st.header("Configuración")
    
    # Opción para reiniciar datos
    st.subheader("Gestión de datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Exportar datos (JSON)", type="primary"):
            datos = {
                'jugadores': st.session_state.jugadores,
                'partidos': st.session_state.partidos,
                'historial': st.session_state.historial
            }
            st.download_button(
                label="Descargar JSON",
                data=json.dumps(datos, indent=2),
                file_name=f"datos_padel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("Reiniciar todos los datos", type="secondary"):
            st.session_state.jugadores = []
            st.session_state.partidos = []
            st.session_state.historial = {}
            st.success("Datos reiniciados!")
            st.rerun()

# Footer
st.markdown("---")
st.markdown("🎾 App de gestión de pádel - Todos los jugadores juegan la misma cantidad de partidos")
