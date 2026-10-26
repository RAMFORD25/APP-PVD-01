import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import base64
import hmac
import json
import re
import gspread
from google.oauth2.service_account import Credentials

# Configuración de página con diseño ancho
st.set_page_config(
    page_title="PVD - Dashboard de Solicitudes de Recursos",
    page_icon="🛣️",
    layout="wide"
)

# Estilos CSS Profesionales con Fondo Ejecutivo e Institucional
st.markdown("""
    <style>
    /* Fondo general de la aplicación y área de contenido principal */
    .stApp {
        background-color: #f8fafc !important;
    }

    /* Fondo de infraestructura vial en la barra lateral con capa institucional roja */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(rgba(220, 38, 38, 0.94), rgba(185, 28, 28, 0.94)), url("https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?q=80&w=1000&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        color: white;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: white !important;
    }
    
    /* FORZAR COLOR ROJO EN TEXTOS DE BOTONES Y BORDES */
    div.stButton > button {
        background-color: #ffffff !important;
        border: 2px solid #ffffff !important;
        border-radius: 6px !important;
        width: 100% !important;
        height: 42px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div.stButton > button * {
        color: #dc2626 !important;
        font-weight: 800 !important;
        font-size: 15px !important;
    }
    div.stButton > button:hover {
        background-color: #ffeeef !important;
        border-color: #ffeeef !important;
    }
    div.stButton > button:hover * {
        color: #991b1b !important;
    }

    .header-container {
        background-color: #dc2626;
        padding: 14px 22px;
        border-radius: 8px;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.2);
    }
    .header-title {
        font-size: 20px;
        font-weight: bold;
        color: white;
        margin: 0;
        text-align: center;
        width: 100%;
        letter-spacing: 0.5px;
    }
    
    /* Tarjetas KPI más elegantes con sombra flotante */
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #dc2626;
        padding: 14px 10px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        text-align: center;
        height: 95px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%;
    }
    .kpi-title { 
        font-size: 10px; 
        color: #64748b; 
        font-weight: bold; 
        text-transform: uppercase; 
        line-height: 1.2;
        margin-bottom: 4px;
    }
    .kpi-value { 
        font-size: 22px; 
        color: #dc2626; 
        font-weight: bold; 
        margin: 0;
    }
    .welcome-card-header {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #dc2626;
        padding: 12px;
        border-radius: 8px 8px 0 0;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .welcome-card-header h4 {
        font-size: 15px;
        color: #dc2626;
        margin: 0;
        font-weight: bold;
    }
    .formal-subtitle {
        font-family: 'Arial', sans-serif;
        font-size: 22px;
        font-weight: 800;
        color: #1e293b;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# CONEXIÓN CON GOOGLE SHEETS (cuenta de servicio)
# ----------------------------------------------------
SHEET_ID = "1v2Nc7v7JNB2IVFqhXM81WVJvaJgiuh31HNA68WwbOlI"
NOMBRE_HOJA = "base_solicitudes_recursos"  # pestaña de la base; si no existe se usa la primera
ESTADO_GMS_INICIAL = "En revisión GMS"
COLUMNAS = ["HT", "Region", "Provincia", "Servicio", "Num_Tramos", "Mes",
            "Fecha_Ingreso_Zonal", "Fecha_Opinion_Zonal", "Fecha_Observado_Zonal",
            "Fecha_NuevoIngreso_Zonal", "Fecha_Validacion_GMS",
            "Estado_Zonal", "Estado_GMS", "Tipo_Trámite"]

def _normalizar_pem(k):
    """Reconstruye el PEM aunque lleguen \\n literales, espacios o saltos mal puestos."""
    k = str(k).replace("\\n", "\n")
    m = re.search(r"-----BEGIN PRIVATE KEY-----(.*?)-----END PRIVATE KEY-----", k, re.S)
    if not m:
        return k
    cuerpo = re.sub(r"\s+", "", m.group(1))
    lineas = [cuerpo[i:i + 64] for i in range(0, len(cuerpo), 64)]
    return "-----BEGIN PRIVATE KEY-----\n" + "\n".join(lineas) + "\n-----END PRIVATE KEY-----\n"

def _info_credenciales():
    if "gcp" in st.secrets and "json" in st.secrets["gcp"]:
        return "gcp.json", json.loads(st.secrets["gcp"]["json"])
    return "gcp_service_account", dict(st.secrets["gcp_service_account"])

def diagnostico_credenciales():
    """Datos NO secretos para depurar (no muestra el cuerpo de la llave)."""
    try:
        origen, info = _info_credenciales()
        k = str(info.get("private_key", ""))
        return {
            "origen": origen,
            "campos": sorted(info.keys()),
            "client_email": info.get("client_email"),
            "largo_private_key": len(k),
            "inicio": k[:30],
            "final": k[-30:],
            "saltos_de_linea_reales": k.count("\n"),
            "barra_n_literales": k.count("\\n"),
            "tiene_BEGIN": "-----BEGIN PRIVATE KEY-----" in k,
            "tiene_END": "-----END PRIVATE KEY-----" in k,
        }
    except Exception as e:
        return {"error_al_leer_secrets": f"{type(e).__name__}: {e}"}

@st.cache_resource
def get_hoja():
    _, info = _info_credenciales()
    if "private_key" in info:
        info["private_key"] = _normalizar_pem(info["private_key"])
    creds = Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    libro = gspread.authorize(creds).open_by_key(SHEET_ID)
    try:
        return libro.worksheet(NOMBRE_HOJA)
    except gspread.WorksheetNotFound:
        return libro.get_worksheet(0)

@st.cache_data(ttl=30)
def cargar_datos():
    df = pd.DataFrame(get_hoja().get_all_records())
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS)
    df["HT"] = df["HT"].astype(str).str.strip()
    return df

def _hoy():
    return date.today().isoformat()

def _buscar_fila(ws, enc, ht):
    col_ht = enc.index("HT") + 1
    for i, v in enumerate(ws.col_values(col_ht), start=1):
        if i > 1 and v.strip().upper() == ht.strip().upper():
            return i
    return None

def registrar_solicitud(datos):
    """Agrega una fila nueva respetando el orden de los encabezados de la hoja."""
    ws = get_hoja()
    enc = ws.row_values(1)
    if _buscar_fila(ws, enc, datos["HT"]):
        raise ValueError(f"La HT {datos['HT']} ya está registrada en la base.")
    ws.append_row([datos.get(h, "") for h in enc],
                  value_input_option="USER_ENTERED", table_range="A1")

def actualizar_fila(ht, cambios_fn, provincias_permitidas=None):
    """Modifica celdas de la fila de una HT. cambios_fn(actual) -> dict {columna: valor}."""
    ws = get_hoja()
    enc = ws.row_values(1)
    fila = _buscar_fila(ws, enc, ht)
    if not fila:
        raise ValueError(f"No se encontró la HT {ht} en la base.")
    actual = dict(zip(enc, ws.row_values(fila)))
    if provincias_permitidas is not None and \
            actual.get("Provincia", "").strip().upper() not in provincias_permitidas:
        raise PermissionError("La HT no pertenece a sus provincias asignadas.")
    celdas = [{"range": gspread.utils.rowcol_to_a1(fila, enc.index(k) + 1), "values": [[v]]}
              for k, v in cambios_fn(actual).items() if k in enc]
    ws.batch_update(celdas, value_input_option="USER_ENTERED")

def cambios_zonal(nuevo):
    def f(actual):
        c = {"Estado_Zonal": nuevo}
        if nuevo == "Opinión favorable":
            c["Fecha_Opinion_Zonal"] = _hoy()
            c["Estado_GMS"] = ESTADO_GMS_INICIAL
        elif nuevo == "Observado":
            c["Fecha_Observado_Zonal"] = _hoy()
        elif nuevo == "En revisión" and actual.get("Estado_Zonal") == "Observado":
            c["Fecha_NuevoIngreso_Zonal"] = _hoy()
        return c
    return f

try:
    df = cargar_datos()
except Exception as e:
    st.error(f"No se pudo leer la hoja de Google Sheets: {e}")
    with st.expander("Diagnóstico de la conexión (temporal)"):
        st.write(diagnostico_credenciales())
    df = pd.DataFrame(columns=COLUMNAS)

# Formatear columna Provincia y ordenar por fecha de ingreso reciente a antigua (Cronológico inverso)
if not df.empty and "Provincia" in df.columns:
    df["Num_Tramos"] = pd.to_numeric(df["Num_Tramos"], errors="coerce").fillna(0)
    df["Provincia_Formateada"] = df["Provincia"].astype(str).str.strip().str.title()
    if "Fecha_Ingreso_Zonal" in df.columns:
        df["_Fecha_Temp"] = pd.to_datetime(df["Fecha_Ingreso_Zonal"], errors="coerce", dayfirst=True, format="mixed")
        df = df.sort_values(by="_Fecha_Temp", ascending=False).drop(columns=["_Fecha_Temp"])
else:
    df["Provincia_Formateada"] = "Sin información"

# Función para convertir imágenes locales a Base64
def img_to_base64(possible_names):
    for name in possible_names:
        try:
            with open(name, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception:
            continue
    return ""

img_transp_b64 = img_to_base64(["Consulta Amigable.png", "consulta amigable.png", "transparencia.png"])
img_transf_b64 = img_to_base64(["Consulta Transferencia.png", "consulta transferencia.png", "transferencia.png"])

# Usuarios y Asignación Exacta de Provincias y Regiones
USUARIOS = {
    "central_gms": {"nombre": "Especialista Sede Central", "rol": "SEDE_CENTRAL", "provincias": "TODAS", "regiones": ["Huancavelica", "Moquegua", "Tacna"]},
    "jparra": {"nombre": "José Parra Benavides", "rol": "ESPECIALISTA_ZONAL", "provincias": ["ACOBAMBA"], "regiones": ["Huancavelica"]},
    "evasquez": {"nombre": "Edgar Vásquez Rivera", "rol": "ESPECIALISTA_ZONAL", "provincias": ["ANGARAES", "CHURCAMPA"], "regiones": ["Huancavelica"]},
    "jponce": {"nombre": "Jhon Ponce Francia", "rol": "ESPECIALISTA_ZONAL", "provincias": ["CASTROVIRREYNA", "HUAYTARÁ"], "regiones": ["Huancavelica"]},
    "jcarhuaricra": {"nombre": "Jaqueline Judith Carhuaricra Estrella", "rol": "ESPECIALISTA_ZONAL", "provincias": ["HUANCAVELICA"], "regiones": ["Huancavelica"]},
    "rleon": {"nombre": "Randolf Arturo León Rojas", "rol": "ESPECIALISTA_ZONAL", "provincias": ["TAYACAJA"], "regiones": ["Huancavelica"]},
    "atorres": {"nombre": "Alexa Torres Flores", "rol": "ESPECIALISTA_ZONAL", "provincias": ["TACNA", "CANDARAVE", "TARATA", "JORGE BASADRE"], "regiones": ["Tacna"]},
    "lortiz": {"nombre": "Luis Eduardo Ortiz Fonttis", "rol": "ESPECIALISTA_ZONAL", "provincias": ["MARISCAL NIETO", "ILO", "GENERAL SANCHEZ CERRO"], "regiones": ["Moquegua"]}
}

# ----------------------------------------------------
# SESIÓN (sin parámetros en la URL: la sesión vive solo en el navegador)
# ----------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

def verificar_login(usr, pwd):
    clave = st.secrets.get("passwords", {}).get(usr)
    return usr in USUARIOS and clave is not None and hmac.compare_digest(str(clave), pwd)

# BARRA LATERAL CON CREDENCIALES DE ACCESO
st.sidebar.title("🔐 Acceso al Sistema")
st.sidebar.markdown("---")

if not st.session_state.logged_in:
    usr = st.sidebar.text_input("Usuario")
    pwd = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("INICIAR SESIÓN", key="btn_login"):
        if verificar_login(usr, pwd):
            st.session_state.logged_in = True
            st.session_state.user = USUARIOS[usr]
            st.session_state.usr_key = usr
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos.")
    
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='text-align: center; font-size: 13px; font-weight: bold; margin-bottom: 8px; color: white;'>ENLACES DE INTERÉS MEF</p>", unsafe_allow_html=True)
    
    html_transp = f'<img src="data:image/png;base64,{img_transp_b64}" style="max-height: 45px; width: auto; border-radius: 4px; background-color: white; padding: 4px;" alt="Consulta Amigable"/>' if img_transp_b64 else '<span style="font-size: 13px; font-weight: bold; color: white;">Consulta Amigable</span>'
    html_transf = f'<img src="data:image/png;base64,{img_transf_b64}" style="max-height: 45px; width: auto; border-radius: 4px; background-color: white; padding: 4px;" alt="Consulta Transferencia"/>' if img_transf_b64 else '<span style="font-size: 13px; font-weight: bold; color: white;">Consulta Transferencia</span>'

    st.sidebar.markdown(
        f"""
        <div style="text-align: center; display: flex; flex-direction: column; gap: 12px; align-items: center; padding-bottom: 20px;">
            <a href="https://apps5.mineco.gob.pe/transparencia/Navegador/default.aspx?y=2026&ap=Actividad" target="_blank" title="Consulta Amigable MEF">
                {html_transp}
            </a>
            <a href="https://apps5.mineco.gob.pe/transferencias/gl/default.aspx" target="_blank" title="Consulta de Transferencias MEF">
                {html_transf}
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # ENCABEZADO INSTITUCIONAL PRINCIPAL
    st.markdown("""
        <div style="background-color: #dc2626; padding: 25px; border-radius: 8px; color: white; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.2);">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 800;">PROVÍAS DESCENTRALIZADO</h1>
            <h3 style="color: #fef2f2; margin-top: 8px; font-weight: normal; font-size: 17px;">COORDINACIÓN DE MANTENIMIENTO VIAL — GERENCIA DE MONITOREO Y SEGUIMIENTO (GMS)</h3>
        </div>
    """, unsafe_allow_html=True)

    # TÍTULO DE LA PLATAFORMA FORMAL
    st.markdown('<div class="formal-subtitle">🌐 PLATAFORMA DE MONITOREO Y GESTIÓN</div>', unsafe_allow_html=True)
    st.write("Sistema informático orientado al seguimiento, control de estados y tramitación de recursos para el mantenimiento rutinario de caminos vecinales a nivel nacional.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # TARJETAS DE BIENVENIDA CON COLORES Y PLOTLY
    col_w1, col_w2, col_w3 = st.columns(3)
    
    # GRÁFICO 1: Cobertura Zonal (ROJO)
    with col_w1:
        st.markdown('<div class="welcome-card-header"><h4>🛣️ Cobertura Zonal</h4></div>', unsafe_allow_html=True)
        if not df.empty and "Region" in df.columns:
            df_reg = df.groupby("Region", as_index=False).size()
            df_reg.columns = ["Región", "Solicitudes"]
            fig_w1 = px.bar(
                df_reg, x="Solicitudes", y="Región", orientation="h",
                color_discrete_sequence=["#dc2626"], text="Solicitudes"
            )
            fig_w1.update_layout(
                height=180, margin=dict(l=5, r=5, t=10, b=10),
                xaxis_title="", yaxis_title="", showlegend=False,
                paper_bgcolor="white", plot_bgcolor="white"
            )
            st.plotly_chart(fig_w1, use_container_width=True)
        else:
            st.info("Cargando cobertura zonal...")

    # GRÁFICO 2: Trazabilidad en Línea (AZUL)
    with col_w2:
        st.markdown('<div class="welcome-card-header"><h4>📊 Trazabilidad en Línea</h4></div>', unsafe_allow_html=True)
        if not df.empty and "Estado_Zonal" in df.columns:
            df_est_z = df.groupby("Estado_Zonal", as_index=False).size()
            df_est_z.columns = ["Estado", "Cantidad"]
            fig_w2 = px.pie(
                df_est_z, values="Cantidad", names="Estado", hole=0.5,
                color_discrete_sequence=["#2563eb", "#60a5fa", "#1d4ed8"]
            )
            fig_w2.update_layout(
                height=180, margin=dict(l=5, r=5, t=10, b=10),
                showlegend=True, legend=dict(orientation="h", y=-0.2),
                paper_bgcolor="white", plot_bgcolor="white"
            )
            st.plotly_chart(fig_w2, use_container_width=True)
        else:
            st.info("Cargando estados zonales...")

    # GRÁFICO 3: Validaciones GMS (VERDE)
    with col_w3:
        st.markdown('<div class="welcome-card-header"><h4>👥 Validaciones GMS</h4></div>', unsafe_allow_html=True)
        if not df.empty and "Estado_GMS" in df.columns:
            df_est_gms = df.groupby("Estado_GMS", as_index=False).size()
            df_est_gms.columns = ["Estado GMS", "Cantidad"]
            fig_w3 = px.pie(
                df_est_gms, values="Cantidad", names="Estado GMS", hole=0.5,
                color_discrete_sequence=["#16a34a", "#22c55e", "#15803d"]
            )
            fig_w3.update_layout(
                height=180, margin=dict(l=5, r=5, t=10, b=10),
                showlegend=True, legend=dict(orientation="h", y=-0.2),
                paper_bgcolor="white", plot_bgcolor="white"
            )
            st.plotly_chart(fig_w3, use_container_width=True)
        else:
            st.info("Cargando validaciones GMS...")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("👈 **Instrucción:** Por favor, ingrese su usuario y contraseña asignados en el panel lateral izquierdo para acceder al sistema.")
    st.stop()

user = st.session_state.user

def _exito(msg):
    st.session_state["flash"] = msg
    cargar_datos.clear()
    st.rerun()

# ENCABEZADO SUPERIOR DEL DASHBOARD
st.markdown("""
<div class="header-container">
    <div class="header-title">DASHBOARD DE MONITOREO Y SEGUIMIENTO DE SOLICITUDES DE RECURSOS - SEDE CENTRAL & UNIDADES ZONALES</div>
</div>
""", unsafe_allow_html=True)

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

# BARRA LATERAL CON DATOS DE USUARIO AUTENTICADO
st.sidebar.markdown(f"👤 **{user['nombre']}**")
st.sidebar.markdown(f"📌 *{user['rol']}*")
if user["rol"] == "ESPECIALISTA_ZONAL":
    st.sidebar.markdown(f"📍 **Provincias a cargo:** {', '.join(user['provincias'])}")

if st.sidebar.button("CERRAR SESIÓN", key="btn_logout"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtros de Búsqueda")

df_f = df.copy()

# APLICAR FILTRO ESTRICTO DE PROVINCIAS SEGÚN EL ROL
if user["rol"] == "ESPECIALISTA_ZONAL":
    provincias_usuario = [p.strip().upper() for p in user["provincias"]]
    df_f = df_f[df_f["Provincia"].astype(str).str.strip().str.upper().isin(provincias_usuario)]

# Filtro por Región
regiones = ["Todas"] + sorted(list(df_f["Region"].dropna().unique()))
sel_reg = st.sidebar.selectbox("Región", regiones)
if sel_reg != "Todas":
    df_f = df_f[df_f["Region"] == sel_reg]

# Filtro por Provincia
provincias_disponibles = ["Todas"] + sorted(list(df_f["Provincia"].dropna().unique()))
sel_prov = st.sidebar.selectbox("Provincia", provincias_disponibles)
if sel_prov != "Todas":
    df_f = df_f[df_f["Provincia"] == sel_prov]

# 1. GESTIÓN ZONAL (SI ES ESPECIALISTA ZONAL)
if user["rol"] == "ESPECIALISTA_ZONAL":
    st.markdown("### ➕ Gestión Zonal: Registrar Nueva Solicitud o Actualizar Estado")
    
    tab_nuevo, tab_actualizar = st.tabs(["📝 Registrar Nueva Solicitud", "✏️ Actualizar Estado de Trámite"])
    
    with tab_nuevo:
        with st.form("form_nueva_solicitud"):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                num_ht = st.text_input("Número de HT (ej. E-050000-2026)")
                regiones_permitidas = user.get("regiones", sorted(list(df["Region"].dropna().unique())))
                reg_ing = st.selectbox("Región", regiones_permitidas)
                prov_ing = st.selectbox("Provincia Asignada", user["provincias"])
            with col_f2:
                serv_ing = st.text_input("Servicio / Obra", "Mantenimiento Rutinario")
                num_tram = st.number_input("Número de Tramos", min_value=1, value=1)
                mes_ing = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"])
            with col_f3:
                tipo_t = st.selectbox("Tipo de Trámite", ["Solicitud de recursos", "Recursos RNU"])
                estado_z = st.selectbox("Estado Zonal", ["En revisión", "Opinión favorable", "Observado"])
                fec_ing = st.date_input("Fecha Ingreso Zonal", date.today())
                
            btn_guardar = st.form_submit_button("💾 Guardar Solicitud en la Zonal")
            if btn_guardar:
                ht_n = num_ht.strip().upper()
                if not re.match(r"^[A-Z]-\d{6}-\d{4}$", ht_n):
                    st.error("Ingrese un número de HT válido (ej. E-050000-2026).")
                else:
                    fav = estado_z == "Opinión favorable"
                    datos = {"HT": ht_n, "Region": reg_ing, "Provincia": prov_ing.title(), "Servicio": serv_ing,
                             "Num_Tramos": int(num_tram), "Mes": mes_ing, "Fecha_Ingreso_Zonal": fec_ing.isoformat(),
                             "Fecha_Opinion_Zonal": _hoy() if fav else "",
                             "Fecha_Observado_Zonal": _hoy() if estado_z == "Observado" else "",
                             "Estado_Zonal": estado_z, "Estado_GMS": ESTADO_GMS_INICIAL if fav else "",
                             "Tipo_Trámite": tipo_t}
                    try:
                        registrar_solicitud(datos)
                    except Exception as e:
                        st.error(f"No se pudo guardar en Google Sheets: {e}")
                    else:
                        _exito(f"¡Solicitud {ht_n} registrada con éxito para {prov_ing} ({reg_ing})!")
    
    with tab_actualizar:
        with st.form("form_act_estado"):
            ht_sel = st.selectbox("Seleccione Código HT a modificar:", df_f["HT"].tolist() if not df_f.empty else [])
            nuevo_est_z = st.selectbox("Nuevo Estado Zonal:", ["En revisión", "Opinión favorable", "Observado"])
            btn_act = st.form_submit_button("🔄 Actualizar Estado Zonal")
            if btn_act and ht_sel:
                try:
                    actualizar_fila(ht_sel, cambios_zonal(nuevo_est_z),
                                    [p.strip().upper() for p in user["provincias"]])
                except Exception as e:
                    st.error(f"No se pudo actualizar: {e}")
                else:
                    _exito(f"¡El estado zonal de la HT {ht_sel} fue actualizado a '{nuevo_est_z}' con éxito!")

    st.markdown("---")

# 1.1. GESTIÓN SEDE CENTRAL (SI ES SEDE CENTRAL) - MUESTRA HT, PROVINCIA Y MES
if user["rol"] == "SEDE_CENTRAL":
    st.markdown("### 🏛️ Gestión Sede Central: Validación y Actualización de Estados GMS")
    
    df_pendientes_validacion = pd.DataFrame()
    if not df.empty and "Estado_Zonal" in df.columns and "Estado_GMS" in df.columns:
        cond_opinion = df["Estado_Zonal"].astype(str).str.strip().str.lower() == "opinión favorable"
        cond_no_validado = df["Estado_GMS"].astype(str).str.strip().str.lower() != "validado"
        df_pendientes_validacion = df[cond_opinion & cond_no_validado]
    
    ht_mapping = {}
    if not df_pendientes_validacion.empty:
        for _, row in df_pendientes_validacion.iterrows():
            ht_val = str(row["HT"])
            prov_val = str(row.get("Provincia", "Sin Provincia"))
            mes_val = str(row.get("Mes", "Sin Mes"))
            label_opcion = f"{ht_val} — {prov_val} ({mes_val})"
            ht_mapping[label_opcion] = ht_val

    lista_opciones_ht = list(ht_mapping.keys())
    
    with st.form("form_gms_central"):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            if lista_opciones_ht:
                sel_label = st.selectbox("Seleccionar Código HT a Validar:", lista_opciones_ht)
                ht_sel_central = ht_mapping[sel_label]
            else:
                st.selectbox("Seleccionar Código HT a Validar:", ["No hay HT con opinión favorable pendientes"])
                ht_sel_central = None
        with col_c2:
            nuevo_est_gms = st.selectbox("Estado GMS:", ["En revisión GMS", "Validado", "Observado GMS"])
        with col_c3:
            fec_gms = st.date_input("Fecha de Validación Central", date.today())
            
        btn_gms = st.form_submit_button("🛡️ Actualizar Estado GMS en Sede Central")
        if btn_gms and ht_sel_central:
            cambios = {"Estado_GMS": nuevo_est_gms}
            if nuevo_est_gms == "Validado":
                cambios["Fecha_Validacion_GMS"] = fec_gms.isoformat()
            try:
                actualizar_fila(ht_sel_central, lambda actual: cambios)
            except Exception as e:
                st.error(f"No se pudo actualizar: {e}")
            else:
                _exito(f"¡La HT {ht_sel_central} fue actualizada a '{nuevo_est_gms}' por Sede Central con éxito!")

    st.markdown("---")

# 2. RESUMEN EJECUTIVO (KPIS)
st.markdown("### 📊 Resumen Ejecutivo")

total_s = len(df_f)
op_fav = len(df_f[df_f["Estado_Zonal"] == "Opinión favorable"])
val_gms = len(df_f[df_f["Estado_GMS"] == "Validado"])
pend_val = len(df_f[df_f["Estado_GMS"] == "En revisión GMS"])
rev_zonal = len(df_f[df_f["Estado_Zonal"] == "En revisión"])
obs_zonal = len(df_f[df_f["Estado_Zonal"] == "Observado"])
aprobadas = val_gms

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Solicitudes</div><div class="kpi-value">{total_s}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Op. Favorable Zonal</div><div class="kpi-value">{op_fav}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Validación GMS</div><div class="kpi-value">{val_gms}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Pendiente GMS</div><div class="kpi-value">{pend_val}</div></div>', unsafe_allow_html=True)
with c5: st.markdown(f'<div class="kpi-card"><div class="kpi-title">En Revisión Zonal</div><div class="kpi-value">{rev_zonal}</div></div>', unsafe_allow_html=True)
with c6: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Observados</div><div class="kpi-value">{obs_zonal}</div></div>', unsafe_allow_html=True)
with c7: st.markdown(f'<div class="kpi-card"><div class="kpi-title">Aprobadas/Tramitadas</div><div class="kpi-value">{aprobadas}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 3. BANDEJA EXCLUSIVA PARA SEDE CENTRAL
if user["rol"] == "SEDE_CENTRAL":
    st.markdown("### 🔔 Bandeja de Actualizaciones Recientes de Unidades Zonales")
    st.info("Monitoreo en tiempo real de los trámites que registran avances, opiniones favorables u observaciones en regiones (Últimas 6 actualizaciones).")
    
    df_actualizaciones = df.copy()
    if "Fecha_Opinion_Zonal" in df_actualizaciones.columns:
        df_actualizaciones["Fecha_Temp"] = pd.to_datetime(df_actualizaciones["Fecha_Opinion_Zonal"], errors="coerce", dayfirst=True, format="mixed")
        df_actualizaciones = df_actualizaciones.sort_values(by="Fecha_Temp", ascending=False).head(6)
        df_actualizaciones = df_actualizaciones.drop(columns=["Fecha_Temp"])
    
    st.dataframe(
        df_actualizaciones[["HT", "Region", "Provincia", "Servicio", "Estado_Zonal", "Fecha_Opinion_Zonal", "Estado_GMS"]],
        use_container_width=True
    )
    st.markdown("---")

# 4. BANDEJA DE TRABAJO PRINCIPAL (ORDENADA DE MÁS RECIENTE A MÁS ANTIGUA)
st.markdown("### 📋 Bandeja de Trabajo - Monitoreo y Seguimiento")
st.dataframe(df_f, use_container_width=True)

col_ex1, col_ex2 = st.columns([3, 1])
with col_ex2:
    csv_data = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exportar Reporte (CSV)", data=csv_data, file_name=f"Reporte_Provincia_{sel_prov}.csv", mime="text/csv")

st.markdown("---")

# 5. MÓDULOS INFERIORES: SEDE CENTRAL (ANCHO COMPLETO Y 90°) VS ZONALES (DOS COLUMNAS)
if user["rol"] == "SEDE_CENTRAL":
    st.markdown("### 🚨 Alertas de Solicitudes Críticas")
    st.info("No se registran solicitudes críticas con exceso de días en la bandeja actual.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Eficiencia: Trámites por Provincia y Mes")
    if not df_f.empty and "Mes" in df_f.columns:
        ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        df_eficiencia = df_f.groupby(["Provincia_Formateada", "Mes"], as_index=False)["Num_Tramos"].sum()
        df_eficiencia["Mes"] = pd.Categorical(df_eficiencia["Mes"], categories=ORDEN_MESES, ordered=True)
        df_eficiencia = df_eficiencia.sort_values("Mes")
        
        fig = px.bar(
            df_eficiencia, 
            x="Provincia_Formateada", 
            y="Num_Tramos", 
            color="Mes", 
            barmode="group",
            category_orders={"Mes": ORDEN_MESES},
            labels={
                "Provincia_Formateada": "Provincia", 
                "Num_Tramos": "Cantidad de Tramos / Trámites",
                "Mes": "Mes"
            }
        )
        fig.update_layout(
            height=450, 
            margin=dict(l=10, r=10, t=10, b=50),
            xaxis=dict(tickangle=90),
            paper_bgcolor="white", plot_bgcolor="white"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se cuenta con la información necesaria en la base de datos para graficar la eficiencia.")

else:
    col_inf1, col_inf2 = st.columns(2)

    with col_inf1:
        st.markdown("### 🚨 Alertas de Solicitudes Críticas")
        st.info("No se registran solicitudes críticas con exceso de días en la bandeja actual.")

    with col_inf2:
        st.markdown("### 📈 Eficiencia: Trámites por Provincia y Mes")
        if not df_f.empty and "Mes" in df_f.columns:
            ORDEN_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            df_eficiencia = df_f.groupby(["Provincia_Formateada", "Mes"], as_index=False)["Num_Tramos"].sum()
            df_eficiencia["Mes"] = pd.Categorical(df_eficiencia["Mes"], categories=ORDEN_MESES, ordered=True)
            df_eficiencia = df_eficiencia.sort_values("Mes")
            
            fig = px.bar(
                df_eficiencia, 
                x="Provincia_Formateada", 
                y="Num_Tramos", 
                color="Mes", 
                barmode="group",
                category_orders={"Mes": ORDEN_MESES},
                labels={
                    "Provincia_Formateada": "Provincia", 
                    "Num_Tramos": "Cantidad de Tramos / Trámites",
                    "Mes": "Mes"
                }
            )
            fig.update_layout(
                height=340, 
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickangle=0),
                paper_bgcolor="white", plot_bgcolor="white"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No se cuenta con la información necesaria en la base de datos para graficar la eficiencia.")
