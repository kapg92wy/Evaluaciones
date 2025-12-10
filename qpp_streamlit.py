import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ==================== CONFIGURACIÓN ====================
st.set_page_config(
    page_title="Sistema de Evaluación",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).parent
ARCHIVO_RESULTADOS = BASE_DIR / 'resultados_evaluacion.csv'
ARCHIVO_MAQUINAS = BASE_DIR / 'maquinas.json'  # Cambiado a JSON para más flexibilidad
ARCHIVO_TAREAS = BASE_DIR / 'tareas.json'
ARCHIVO_PAYOUT = BASE_DIR / 'historial_payout.csv'
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Usuarios y sus roles
USUARIOS = {
    "Leonel": {"rol": "Ventas", "password": None},
    "Gina": {"rol": "Finanzas", "password": None},
    "Christian": {"rol": "Técnico", "password": None},
    "Eduardo": {"rol": "Calidad", "password": None},
    "Daniel": {"rol": "Soporte", "password": None}
}

ADMIN_PASSWORD = "181025"

# Criterios de evaluación
CRITERIOS_ESTANDAR = [
    {
        "id": 1, "criterio": "VENTA (Presupuesto)", "peso": 0.20, "responsable": "Leonel",
        "sub_items": ["¿La máquina cumple o supera el presupuesto de venta?"]
    },
    {
        "id": 2, "criterio": "VENTA (Payout)", "peso": 0.20, "responsable": "Gina",
        "sub_items": ["¿La máquina cumple el payout/recaudación estipulado?"]
    },
    {
        "id": 3, "criterio": "FUNCIONALIDAD", "peso": 0.20, "responsable": "Christian",
        "sub_items": [
            "¿El voltaje está especificado?",
            "¿Las palancas son mecánicas?",
            "¿Funciones operan correctamente?",
            "¿Estabilidad encendido?",
            "¿Sin calibración constante?",
            "¿Sin desajustes frecuentes?"
        ]
    },
    {
        "id": 4, "criterio": "CALIDAD DE MATERIALES", "peso": 0.10, "responsable": "Eduardo",
        "sub_items": [
            "¿Carcasa metal?", "¿Firmeza?", "¿Ensamblaje?",
            "¿Piezas flojas?", "¿Portacandado?", "¿Chapa alcancía?",
            "¿Bloqueo puertas?", "¿Fuente MEAN WELL?", "¿Cables calibre 14?"
        ]
    },
    {
        "id": 5, "criterio": "LOOK & FEEL", "peso": 0.10, "responsable": "Gina",
        "sub_items": [
            "¿Diseño moderno?", "¿Etiquetas bien?", "¿Sin filos?",
            "¿Estado exterior?", "¿Controles alcanzables?",
            "¿Botones visibles?", "¿Instrucciones claras?", "¿Flujo lógico?"
        ]
    },
    {
        "id": 6, "criterio": "MANTENIMIENTO", "peso": 0.10, "responsable": "Christian",
        "sub_items": [
            "¿Apertura fácil?", "¿Espacio interior?",
            "¿Refacciones comunes?", "¿Modelos identificables?",
            "¿Manual incluido?", "¿Esquema eléctrico?"
        ]
    },
    {
        "id": 7, "criterio": "SOPORTE", "peso": 0.10, "responsable": "Daniel",
        "sub_items": [
            "¿Ajustes clave?",
            "¿Disponibilidad refacciones?",
            "¿Documentación?"
        ]
    }
]

# ==================== FUNCIONES AUXILIARES ====================

def iniciar_archivos():
    """Inicializa archivos si no existen"""
    if not ARCHIVO_RESULTADOS.exists():
        pd.DataFrame(columns=[
            'Maquina', 'Usuario', 'Criterio_ID', 'Criterio',
            'Peso', 'Calificacion', 'Comentarios', 'Fecha'
        ]).to_csv(ARCHIVO_RESULTADOS, index=False, encoding='utf-8-sig')
    
    if not ARCHIVO_PAYOUT.exists():
        pd.DataFrame(columns=[
            'Maquina', 'Fecha', 'Semana', 'Venta', 'Payout', 'Cambios'
        ]).to_csv(ARCHIVO_PAYOUT, index=False, encoding='utf-8-sig')
    
    if not ARCHIVO_MAQUINAS.exists():
        maquinas_default = [
            {
                "nombre": "Clip Machine 4P - #001",
                "asignada_a": ["Leonel", "Gina"],  # Nueva propiedad
                "foto": None,
                "activa": True
            }
        ]
        with open(ARCHIVO_MAQUINAS, 'w', encoding='utf-8') as f:
            json.dump(maquinas_default, f, indent=4, ensure_ascii=False)
    
    if not ARCHIVO_TAREAS.exists():
        with open(ARCHIVO_TAREAS, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)

def get_maquinas(usuario=None):
    """Obtiene lista de máquinas, filtradas por usuario si se especifica"""
    with open(ARCHIVO_MAQUINAS, 'r', encoding='utf-8') as f:
        maquinas = json.load(f)
    
    if usuario and usuario != "ADMIN":
        # Filtrar solo máquinas asignadas al usuario
        maquinas = [m for m in maquinas if usuario in m.get('asignada_a', [])]
    
    return [m for m in maquinas if m.get('activa', True)]

def save_maquinas(lista):
    """Guarda lista de máquinas"""
    with open(ARCHIVO_MAQUINAS, 'w', encoding='utf-8') as f:
        json.dump(lista, f, indent=4, ensure_ascii=False)

def cargar_tareas():
    """Carga tareas desde archivo"""
    if not ARCHIVO_TAREAS.exists():
        return []
    with open(ARCHIVO_TAREAS, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_tareas(lista):
    """Guarda tareas en archivo"""
    with open(ARCHIVO_TAREAS, 'w', encoding='utf-8') as f:
        json.dump(lista, f, indent=4, ensure_ascii=False)

def generar_grafica_payout(df_maquina):
    """Genera gráfica interactiva de Payout con Plotly"""
    if df_maquina.empty:
        return None
    
    # Obtener rango objetivo
    fila_rango = df_maquina[df_maquina['Semana'] == 'META_RANGO']
    target_min = 18.0
    target_max = 22.0
    
    if not fila_rango.empty:
        target_min = float(fila_rango.iloc[-1]['Venta'])
        target_max = float(fila_rango.iloc[-1]['Payout'])
    
    # Datos reales
    datos = df_maquina[df_maquina['Semana'] != 'META_RANGO'].copy()
    if datos.empty:
        return None
    
    semanas = datos['Semana'].tolist()
    porcentajes = datos['Payout'].astype(float).tolist()
    
    # Crear gráfica
    fig = go.Figure()
    
    # Zona ideal (verde)
    fig.add_hrect(
        y0=target_min, y1=target_max,
        fillcolor="green", opacity=0.2,
        layer="below", line_width=0,
        annotation_text=f"Rango Ideal ({target_min}%-{target_max}%)",
        annotation_position="top left"
    )
    
    # Línea de datos
    colores = ['red' if (p < target_min or p > target_max) else '#007bff' for p in porcentajes]
    
    fig.add_trace(go.Scatter(
        x=semanas, y=porcentajes,
        mode='lines+markers',
        name='Payout Real',
        line=dict(color='#007bff', width=3),
        marker=dict(size=10, color=colores)
    ))
    
    fig.update_layout(
        title="Comportamiento de Payout (Premios vs Venta)",
        xaxis_title="Semana",
        yaxis_title="Porcentaje (%)",
        hovermode='x unified',
        height=400
    )
    
    return fig

# ==================== INICIALIZACIÓN ====================
iniciar_archivos()

# ==================== ESTADO DE SESIÓN ====================
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'login'

# ==================== PÁGINAS ====================

def pagina_login():
    """Página de inicio de sesión"""
    st.title("🎰 Sistema de Evaluación de Máquinas")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Identifícate")
        
        usuario_seleccionado = st.selectbox(
            "Usuario",
            options=list(USUARIOS.keys()),
            key="select_usuario"
        )
        
        if st.button("Ingresar", use_container_width=True):
            st.session_state.usuario = usuario_seleccionado
            st.session_state.pagina = 'menu'
            st.rerun()
        
        st.markdown("---")
        
        # Botón admin discreto
        if st.button("🔐 Admin", use_container_width=True):
            st.session_state.pagina = 'admin_login'
            st.rerun()

def pagina_admin_login():
    """Página de login de administrador"""
    st.title("🔐 Panel de Dirección")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        password = st.text_input("Contraseña Maestra", type="password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Entrar", use_container_width=True):
                if password == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.session_state.pagina = 'dashboard'
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")
        
        with col_btn2:
            if st.button("Volver", use_container_width=True):
                st.session_state.pagina = 'login'
                st.rerun()

def pagina_menu():
    """Página de menú principal para usuarios"""
    usuario = st.session_state.usuario
    
    st.title(f"👋 Hola, {usuario}")
    st.caption(f"Rol: {USUARIOS[usuario]['rol']}")
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {usuario}")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.usuario = None
            st.session_state.pagina = 'login'
            st.rerun()
    
    # Tareas pendientes
    todas_tareas = cargar_tareas()
    mis_tareas = [t for t in todas_tareas if t['asignado_a'] == usuario and not t.get('completada', False)]
    
    if mis_tareas:
        st.warning(f"⚠️ Tienes {len(mis_tareas)} tareas pendientes")
        
        for tarea in mis_tareas:
            with st.expander(f"📋 {tarea['titulo']} - {tarea['maquina']}"):
                if tarea['tipo'] == 'CORTE':
                    with st.form(f"form_corte_{tarea['id']}"):
                        st.markdown(f"**Instrucción:** {tarea['pregunta']}")
                        
                        venta = st.number_input("💰 Venta Total ($)", min_value=0.0, step=100.0)
                        payout = st.number_input("🎯 Payout Real (%)", min_value=0.0, max_value=100.0, step=0.1)
                        cambios = st.text_area("📝 Cambios (Opcional)")
                        
                        if st.form_submit_button("Guardar Corte"):
                            # Guardar en CSV
                            nuevo_corte = {
                                'Maquina': tarea['maquina'],
                                'Fecha': datetime.now().strftime("%Y-%m-%d"),
                                'Semana': tarea['titulo'],
                                'Venta': venta,
                                'Payout': payout,
                                'Cambios': cambios
                            }
                            pd.DataFrame([nuevo_corte]).to_csv(
                                ARCHIVO_PAYOUT, mode='a', header=False, index=False, encoding='utf-8-sig'
                            )
                            
                            # Marcar tarea como completada
                            tarea['completada'] = True
                            guardar_tareas(todas_tareas)
                            
                            st.success("✅ Corte registrado")
                            st.rerun()
                else:
                    # Misión normal
                    st.markdown(f"**Pregunta:** {tarea['pregunta']}")
                    st.session_state.tarea_actual = tarea
                    if st.button(f"Responder Misión", key=f"btn_mision_{tarea['id']}"):
                        st.session_state.pagina = 'mision'
                        st.rerun()
        
        st.markdown("---")
    
    # Lista de máquinas asignadas
    st.subheader("🎰 Máquinas Asignadas")
    
    maquinas = get_maquinas(usuario)
    
    if not maquinas:
        st.info("No tienes máquinas asignadas actualmente")
        return
    
    cols = st.columns(3)
    
    for idx, maquina in enumerate(maquinas):
        with cols[idx % 3]:
            with st.container():
                st.markdown(f"### {maquina['nombre']}")
                
                # Mostrar imagen si existe
                foto_path = UPLOAD_FOLDER / f"{maquina['nombre']}.jpg"
                if foto_path.exists():
                    st.image(str(foto_path), use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x200?text=Sin+Foto", use_container_width=True)
                
                if st.button(f"Evaluar", key=f"eval_{maquina['nombre']}"):
                    st.session_state.maquina_actual = maquina['nombre']
                    st.session_state.pagina = 'evaluar'
                    st.rerun()

def pagina_evaluar():
    """Página de evaluación de máquina"""
    maquina = st.session_state.maquina_actual
    usuario = st.session_state.usuario
    
    st.title(f"📝 Evaluando: {maquina}")
    st.caption(f"Evaluador: {usuario}")
    
    # Botón volver
    if st.button("← Volver al Menú"):
        st.session_state.pagina = 'menu'
        st.rerun()
    
    # Encontrar criterios del usuario
    mis_criterios = [c for c in CRITERIOS_ESTANDAR if c['responsable'] == usuario]
    
    if not mis_criterios:
        st.warning("No tienes criterios asignados para evaluar")
        return
    
    with st.form("form_evaluacion"):
        datos_evaluacion = []
        
        for criterio in mis_criterios:
            st.markdown(f"## {criterio['criterio']}")
            
            # Metas especiales
            if criterio['id'] == 1:
                meta = st.number_input(
                    "💰 Define el Presupuesto de Venta Esperado ($)",
                    min_value=0.0, step=1000.0, key=f"meta_{criterio['id']}"
                )
                
                datos_evaluacion.append({
                    'Maquina': maquina, 'Usuario': usuario,
                    'Criterio_ID': criterio['id'], 'Criterio': criterio['criterio'],
                    'Peso': criterio['peso'], 'Calificacion': 3,
                    'Comentarios': f"Meta establecida: ${meta}",
                    'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                
            elif criterio['id'] == 2:
                meta = st.number_input(
                    "🎯 Define el Payout Esperado (%)",
                    min_value=0.0, max_value=100.0, step=0.1, key=f"meta_{criterio['id']}"
                )
                
                # Guardar rango en archivo payout
                payout_row = {
                    'Maquina': maquina,
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'Semana': 'META_RANGO',
                    'Venta': meta - 5.0,  # Min
                    'Payout': meta + 5.0,  # Max
                    'Cambios': f"Meta Payout definida: {meta}%"
                }
                pd.DataFrame([payout_row]).to_csv(
                    ARCHIVO_PAYOUT, mode='a', header=False, index=False, encoding='utf-8-sig'
                )
                
                datos_evaluacion.append({
                    'Maquina': maquina, 'Usuario': usuario,
                    'Criterio_ID': criterio['id'], 'Criterio': criterio['criterio'],
                    'Peso': criterio['peso'], 'Calificacion': 3,
                    'Comentarios': f"Meta establecida: {meta}%",
                    'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                
            else:
               # Evaluación normal con sub-items
                st.markdown("### Sub-criterios")

                calificaciones = []
                detalles = []

                sub_items = criterio['sub_items'][:]  # Copia lista original

                # Permitir agregar nuevos sub-items
                nuevo_sub = st.text_input(f"➕ Agregar nuevo sub-criterio para '{criterio['criterio']}'", key=f"new_sub_{criterio['id']}")
                if nuevo_sub:
                    sub_items.append(nuevo_sub)

                for idx, sub_item in enumerate(sub_items):
                    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])

                    with col1:
                        st.write(sub_item)

                    with col4:
                        no_aplica = st.checkbox(
                            "N/A",
                            key=f"na_{criterio['id']}_{idx}",
                            help="Marcar si este sub-criterio no aplica"
                        )

                    if no_aplica:
                        detalles.append(f"[{sub_item}: NO APLICA]")
                        continue  # No agregar calificación, no promedia

                    with col2:
                        calif = st.number_input(
                            "Calif (1-10)",
                            min_value=1, max_value=10,
                            key=f"calif_{criterio['id']}_{idx}",
                            label_visibility="collapsed"
                        )
                        calificaciones.append(calif)

                    with col3:
                        comentario = st.text_input(
                            "Comentario",
                            key=f"coment_{criterio['id']}_{idx}",
                            label_visibility="collapsed",
                            placeholder="Comentario opcional..."
                        )
                        detalles.append(f"[{sub_item}: {calif}{' - ' + comentario if comentario else ''}]")

                # Calcular calificación general
                if len(calificaciones) == 0:
                    calif_final = 3  # O dime si lo quieres en 0
                    promedio = 0
                    detalles.append("(Todos los sub-criterios marcados como NO APLICA)")
                else:
                    promedio = sum(calificaciones) / len(calificaciones)
                    if promedio >= 9:
                        calif_final = 3
                    elif promedio >= 6:
                        calif_final = 2
                    else:
                        calif_final = 1

                st.markdown(f"**Promedio:** {promedio:.1f} → **Calificación:** {calif_final}")

                datos_evaluacion.append({
                    'Maquina': maquina, 'Usuario': usuario,
                    'Criterio_ID': criterio['id'], 'Criterio': criterio['criterio'],
                    'Peso': criterio['peso'], 'Calificacion': calif_final,
                    'Comentarios': " ".join(detalles),
                    'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
                })

            
            st.markdown("---")
        
        if st.form_submit_button("💾 Guardar Evaluación", use_container_width=True):
            if datos_evaluacion:
                pd.DataFrame(datos_evaluacion).to_csv(
                    ARCHIVO_RESULTADOS, mode='a', header=False, index=False, encoding='utf-8-sig'
                )
                st.success("✅ Evaluación guardada correctamente")
                st.session_state.pagina = 'menu'
                st.rerun()

def pagina_mision():
    """Página para completar misión"""
    tarea = st.session_state.tarea_actual
    usuario = st.session_state.usuario
    
    st.title("📂 Misión de Seguimiento")
    
    st.info(f"**Objetivo:** {tarea['maquina']}")
    st.warning(f"**Pregunta:** {tarea['pregunta']}")
    
    with st.form("form_mision"):
        calificacion = st.selectbox(
            "Evaluación",
            options=[
                (3, "3 - Bien / Cumple Correctamente"),
                (2, "2 - Regular / Tiene detalles"),
                (1, "1 - Mal / No cumple")
            ],
            format_func=lambda x: x[1]
        )
        
        observacion = st.text_area("Observaciones / Hallazgos")
        
        if st.form_submit_button("Enviar Informe"):
            nuevo = {
                'Maquina': tarea['maquina'], 'Usuario': usuario,
                'Criterio_ID': 'MISION',
                'Criterio': f"MISION: {tarea['titulo']}",
                'Peso': 0, 'Calificacion': calificacion[0],
                'Comentarios': f"Pregunta: {tarea['pregunta']} | Resp: {observacion}",
                'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            pd.DataFrame([nuevo]).to_csv(
                ARCHIVO_RESULTADOS, mode='a', header=False, index=False, encoding='utf-8-sig'
            )
            
            # Marcar como completada
            todas_tareas = cargar_tareas()
            for t in todas_tareas:
                if t['id'] == tarea['id']:
                    t['completada'] = True
            guardar_tareas(todas_tareas)
            
            st.success("✅ Misión completada")
            st.session_state.pagina = 'menu'
            st.rerun()
    
    if st.button("Cancelar"):
        st.session_state.pagina = 'menu'
        st.rerun()

def pagina_dashboard():
    """Dashboard administrativo"""
    st.title("🚀 Panel de Dirección")
    
    # Sidebar admin
    with st.sidebar:
        st.markdown("### 👨‍💼 Administrador")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.is_admin = False
            st.session_state.pagina = 'login'
            st.rerun()
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen", "🎰 Máquinas", "📋 Tareas", "📈 Reportes"])
    
    with tab1:
        mostrar_resumen_general()
    
    with tab2:
        gestionar_maquinas()
    
    with tab3:
        gestionar_tareas()
    
    with tab4:
        mostrar_reportes_detallados()

def mostrar_resumen_general():
    """Muestra resumen general de evaluaciones"""
    if not ARCHIVO_RESULTADOS.exists():
        st.info("No hay evaluaciones registradas aún")
        return
    
    df = pd.read_csv(ARCHIVO_RESULTADOS, encoding='utf-8-sig')
    
    if df.empty:
        st.info("No hay evaluaciones registradas aún")
        return
    
    # Gráfica de rendimiento general
    df_std = df[df['Criterio_ID'] != 'MISION'].copy()
    
    if not df_std.empty:
        df_std['Puntaje_Ponderado'] = df_std['Calificacion'] * df_std['Peso']
        resumen = df_std.groupby('Maquina')['Puntaje_Ponderado'].sum().reset_index()
        resumen['Porcentaje'] = (resumen['Puntaje_Ponderado'] / 3.0) * 100
        
        fig = px.bar(
            resumen, x='Maquina', y='Porcentaje',
            title="Rendimiento General (% Aprobación)",
            labels={'Porcentaje': '% Aprobación', 'Maquina': 'Máquina'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Matriz de progreso
    st.subheader("Matriz de Progreso")
    
    maquinas_lista = [m['nombre'] for m in get_maquinas()]
    matriz_data = []
    
    for maquina in maquinas_lista:
        fila = {'Máquina': maquina}
        for usuario in USUARIOS.keys():
            evaluaciones = df[
                (df['Maquina'] == maquina) &
                (df['Usuario'] == usuario) &
                (df['Criterio_ID'] != 'MISION')
            ]
            fila[usuario] = '✅' if not evaluaciones.empty else '⏳'
        matriz_data.append(fila)
    
    if matriz_data:
        st.dataframe(pd.DataFrame(matriz_data), use_container_width=True)

def gestionar_maquinas():
    """Gestión de máquinas"""
    st.subheader("Gestión de Máquinas")
    
    # Agregar nueva máquina
    with st.expander("➕ Agregar Nueva Máquina"):
        with st.form("form_nueva_maquina"):
            nombre = st.text_input("Nombre de la máquina")
            
            usuarios_seleccionados = st.multiselect(
                "Asignar a usuarios",
                options=list(USUARIOS.keys()),
                default=["Leonel", "Gina"]
            )
            
            foto = st.file_uploader("Foto de la máquina", type=['jpg', 'jpeg', 'png'])
            
            if st.form_submit_button("Crear Máquina"):
                if nombre:
                    maquinas = get_maquinas("ADMIN")
                    
                    nueva = {
                        "nombre": nombre,
                        "asignada_a": usuarios_seleccionados,
                        "foto": None,
                        "activa": True
                    }
                    
                    if foto:
                        foto_path = UPLOAD_FOLDER / f"{nombre}.jpg"
                        with open(foto_path, "wb") as f:
                            f.write(foto.getbuffer())
                        nueva["foto"] = str(foto_path)
                    
                    maquinas.append(nueva)
                    save_maquinas(maquinas)
                    
                    st.success(f"✅ Máquina '{nombre}' creada")
                    st.rerun()
    
    # Lista de máquinas existentes
    maquinas = get_maquinas("ADMIN")
    
    st.markdown("---")
    st.subheader("Máquinas Existentes")
    
    for maquina in maquinas:
        with st.expander(f"🎰 {maquina['nombre']}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Asignada a:** {', '.join(maquina['asignada_a'])}")
                
                # Actualizar asignaciones
                nuevas_asignaciones = st.multiselect(
                    "Reasignar a",
                    options=list(USUARIOS.keys()),
                    default=maquina['asignada_a'],
                    key=f"asig_{maquina['nombre']}"
                )
                
                if st.button(f"Actualizar Asignaciones", key=f"btn_asig_{maquina['nombre']}"):
                    maquina['asignada_a'] = nuevas_asignaciones
                    save_maquinas(maquinas)
                    st.success("Actualizado")
                    st.rerun()
            
            with col2:
                if st.button(f"🗑️ Eliminar", key=f"del_{maquina['nombre']}"):
                    maquina['activa'] = False
                    save_maquinas(maquinas)
                    st.success("Máquina eliminada")
                    st.rerun()

def gestionar_tareas():
    """Gestión de tareas y misiones"""
    st.subheader("Asignar Tareas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Solicitar Corte Semanal")
        with st.form("form_corte"):
            responsable = st.selectbox("Responsable", list(USUARIOS.keys()), key="corte_resp")
            maquina = st.selectbox(
                "Máquina",
                [m['nombre'] for m in get_maquinas("ADMIN")],
                key="corte_maq"
            )
            semana = st.text_input("Semana (ej. Semana 3 - Octubre)")
            
            if st.form_submit_button("Asignar Tarea de Corte"):
                import uuid
                nueva_tarea = {
                    'id': str(uuid.uuid4()),
                    'tipo': 'CORTE',
                    'asignado_a': responsable,
                    'maquina': maquina,
                    'titulo': semana,
                    'pregunta': "Registro de Payout",
                    'completada': False
                }
                tareas = cargar_tareas()
                tareas.append(nueva_tarea)
                guardar_tareas(tareas)
                st.success("✅ Tarea de corte asignada")
                st.rerun()
    
    with col2:
        st.markdown("### ⚡ Asignar Misión Extra")
        with st.form("form_mision"):
            responsable = st.selectbox("Responsable", list(USUARIOS.keys()), key="mision_resp")
            maquina = st.selectbox(
                "Máquina",
                [m['nombre'] for m in get_maquinas("ADMIN")],
                key="mision_maq"
            )
            titulo = st.text_input("Título (ej. Revisión)")
            pregunta = st.text_area("Instrucción detallada")
            
            if st.form_submit_button("Enviar Orden"):
                import uuid
                nueva_tarea = {
                    'id': str(uuid.uuid4()),
                    'tipo': 'MISION',
                    'asignado_a': responsable,
                    'maquina': maquina,
                    'titulo': titulo,
                    'pregunta': pregunta,
                    'completada': False
                }
                tareas = cargar_tareas()
                tareas.append(nueva_tarea)
                guardar_tareas(tareas)
                st.success("✅ Misión asignada")
                st.rerun()
    
    # Tareas pendientes
    st.markdown("---")
    st.subheader("Tareas Pendientes")
    
    tareas = cargar_tareas()
    pendientes = [t for t in tareas if not t.get('completada', False)]
    
    if pendientes:
        for tarea in pendientes:
            st.info(f"📋 {tarea['titulo']} - {tarea['maquina']} (Asignada a: {tarea['asignado_a']})")
    else:
        st.success("No hay tareas pendientes")

def mostrar_reportes_detallados():
    """Reportes detallados por máquina"""
    st.subheader("Reportes Detallados")
    
    maquinas = [m['nombre'] for m in get_maquinas("ADMIN")]
    
    if not maquinas:
        st.info("No hay máquinas registradas")
        return
    
    maquina_sel = st.selectbox("Selecciona una máquina", maquinas)
    
    tabs = st.tabs(["📊 Evaluaciones", "💰 Payout"])
    
    with tabs[0]:
        mostrar_detalle_evaluaciones(maquina_sel)
    
    with tabs[1]:
        mostrar_detalle_payout(maquina_sel)

def mostrar_detalle_evaluaciones(maquina):
    """Muestra detalle de evaluaciones de una máquina"""
    if not ARCHIVO_RESULTADOS.exists():
        st.info("No hay evaluaciones")
        return
    
    df = pd.read_csv(ARCHIVO_RESULTADOS, encoding='utf-8-sig')
    df_maq = df[df['Maquina'] == maquina]
    
    if df_maq.empty:
        st.info("No hay evaluaciones para esta máquina")
        return
    
    # Score global
    df_std = df_maq[df_maq['Criterio_ID'] != 'MISION']
    if not df_std.empty:
        puntaje = (df_std['Calificacion'] * df_std['Peso']).sum()
        score = (puntaje / 3.0) * 100
        
        st.metric("Nivel de Aprobación Global", f"{score:.1f}%")
    
    # Radar chart
    agrupado = df_std.groupby('Criterio')['Calificacion'].mean().reset_index()
    
    if not agrupado.empty:
        fig = go.Figure(data=go.Scatterpolar(
            r=agrupado['Calificacion'],
            theta=agrupado['Criterio'],
            fill='toself'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
            showlegend=False,
            title="Fortalezas y Debilidades"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Detalles por criterio
    st.markdown("### Auditoría Desglosada")
    
    for _, row in df_maq.iterrows():
        color = "green" if row['Calificacion'] == 3 else "orange" if row['Calificacion'] == 2 else "red"
        
        with st.container():
            st.markdown(f"""
            <div style="border-left: 5px solid {color}; padding: 10px; margin: 10px 0; background: white; border-radius: 5px;">
                <strong>{row['Usuario']}</strong> | <strong>{row['Criterio']}</strong>
                <br><small>{row['Comentarios']}</small>
            </div>
            """, unsafe_allow_html=True)

def mostrar_detalle_payout(maquina):
    """Muestra detalle de payout de una máquina"""
    if not ARCHIVO_PAYOUT.exists():
        st.info("No hay registros de payout")
        return
    
    df = pd.read_csv(ARCHIVO_PAYOUT, encoding='utf-8-sig')
    df_maq = df[df['Maquina'] == maquina]
    
    if df_maq.empty:
        st.warning("No hay datos de payout para esta máquina")
        st.info("""
        Para ver esta gráfica necesitas:
        1. Que Gina evalúe la máquina para establecer la Meta (%)
        2. Registrar cortes semanales usando las Tareas de Corte
        """)
        return
    
    # Gráfica
    fig = generar_grafica_payout(df_maq)
    
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de historial
    st.subheader("Historial de Cortes Semanales")
    
    df_view = df_maq[df_maq['Semana'] != 'META_RANGO'].copy()
    
    if not df_view.empty:
        # Aplicar colores según el payout
        def colorear_payout(val):
            if val > 22:
                return 'background-color: #ffcccc'
            elif val < 18:
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #d4edda'
        
        styled_df = df_view[['Semana', 'Fecha', 'Venta', 'Payout', 'Cambios']].style.applymap(
            colorear_payout, subset=['Payout']
        )
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Sin registros semanales aún")

# ==================== ROUTER PRINCIPAL ====================

def main():
    """Función principal - Router de páginas"""
    
    pagina = st.session_state.pagina
    
    if pagina == 'login':
        pagina_login()
    elif pagina == 'admin_login':
        pagina_admin_login()
    elif pagina == 'menu':
        pagina_menu()
    elif pagina == 'evaluar':
        pagina_evaluar()
    elif pagina == 'mision':
        pagina_mision()
    elif pagina == 'dashboard':
        if st.session_state.is_admin:
            pagina_dashboard()
        else:
            st.session_state.pagina = 'admin_login'
            st.rerun()
    else:
        st.session_state.pagina = 'login'
        st.rerun()

if __name__ == "__main__":

    main()

