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

# Función para guardar datos automáticamente
def guardar_datos():
    datos = {
        'jugadores': st.session_state.jugadores,
        'partidos': st.session_state.partidos,
        'historial': st.session_state.historial
    }
    st.session_state.datos_guardados = json.dumps(datos)

# Función para cargar datos
def cargar_datos(datos_json):
    try:
        datos = json.loads(datos_json)
        st.session_state.jugadores = datos.get('jugadores', [])
        st.session_state.partidos = datos.get('partidos', [])
        st.session_state.historial = datos.get('historial', {})
        return True
    except:
        return False

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
                guardar_datos()
                st.success(f"✅ {nombre} registrado correctamente!")
                st.rerun()
            else:
                st.error("❌ Este jugador ya existe")
    
    st.markdown("---")
    
    # Cargar datos desde archivo
    st.header("📂 Cargar datos")
    archivo_subido = st.file_uploader("Seleccionar archivo JSON", type=['json'])
    if archivo_subido is not None:
        try:
            contenido = archivo_subido.read().decode('utf-8')
            if cargar_datos(contenido):
                st.success("✅ Datos cargados correctamente!")
                st.rerun()
            else:
                st.error("❌ Error al cargar los datos")
        except:
            st.error("❌ Error al leer el archivo")

# Área principal en pestañas
tab1, tab2, tab3, tab4 = st.tabs(["👥 Jugadores", "🎯 Crear Partidos", "📊 Estadísticas", "⚙️ Configuración"])

# Pestaña 1: Lista de jugadores
with tab1:
    st.header("Jugadores registrados")
    
    if st.session_state.jugadores:
        # Mostrar jugadores en una tabla
        df_jugadores = pd.DataFrame(st.session_state.jugadores)
        
        # Crear columnas para mejor visualización
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.dataframe(
                df_jugadores[['nombre', 'nivel', 'sexo', 'partidos_jugados']],
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            st.metric("Total jugadores", len(st.session_state.jugadores))
            st.metric("Total partidos", len([p for p in st.session_state.partidos if p.get('finalizado', False)]))
        
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
                guardar_datos()
                st.success(f"Jugador {jugador_a_eliminar} eliminado")
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
            # Mostrar cuántos jugadores hay
            st.info(f"Jugadores disponibles: {len(st.session_state.jugadores)}")
            
            # Selección de jugadores para el partido
            nombres_jugadores = [j['nombre'] for j in st.session_state.jugadores]
            
            if len(nombres_jugadores) >= 4:
                # Sugerir jugadores que menos han jugado
                with st.expander("Ver sugerencia de jugadores"):
                    jugadores_ordenados = sorted(
                        st.session_state.jugadores,
                        key=lambda x: x['partidos_jugados']
                    )
                    st.write("Jugadores que menos han jugado:")
                    for j in jugadores_ordenados[:4]:
                        st.write(f"- {j['nombre']} ({j['partidos_jugados']} partidos)")
                
                # Selección manual
                st.write("Selecciona los 4 jugadores:")
                jugador1 = st.selectbox("Jugador 1", nombres_jugadores, key="j1")
                
                # Filtrar opciones para no repetir
                opciones_j2 = [j for j in nombres_jugadores if j != jugador1]
                jugador2 = st.selectbox("Jugador 2", opciones_j2, key="j2")
                
                opciones_j3 = [j for j in nombres_jugadores if j not in [jugador1, jugador2]]
                jugador3 = st.selectbox("Jugador 3", opciones_j3, key="j3")
                
                opciones_j4 = [j for j in nombres_jugadores if j not in [jugador1, jugador2, jugador3]]
                jugador4 = st.selectbox("Jugador 4", opciones_j4, key="j4")
                
                # Opción de mezclar aleatoriamente
                if st.button("🎲 Mezclar parejas aleatoriamente"):
                    jugadores_partido = [jugador1, jugador2, jugador3, jugador4]
                    random.shuffle(jugadores_partido)
                    st.session_state.pareja_temp = {
                        'pareja1': f"{jugadores_partido[0]} y {jugadores_partido[1]}",
                        'pareja2': f"{jugadores_partido[2]} y {jugadores_partido[3]}"
                    }
                
                # Mostrar parejas si se mezclaron
                if 'pareja_temp' in st.session_state:
                    st.write("---")
                    st.write("**Parejas sugeridas:**")
                    st.success(f"🏸 {st.session_state.pareja_temp['pareja1']}")
                    st.success(f"🏸 {st.session_state.pareja_temp['pareja2']}")
                
                # Botón para crear partido
                if st.button("Crear partido", type="primary"):
                    # Determinar las parejas
                    if 'pareja_temp' in st.session_state:
                        parejas = st.session_state.pareja_temp
                        del st.session_state.pareja_temp
                    else:
                        # Parejas por defecto: 1-2 vs 3-4
                        parejas = {
                            'pareja1': f"{jugador1} y {jugador2}",
                            'pareja2': f"{jugador3} y {jugador4}"
                        }
                    
                    nuevo_partido = {
                        'id': len(st.session_state.partidos) + 1,
                        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'jugadores': [jugador1, jugador2, jugador3, jugador4],
                        'pareja1': parejas['pareja1'],
                        'pareja2': parejas['pareja2'],
                        'finalizado': False
                    }
                    st.session_state.partidos.append(nuevo_partido)
                    guardar_datos()
                    st.success("🎯 Partido creado!")
                    st.rerun()
            else:
                st.warning(f"Se necesitan al menos 4 jugadores. Actualmente hay {len(nombres_jugadores)}.")
        else:
            st.info("No hay jugadores registrados.")
    
    with col2:
        st.subheader("Partidos programados")
        if st.session_state.partidos:
            # Filtrar partidos activos
            partidos_activos = [p for p in st.session_state.partidos if not p.get('finalizado', False)]
            
            if partidos_activos:
                for partido in partidos_activos:
                    with st.container():
                        st.write(f"**Partido #{partido['id']}**")
                        st.write(f"📅 {partido['fecha']}")
                        st.write(f"🎾 {partido.get('pareja1', '')}")
                        st.write(f"🎾 {partido.get('pareja2', '')}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button(f"✅ Finalizar partido {partido['id']}", key=f"fin_{partido['id']}"):
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
                                guardar_datos()
                                st.rerun()
                        st.divider()
            else:
                st.info("No hay partidos activos")
                
            # Mostrar partidos finalizados recientemente
            with st.expander("Ver últimos partidos finalizados"):
                partidos_finalizados = [p for p in st.session_state.partidos if p.get('finalizado', False)]
                if partidos_finalizados:
                    for p in partidos_finalizados[-5:]:  # Últimos 5
                        st.write(f"📊 {p['fecha']}: {p.get('pareja1', '')} vs {p.get('pareja2', '')}")
        else:
            st.info("No hay partidos creados.")

# Pestaña 3: Estadísticas
with tab3:
    st.header("Estadísticas")
    
    if st.session_state.jugadores:
        # Métricas principales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Jugadores", len(st.session_state.jugadores))
        with col2:
            total_partidos = len([p for p in st.session_state.partidos if p.get('finalizado', False)])
            st.metric("Partidos Jugados", total_partidos)
        with col3:
            if st.session_state.jugadores:
                promedio = sum(j['partidos_jugados'] for j in st.session_state.jugadores) / len(st.session_state.jugadores)
                st.metric("Promedio partidos/jugador", round(promedio, 1))
        
        # Tabla de estadísticas
        st.subheader("Detalle de jugadores")
        df_stats = pd.DataFrame(st.session_state.jugadores)
        df_stats = df_stats.sort_values('partidos_jugados', ascending=False)
        
        # Mostrar tabla
        st.dataframe(
            df_stats[['nombre', 'nivel', 'partidos_jugados']],
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico simple con barras de texto
        st.subheader("Partidos jugados por persona")
        for _, row in df_stats.iterrows():
            st.text(f"{row['nombre']}: {'█' * row['partidos_jugados']} ({row['partidos_jugados']})")
        
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
                st.write(f"{i}. **{jugador['nombre']}** - {jugador['partidos_jugados']} partidos")
            
            # Botón para crear partido con recomendados
            if st.button("Crear partido con estos jugadores"):
                # Redirigir a la pestaña de crear partido (esto es solo visual)
                st.info("Ve a la pestaña 'Crear Partidos' para formar el partido")
    else:
        st.info("No hay suficientes datos para mostrar estadísticas.")

# Pestaña 4: Configuración
with tab4:
    st.header("Configuración")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Exportar datos")
        if st.button("Preparar exportación", type="primary"):
            datos = {
                'jugadores': st.session_state.jugadores,
                'partidos': st.session_state.partidos,
                'historial': st.session_state.historial,
                'fecha_exportacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            json_str = json.dumps(datos, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Descargar JSON",
                data=json_str,
                file_name=f"datos_padel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        st.subheader("Reiniciar datos")
        if st.button("⚠️ Reiniciar todos los datos", type="secondary"):
            if st.checkbox("Confirmar que quiero reiniciar todos los datos"):
                st.session_state.jugadores = []
                st.session_state.partidos = []
                st.session_state.historial = {}
                guardar_datos()
                st.success("✅ Datos reiniciados correctamente!")
                st.rerun()

# Footer
st.markdown("---")
st.markdown("🎾 **App de gestión de pádel** - Desarrollada con Streamlit")
st.markdown("💡 Todos los jugadores juegan la misma cantidad de partidos")
