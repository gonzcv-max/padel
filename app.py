# Agregar después de las importaciones existentes
import streamlit as st
import pandas as pd
import random
import sqlite3
from datetime import datetime
import json
import os
import re

# ... (todas las funciones anteriores se mantienen igual hasta la función paginador)

# ============================================
# FUNCIONES PARA PUNTUACIÓN DE PÁDEL (15-30-40-JUEGO)
# ============================================

def convertir_puntos_tenis(puntos):
    """
    Convierte puntos numéricos a notación de tenis/pádel
    0 -> 0
    1 -> 15
    2 -> 30
    3 -> 40
    4+ -> Juego
    """
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
    """
    Calcula el estado actual del punto en notación de tenis
    """
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
    
    # Punto normal
    return "normal"

def actualizar_puntaje_tenis(partido_id, puntos_pareja1, puntos_pareja2):
    """Actualiza los puntos en la BD"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE partidos 
        SET puntos_pareja1 = ?, puntos_pareja2 = ?
        WHERE id = ?
    ''', (puntos_pareja1, puntos_pareja2, partido_id))
    conn.commit()
    conn.close()

def finalizar_partido_tenis(partido_id, puntos_pareja1, puntos_pareja2, ganadores, ganadores_lista, perdedores_lista):
    """Finaliza el partido y actualiza estadísticas"""
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

# ============================================
# INTERFAZ DE USUARIO MODIFICADA
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

# Pestañas (ahora con 7 tabs incluyendo la nueva de Puntuación)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "👥 Jugadores", "🎯 Partidos", "🏆 Puntuación", "📊 Clasificación", 
    "📜 Historial", "✏️ Editar Partido", "🗑️ Borrar"
])

# TAB 1: Lista de jugadores (sin cambios)
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

# TAB 2: Crear partidos (sin cambios)
with tab2:
    col1, col2 = st.columns(2)
    jugadores = cargar_jugadores()
    
    with col1:
        st.subheader("Nuevo Partido")
        
        if len(jugadores) >= 4:
            nombres = [j['nombre'] for j in jugadores]
            
            # Selección rápida de los que menos jugaron
            if st.button("🎲 Seleccionar los que menos jugaron"):
                menos_jugados = sorted(jugadores, key=lambda x: x['partidos'])
                seleccionados = [j['nombre'] for j in menos_jugados[:4]]
                st.session_state.seleccion_rapida = seleccionados
                st.rerun()
            
            # Selección por parejas
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
                crear_partido(jugador1_p1, jugador2_p1, jugador1_p2, jugador2_p2, pareja1, pareja2)
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
                    if p['puntos_pareja1'] is not None:
                        st.write(f"📊 Puntaje actual: {p['puntos_pareja1']} - {p['puntos_pareja2']}")
                    st.divider()
        else:
            st.info("No hay partidos activos")

# TAB 3: Puntuación con sistema 15-30-40-JUEGO (NUEVA)
with tab3:
    st.header("🏆 Puntuación de Partidos - Sistema 15-30-40")
    st.markdown("---")
    
    partidos_activos = cargar_partidos_activos()
    
    if partidos_activos:
        # Selector de partido con formato claro
        opciones_partido = []
        for p in partidos_activos:
            puntos1 = p['puntos_pareja1'] if p['puntos_pareja1'] is not None else 0
            puntos2 = p['puntos_pareja2'] if p['puntos_pareja2'] is not None else 0
            
            # Mostrar puntaje en formato tenis
            puntaje_tenis1 = convertir_puntos_tenis(puntos1)
            puntaje_tenis2 = convertir_puntos_tenis(puntos2)
            
            opciones_partido.append(f"#{p['id']} - {p['pareja1']} vs {p['pareja2']} [{puntaje_tenis1}-{puntaje_tenis2}]")
        
        partido_seleccionado = st.selectbox(
            "Selecciona el partido", 
            opciones_partido,
            key="puntaje_partido"
        )
        
        # Extraer ID
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
                
                # Mostrar marcador en formato tenis
                puntaje_tenis1 = convertir_puntos_tenis(puntos_actuales1)
                puntaje_tenis2 = convertir_puntos_tenis(puntos_actuales2)
                
                # Determinar estado del punto
                estado = calcular_estado_punto(puntos_actuales1, puntos_actuales2)
                
                # Mostrar marcador grande
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
                elif estado == "game_won_1":
                    st.balloons()
                    st.success(f"🏆 ¡{partido['pareja1']} ha ganado el JUEGO! 🏆")
                elif estado == "game_won_2":
                    st.balloons()
                    st.success(f"🏆 ¡{partido['pareja2']} ha ganado el JUEGO! 🏆")
                
                st.markdown("---")
                
                # Verificar si alguien ya ganó el juego
                if estado in ["game_won_1", "game_won_2"]:
                    st.warning("⚠️ Este juego ya ha terminado. Debes finalizar el partido o crear uno nuevo.")
                    
                    # Botón para finalizar el partido
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f2:
                        if st.button("✅ FINALIZAR PARTIDO", type="primary", use_container_width=True):
                            # Determinar ganadores
                            if puntos_actuales1 > puntos_actuales2:
                                ganadores = partido['pareja1']
                                ganadores_lista = [partido['j1'], partido['j2']]
                                perdedores_lista = [partido['j3'], partido['j4']]
                            else:
                                ganadores = partido['pareja2']
                                ganadores_lista = [partido['j3'], partido['j4']]
                                perdedores_lista = [partido['j1'], partido['j2']]
                            
                            finalizar_partido_tenis(partido_id, puntos_actuales1, puntos_actuales2, 
                                                   ganadores, ganadores_lista, perdedores_lista)
                            st.success(f"✅ Partido finalizado! Ganó {ganadores}")
                            st.rerun()
                
                else:
                    # Botones para sumar puntos (en sistema tenis)
                    st.subheader("➕ Sumar punto")
                    
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                    
                    with col_btn1:
                        if st.button(f"🏸 +1 PUNTO\n{partido['pareja1']}", use_container_width=True, type="primary"):
                            nuevos_puntos = puntos_actuales1 + 1
                            actualizar_puntaje_tenis(partido_id, nuevos_puntos, puntos_actuales2)
                            st.rerun()
                    
                    with col_btn2:
                        if st.button(f"🏸 +1 PUNTO\n{partido['pareja2']}", use_container_width=True, type="primary"):
                            nuevos_puntos = puntos_actuales2 + 1
                            actualizar_puntaje_tenis(partido_id, puntos_actuales1, nuevos_puntos)
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
                    
                    # Modal para restar puntos
                    if st.session_state.get('mostrar_restar_tenis', False):
                        st.markdown("---")
                        st.subheader("➖ Restar punto")
                        col_r1, col_r2, col_r3 = st.columns(3)
                        
                        with col_r1:
                            if st.button(f"➖ Restar a\n{partido['pareja1']}", use_container_width=True):
                                if puntos_actuales1 > 0:
                                    actualizar_puntaje_tenis(partido_id, puntos_actuales1 - 1, puntos_actuales2)
                                    st.session_state['mostrar_restar_tenis'] = False
                                    st.rerun()
                                else:
                                    st.error("No se puede restar más puntos")
                        
                        with col_r2:
                            if st.button(f"➖ Restar a\n{partido['pareja2']}", use_container_width=True):
                                if puntos_actuales2 > 0:
                                    actualizar_puntaje_tenis(partido_id, puntos_actuales1, puntos_actuales2 - 1)
                                    st.session_state['mostrar_restar_tenis'] = False
                                    st.rerun()
                                else:
                                    st.error("No se puede restar más puntos")
                        
                        with col_r3:
                            if st.button("❌ Cancelar", use_container_width=True):
                                st.session_state['mostrar_restar_tenis'] = False
                                st.rerun()
                    
                    # Modal para reiniciar
                    if st.session_state.get('mostrar_reiniciar_tenis', False):
                        st.markdown("---")
                        st.warning("⚠️ ¿Estás segura de que quieres reiniciar el marcador a 0-0?")
                        col_rec1, col_rec2, col_rec3 = st.columns(3)
                        
                        with col_rec2:
                            col_rr1, col_rr2 = st.columns(2)
                            with col_rr1:
                                if st.button("✅ Sí, reiniciar", use_container_width=True):
                                    actualizar_puntaje_tenis(partido_id, 0, 0)
                                    st.session_state['mostrar_reiniciar_tenis'] = False
                                    st.rerun()
                            with col_rr2:
                                if st.button("❌ No, cancelar", use_container_width=True):
                                    st.session_state['mostrar_reiniciar_tenis'] = False
                                    st.rerun()
                    
                    st.markdown("---")
                    
                    # Explicación del sistema de puntuación
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
                        
                        💡 **Consejo**: Si llegas a 40-40 (Deuce), tendrás que ganar 2 puntos seguidos para llevarte el juego.
                        """)
    else:
        st.info("No hay partidos activos. Crea un partido primero en la pestaña 'Partidos'")

# TAB 4: Clasificación (sin cambios)
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

# TAB 5: Historial (sin cambios)
with tab5:
    st.subheader("📜 Historial de Partidos")
    
    filtro_historial = st.text_input("🔍 Buscar en historial (por pareja, resultado o ganadores)", key="filtro_historial")
    items_por_pagina = 20
    
    offset = (st.session_state.get('historial_pagina', 1) - 1) * items_por_pagina
    historial, total_historial = cargar_historial(offset, items_por_pagina, filtro_historial)
    
    if historial:
        st.write(f"**Total de partidos en historial: {total_historial}**")
        
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

# TAB 6: Editar Partido (sin cambios significativos)
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
            
            jugadores_partido = [partido['j1'], partido['j2'], partido['j3'], partido['j4']]
            jugadores_faltantes = [j for j in jugadores_partido if j not in nombres]
            
            if jugadores_faltantes:
                st.warning(f"⚠️ Los siguientes jugadores ya no existen: {', '.join(jugadores_faltantes)}")
            
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
                actualizar_partido(partido_id, jugador1_p1, jugador2_p1, jugador1_p2, jugador2_p2, pareja1, pareja2)
                st.success("✅ Partido actualizado!")
                st.rerun()
    else:
        st.info("No hay partidos activos para editar")

# TAB 7: Borrar (sin cambios)
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
                            eliminar_partido(partido_id)
                            st.success(f"✅ Partido #{partido_id} eliminado!")
                            st.rerun()
    else:
        if filtro_partido:
            st.info(f"No hay partidos que coincidan con '{filtro_partido}'")
        else:
            st.info("No hay partidos registrados")
