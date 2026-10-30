import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta, timezone
import base64
import hashlib
import hmac
import inspect
import secrets as _secrets
import json
import re
import gspread
import modulo2
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

    /* Formulario de ingreso en la barra lateral: sin borde y con botón blanco / texto rojo */
    [data-testid="stSidebar"] [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] button,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button,
    [data-testid="stSidebar"] button[kind="secondaryFormSubmit"],
    [data-testid="stSidebar"] button[kind="primaryFormSubmit"] {
        background-color: #ffffff !important;
        border: 2px solid #ffffff !important;
        border-radius: 6px !important;
        min-height: 42px !important;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] button *,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button *,
    [data-testid="stSidebar"] button[kind="secondaryFormSubmit"] *,
    [data-testid="stSidebar"] button[kind="primaryFormSubmit"] * {
        color: #dc2626 !important;
        font-weight: 800 !important;
        font-size: 15px !important;
    }
    [data-testid="stSidebar"] [data-testid="stForm"] button:hover {
        background-color: #ffeeef !important;
        border-color: #ffeeef !important;
    }
    /* Cabecera del desplegable de la barra lateral: texto rojo legible sobre fondo blanco */
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background-color: #ffffff !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary *,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
        color: #dc2626 !important;
        fill: #dc2626 !important;
        font-weight: 700 !important;
    }
    /* Mensajes (éxito/error) dentro de la barra lateral: texto oscuro legible */
    [data-testid="stSidebar"] [data-testid="stAlert"],
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] {
        background-color: #ffffff !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] *,
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] * {
        color: #1e293b !important;
    }

    /* Pestañas Módulo 1 / Módulo 2 */
    .stTabs [data-baseweb="tab"] { font-weight: 800; font-size: 1.05rem; padding: 10px 22px; }
    .stTabs [aria-selected="true"] { color: #dc2626 !important; }
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
NOMBRE_HOJA = "BD"  # pestaña de la base; si no existe se usa la primera
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
    df = df[df["HT"] != ""].reset_index(drop=True)  # ignora filas en blanco de la tabla
    return df

def hoy_lima():
    return (datetime.now(timezone.utc) - timedelta(hours=5)).date()

def _hoy():
    return hoy_lima().isoformat()

def _buscar_fila(ws, enc, ht):
    col_ht = enc.index("HT") + 1
    for i, v in enumerate(ws.col_values(col_ht), start=1):
        if i > 1 and v.strip().upper() == ht.strip().upper():
            return i
    return None

def _extender_tabla(ws, fila):
    """Si la fila nueva quedó debajo de la tabla Base_Datos, amplía la tabla hasta ella."""
    meta = ws.spreadsheet.fetch_sheet_metadata(params={"fields": "sheets(properties(sheetId),tables)"})
    for sh in meta.get("sheets", []):
        if sh["properties"]["sheetId"] != ws.id:
            continue
        for t in sh.get("tables", []):
            r = t.get("range", {})
            if r.get("startRowIndex", 0) == 0 and r.get("endRowIndex", 0) < fila:
                ws.spreadsheet.batch_update({"requests": [{"updateTable": {
                    "table": {"tableId": t["tableId"], "range": dict(r, endRowIndex=fila)},
                    "fields": "range"}}]})
            return

def registrar_solicitud(datos):
    """Inserta una fila nueva debajo del último registro de la tabla Base_Datos y la llena."""
    ws = get_hoja()
    enc = ws.row_values(1)
    if _buscar_fila(ws, enc, datos["HT"]):
        raise ValueError(f"La HT {datos['HT']} ya está registrada en la base.")
    col_ht = enc.index("HT") + 1
    fila = len(ws.col_values(col_ht)) + 1  # justo debajo del último registro
    sid = ws.id
    try:  # inserta la fila (hereda el formato de la fila anterior; la tabla crece)
        ws.spreadsheet.batch_update({"requests": [{"insertDimension": {
            "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": fila - 1, "endIndex": fila},
            "inheritFromBefore": True}}]})
    except Exception:
        if fila > ws.row_count:
            ws.add_rows(fila - ws.row_count)
    ws.update(range_name=f"A{fila}", values=[[datos.get(h, "") for h in enc]],
              value_input_option="USER_ENTERED")
    # Lo siguiente es solo estético: si falla, el dato ya quedó guardado
    try:
        _extender_tabla(ws, fila)
    except Exception:
        pass
    try:
        reqs = [{"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": fila - 1, "endRowIndex": fila,
                      "startColumnIndex": i, "endColumnIndex": i + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "d/m/yyyy"}}},
            "fields": "userEnteredFormat.numberFormat"}}
            for i, h in enumerate(enc) if h.startswith("Fecha_")]
        if fila > 2:
            fila_ant = {"sheetId": sid, "startRowIndex": fila - 2, "endRowIndex": fila - 1,
                        "startColumnIndex": 0, "endColumnIndex": len(enc)}
            fila_nueva = dict(fila_ant, startRowIndex=fila - 1, endRowIndex=fila)
            reqs.append({"copyPaste": {"source": fila_ant, "destination": fila_nueva,
                                       "pasteType": "PASTE_DATA_VALIDATION"}})
        ws.spreadsheet.batch_update({"requests": reqs})
    except Exception:
        pass

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
    cambios = cambios_fn(actual)
    celdas = [{"range": gspread.utils.rowcol_to_a1(fila, enc.index(k) + 1), "values": [[v]]}
              for k, v in cambios.items() if k in enc]
    ws.batch_update(celdas, value_input_option="USER_ENTERED")
    try:  # fechas con formato d/m/aaaa (solo estético; el dato ya quedó guardado)
        reqs = [{"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": fila - 1, "endRowIndex": fila,
                      "startColumnIndex": enc.index(k), "endColumnIndex": enc.index(k) + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "d/m/yyyy"}}},
            "fields": "userEnteredFormat.numberFormat"}}
            for k in cambios if k in enc and k.startswith("Fecha_")]
        if reqs:
            ws.spreadsheet.batch_update({"requests": reqs})
    except Exception:
        pass

def cambios_zonal(nuevo, fecha=None):
    """Cambios a escribir al actualizar el estado zonal; 'fecha' la elige el especialista."""
    fecha = fecha or hoy_lima()
    def f(actual):
        if fecha > hoy_lima():
            raise ValueError("La fecha no puede ser futura.")
        ing = pd.to_datetime(actual.get("Fecha_Ingreso_Zonal", ""), dayfirst=True, errors="coerce")
        if pd.notna(ing) and pd.Timestamp(fecha) < ing:
            raise ValueError(f"La fecha no puede ser anterior a la fecha de ingreso ({ing:%d/%m/%Y}).")
        iso = fecha.isoformat()
        c = {"Estado_Zonal": nuevo}
        if nuevo == "Opinión favorable":
            c["Fecha_Opinion_Zonal"] = iso
            if str(actual.get("Estado_GMS", "")).strip().lower() != "validado":
                c["Estado_GMS"] = ESTADO_GMS_INICIAL  # no pisa una validación ya hecha por Sede Central
        elif nuevo == "Observado":
            c["Fecha_Observado_Zonal"] = iso
        elif nuevo == "En revisión" and actual.get("Estado_Zonal") == "Observado":
            c["Fecha_NuevoIngreso_Zonal"] = iso
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
    "jcarhuaricra": {"nombre": "Jaquelin Judith Carhuaricra Estrella", "rol": "ESPECIALISTA_ZONAL", "provincias": ["HUANCAVELICA"], "regiones": ["Huancavelica"]},
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

HOJA_USUARIOS = "Usuarios"  # pestaña (se crea sola) con las claves cambiadas por los usuarios
CLAVE_MIN = 8

def _hash_clave(clave, sal=None):
    sal = sal or _secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), 200_000).hex()
    return f"pbkdf2${sal}${h}"

def _coincide(clave, guardada):
    try:
        _, sal, _ = guardada.split("$")
        return hmac.compare_digest(_hash_clave(clave, sal), guardada)
    except Exception:
        return False

@st.cache_resource
def _hoja_usuarios():
    libro = get_hoja().spreadsheet
    try:
        return libro.worksheet(HOJA_USUARIOS)
    except gspread.WorksheetNotFound:
        ws = libro.add_worksheet(title=HOJA_USUARIOS, rows=50, cols=3)
        ws.update(range_name="A1:C1", values=[["usuario", "clave", "fecha_cambio"]], value_input_option="RAW")
        return ws

def _fila_usuario(ws, usr):
    for i, v in enumerate(ws.col_values(1), start=1):
        if i > 1 and v.strip() == usr:
            return i
    return None

def _clave_guardada(usr):
    ws = _hoja_usuarios()
    fila = _fila_usuario(ws, usr)
    return ws.cell(fila, 2).value if fila else None

def verificar_login(usr, pwd):
    """Clave cambiada por el usuario (hoja 'Usuarios'); si no la cambió, la inicial de Secrets."""
    if usr not in USUARIOS:
        return False
    try:
        guardada = _clave_guardada(usr)
    except Exception as e:
        st.sidebar.error(f"No se pudo verificar la contraseña: {e}")
        return False
    if guardada:
        return _coincide(pwd, guardada)
    inicial = st.secrets.get("passwords", {}).get(usr)
    return inicial is not None and hmac.compare_digest(str(inicial), pwd)

def cambiar_clave(usr, actual, nueva, confirmar):
    if not verificar_login(usr, actual):
        raise ValueError("La contraseña actual no es correcta.")
    if nueva != confirmar:
        raise ValueError("La nueva contraseña y su confirmación no coinciden.")
    if len(nueva) < CLAVE_MIN:
        raise ValueError(f"La nueva contraseña debe tener al menos {CLAVE_MIN} caracteres.")
    if not (any(c.isalpha() for c in nueva) and any(c.isdigit() for c in nueva)):
        raise ValueError("La nueva contraseña debe combinar letras y números.")
    if nueva == actual:
        raise ValueError("La nueva contraseña debe ser distinta de la actual.")
    ws = _hoja_usuarios()
    fila = _fila_usuario(ws, usr)
    valores = [_hash_clave(nueva), hoy_lima().isoformat()]
    if fila:
        ws.update(range_name=f"B{fila}:C{fila}", values=[valores], value_input_option="RAW")
    else:
        ws.append_row([usr] + valores, value_input_option="RAW")

# BARRA LATERAL CON CREDENCIALES DE ACCESO
st.sidebar.title("🔐 Acceso al Sistema")
st.sidebar.markdown("---")

VERIFICACION_SEGURIDAD = True  # False = sin código de verificación en el acceso

if not st.session_state.logged_in:
    img_logo_b64 = img_to_base64(["logo_provias.png"])
    if "cap_n" not in st.session_state:
        st.session_state.cap_n = 0
    if "cap_code" not in st.session_state:
        st.session_state.cap_code = f"{_secrets.randbelow(10000):04d}"

    ICO_USUARIO = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
                   "viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='1.8' stroke-linecap='round' "
                   "stroke-linejoin='round'><circle cx='12' cy='8' r='4'/><path d='M4 21c0-4 4-7 8-7s8 3 8 7'/></svg>\")")
    ICO_CLAVE = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' "
                 "viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='1.8' stroke-linecap='round' "
                 "stroke-linejoin='round'><rect x='5' y='11' width='14' height='9' rx='2'/><path d='M8 11V8a4 4 0 0 1 8 0v3'/></svg>\")")
    st.markdown(f"""
    <style>
    .stApp {{ background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 55%, #e2e8f0 100%) !important; }}
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {{ display: none !important; }}
    [data-testid="stMainBlockContainer"] {{ max-width: 1160px !important; margin: 0 auto !important; }}
    .st-key-login_card {{ max-width: 100%; margin: 18px auto 34px auto; border-radius: 26px; overflow: hidden;
        background: #ffffff; box-shadow: 0 30px 60px -18px rgba(15, 23, 42, 0.30); }}
    .st-key-login_card [data-testid="stHorizontalBlock"] {{ gap: 0 !important; align-items: stretch !important; }}
    .st-key-login_card [data-testid="stColumn"]:first-child, .st-key-login_card [data-testid="column"]:first-child {{
        background: linear-gradient(165deg, #0a1e36 0%, #0d2a47 55%, #123a60 100%); padding: 0 !important; }}
    .st-key-login_card [data-testid="stColumn"]:last-child, .st-key-login_card [data-testid="column"]:last-child {{
        background: #ffffff; padding: 34px 44px 26px 44px !important; }}
    .lg-izq {{ min-height: 690px; padding: 36px 40px; display: flex; flex-direction: column; justify-content: space-between; color: #fff; }}
    .lg-badge {{ display: inline-flex; align-items: center; gap: 12px; padding: 9px 16px 9px 10px; border-radius: 12px;
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14); font-size: 12px; font-weight: 800;
        letter-spacing: 1.6px; width: fit-content; }}
    .lg-barra {{ width: 56px; height: 4px; border-radius: 4px; background: #f43f5e; margin-bottom: 26px; }}
    .lg-sigla {{ font-size: 54px; font-weight: 800; line-height: 1; color: #ffffff; letter-spacing: -1px; }}
    .lg-nombre {{ font-size: 40px; font-weight: 800; line-height: 1.12; color: #cbd5e1; letter-spacing: -1px; margin-top: 4px; }}
    .lg-desc {{ margin-top: 26px; font-size: 15px; line-height: 1.7; color: #e2e8f0; max-width: 380px; }}
    .lg-pie {{ display: inline-flex; align-items: center; gap: 10px; padding: 12px 18px; border-radius: 12px; width: fit-content;
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14); font-size: 13px; font-weight: 600; color: #e2e8f0; }}
    .lg-logo {{ height: 50px; width: auto; max-width: 100%; display: block; margin-bottom: 20px; }}
    .lg-sistema {{ font-size: 11px; font-weight: 800; letter-spacing: 1.6px; color: #475569; display: flex; align-items: center; gap: 8px; }}
    .lg-sistema::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: #dc2626; display: inline-block; }}
    .lg-bienvenido {{ font-size: 36px; font-weight: 800; color: #0f172a; margin: 6px 0 2px 0; letter-spacing: -1px; line-height: 1.15; }}
    .lg-sub {{ font-size: 13px; color: #64748b; margin-bottom: 14px; }}
    .lg-olvido summary {{ list-style: none; cursor: pointer; text-align: right; font-size: 12.5px; font-weight: 700; color: #b91c1c; margin: -4px 0 10px 0; }}
    .lg-olvido summary::-webkit-details-marker {{ display: none; }}
    .lg-olvido div {{ font-size: 12.5px; color: #334155; background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; }}
    .lg-verif {{ border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 12px; padding: 12px 14px 10px 14px; margin: 4px 0 8px 0; }}
    .lg-verif-t {{ font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 8px; }}
    .lg-verif-c {{ font-size: 13.5px; color: #475569; }}
    .lg-codigo {{ display: inline-block; background: #dc2626; color: #fff; font-weight: 800; letter-spacing: 4px; padding: 3px 12px; border-radius: 6px; margin-left: 6px; font-size: 14px; }}
    .lg-mef {{ border-top: 1px solid #e2e8f0; margin-top: 16px; padding-top: 12px; text-align: center; font-size: 12.5px; color: #475569; font-weight: 600; }}
    .lg-mef-links {{ display: flex; justify-content: center; align-items: center; gap: 14px; margin-top: 8px; flex-wrap: wrap; }}
    .lg-mef-links img {{ height: 34px; width: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 3px; background: #fff; }}
    .lg-mef-links a {{ color: #b91c1c; font-weight: 700; text-decoration: none; }}
    /* campos y botón del formulario */
    .st-key-login_card [data-testid="stForm"] {{ border: none !important; padding: 0 !important; }}
    .st-key-login_card [data-testid="stTextInput"] label p {{ font-size: 13px !important; font-weight: 700 !important; color: #0f172a !important; }}
    .st-key-login_card [data-testid="stTextInputRootElement"], .st-key-login_card [data-baseweb="input"], .st-key-login_card [data-baseweb="base-input"] {{ background: #eaf0fb !important; border: 1px solid #dbe4f5 !important; border-radius: 10px !important; }}
    .st-key-login_card [data-baseweb="input"] input {{ background-color: transparent !important; color: #0f172a !important; height: 42px; }}
    .st-key-login_card input[aria-label="Usuario"] {{ background-image: {ICO_USUARIO}; background-repeat: no-repeat; background-position: 12px center; padding-left: 40px !important; }}
    .st-key-login_card input[aria-label="Contraseña"] {{ background-image: {ICO_CLAVE}; background-repeat: no-repeat; background-position: 12px center; padding-left: 40px !important; }}
    .st-key-login_card [data-testid="stFormSubmitButton"] {{ width: 100% !important; }}
    .st-key-login_card [data-testid="stFormSubmitButton"] button, .st-key-login_card form button {{
        width: 100% !important; min-height: 46px; border: none !important; border-radius: 11px !important; margin-top: 6px;
        background: linear-gradient(180deg, #e11d48 0%, #c81e3a 100%) !important; box-shadow: 0 10px 20px -8px rgba(200, 30, 58, 0.55); }}
    .st-key-login_card [data-testid="stFormSubmitButton"] button *, .st-key-login_card form button * {{
        color: #ffffff !important; font-weight: 800 !important; font-size: 15px !important; }}
    .st-key-login_card [data-testid="stFormSubmitButton"] button:hover {{ filter: brightness(1.07); }}
    @media (max-width: 768px) {{ .lg-izq {{ min-height: auto; gap: 24px; }} .st-key-login_card [data-testid="stColumn"]:last-child {{ padding: 26px 22px !important; }} }}
    </style>
    """, unsafe_allow_html=True)

    logo_html = (f'<img class="lg-logo" src="data:image/png;base64,{img_logo_b64}" alt="Provías Descentralizado">'
                 if img_logo_b64 else '<div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:18px;">PROVÍAS <span style="font-weight:500;">Descentralizado</span></div>')
    ico_edificio = ("<svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='#e2e8f0' stroke-width='1.8' "
                    "stroke-linecap='round' stroke-linejoin='round'><rect x='4' y='3' width='9' height='18' rx='1'/>"
                    "<path d='M13 9h6a1 1 0 0 1 1 1v11H13M7 7h3M7 11h3M7 15h3'/></svg>")
    ico_escudo = ("<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='#e2e8f0' stroke-width='1.8' "
                  "stroke-linecap='round' stroke-linejoin='round'><path d='M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z'/>"
                  "<path d='M9 12l2 2 4-4'/></svg>")

    with st.container(key="login_card"):
        col_izq, col_der = st.columns(2, gap="small")
        with col_izq:
            st.markdown(f"""
            <div class="lg-izq">
                <div class="lg-badge">{ico_edificio}<span>PROVÍAS DESCENTRALIZADO</span></div>
                <div>
                    <div class="lg-barra"></div>
                    <div class="lg-sigla">GMS</div>
                    <div class="lg-nombre">Plataforma de Monitoreo y Gestión</div>
                    <div class="lg-desc">Sistema informático orientado al seguimiento, control de estados y tramitación
                    de recursos para el mantenimiento rutinario de caminos vecinales a nivel nacional.</div>
                </div>
                <div class="lg-pie">{ico_escudo}<span>Gerencia de Monitoreo y Seguimiento</span></div>
            </div>
            """, unsafe_allow_html=True)
        with col_der:
            st.markdown(f"""
            {logo_html}
            <div class="lg-sistema">COORDINACIÓN DE MANTENIMIENTO VIAL</div>
            <div class="lg-bienvenido">Bienvenido</div>
            <div class="lg-sub">Ingresa tus credenciales para acceder a tu cuenta.</div>
            """, unsafe_allow_html=True)
            # Formulario: envía de una vez lo escrito o autocompletado por el navegador (y funciona con Enter)
            with st.form("form_login"):
                usr = st.text_input("Usuario", autocomplete="username")
                pwd = st.text_input("Contraseña", type="password", autocomplete="current-password")
                st.markdown("""
                <details class="lg-olvido"><summary>¿Olvidaste tu contraseña?</summary>
                <div>Comuníquese con Sede Central (GMS) para restablecer su contraseña. Si usted la cambió desde la
                aplicación, Sede Central puede devolverle la contraseña inicial.</div></details>
                """, unsafe_allow_html=True)
                cod = ""
                if VERIFICACION_SEGURIDAD:
                    st.markdown(f"""
                    <div class="lg-verif"><div class="lg-verif-t">🛡️ Verificación de seguridad</div>
                    <div class="lg-verif-c">Escriba los números: <span class="lg-codigo">{st.session_state.cap_code}</span></div></div>
                    """, unsafe_allow_html=True)
                    cod = st.text_input("Código de verificación", max_chars=4, placeholder="Escriba los 4 números",
                                        autocomplete="off", label_visibility="collapsed",
                                        key=f"login_cod_{st.session_state.cap_n}")
                enviar_login = st.form_submit_button("Iniciar sesión  →", use_container_width=True)

            if "login_msg" in st.session_state:
                st.error(st.session_state.pop("login_msg"))
            if enviar_login:
                usr = usr.strip().lower()
                if VERIFICACION_SEGURIDAD and cod.strip() != st.session_state.cap_code:
                    st.session_state.login_msg = "El código de verificación no coincide. Intente con el nuevo código."
                elif verificar_login(usr, pwd):
                    st.session_state.logged_in = True
                    st.session_state.user = USUARIOS[usr]
                    st.session_state.usr_key = usr
                    st.session_state.cap_n += 1
                    st.session_state.cap_code = f"{_secrets.randbelow(10000):04d}"
                    st.rerun()
                else:
                    st.session_state.login_msg = "Usuario o contraseña incorrectos."
                if "login_msg" in st.session_state:  # nuevo código y campo de verificación vacío
                    st.session_state.cap_n += 1
                    st.session_state.cap_code = f"{_secrets.randbelow(10000):04d}"
                    st.rerun()

            enlace_amigable = (f'<a href="https://apps5.mineco.gob.pe/transparencia/Navegador/default.aspx?y=2026&ap=Actividad" target="_blank" title="Consulta Amigable MEF">'
                               + (f'<img src="data:image/png;base64,{img_transp_b64}" alt="Consulta Amigable">' if img_transp_b64 else "Consulta Amigable") + "</a>")
            enlace_transf = (f'<a href="https://apps5.mineco.gob.pe/transferencias/gl/default.aspx" target="_blank" title="Consulta de Transferencias MEF">'
                             + (f'<img src="data:image/png;base64,{img_transf_b64}" alt="Consulta Transferencia">' if img_transf_b64 else "Consulta Transferencia") + "</a>")
            st.markdown(f"""
            <div class="lg-mef">Enlaces de interés MEF
                <div class="lg-mef-links">{enlace_amigable}{enlace_transf}</div>
            </div>
            """, unsafe_allow_html=True)

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

    st.stop()

user = st.session_state.user

def _exito(msg):
    st.session_state["flash"] = msg
    st.session_state["modulo_activo"] = "Módulo 1"
    cargar_datos.clear()
    st.rerun()

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

def _guardar_clave():
    try:
        cambiar_clave(st.session_state.usr_key, st.session_state.cc_act,
                      st.session_state.cc_nueva, st.session_state.cc_conf)
    except Exception as e:
        st.session_state["cc_msg"] = ("error", str(e))
    else:
        st.session_state["cc_msg"] = ("ok", "Contraseña actualizada. Úsela en su próximo ingreso.")
        for k in ("cc_act", "cc_nueva", "cc_conf"):
            st.session_state[k] = ""

with st.sidebar.expander("🔑 Cambiar contraseña"):
    st.text_input("Contraseña actual", type="password", key="cc_act", autocomplete="current-password")
    st.text_input("Nueva contraseña", type="password", key="cc_nueva", autocomplete="new-password")
    st.text_input("Confirmar nueva contraseña", type="password", key="cc_conf", autocomplete="new-password")
    st.button("Guardar nueva contraseña", key="btn_cambiar_clave", on_click=_guardar_clave)
    _msg = st.session_state.pop("cc_msg", None)
    if _msg:
        (st.success if _msg[0] == "ok" else st.error)(_msg[1])

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtros de Búsqueda (Módulo 1)")

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

# PESTAÑAS: MÓDULO 1 (seguimiento de solicitudes) Y MÓDULO 2 (validación de tramos)
_pestana = st.session_state.get("modulo_activo", "Módulo 1")
_kw = {"default": _pestana} if "default" in inspect.signature(st.tabs).parameters else {}
tab_m1, tab_m2 = st.tabs(["Módulo 1", "Módulo 2"], **_kw)  # se recuerda la pestaña tras cada acción
tab_m1.__enter__()  # todo lo que sigue (hasta el final del archivo) se muestra dentro de la pestaña Módulo 1
st.markdown("""
<div class="header-container">
    <div class="header-title">SEGUIMIENTO DE SOLICITUDES DE RECURSOS</div>
</div>
""", unsafe_allow_html=True)

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
modulo2.mostrar_avisos(get_hoja().spreadsheet, user, st.session_state.usr_key, con_flash=False)

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
                TIPOS_TRAMITE = ["Solicitud de recursos", "Recursos RNU", "Programación", "Validación", "Uso de Saldo"]
                tipo_t = st.selectbox("Tipo de Trámite", TIPOS_TRAMITE)
                estado_z = st.selectbox("Estado Zonal", ["En revisión", "Opinión favorable", "Observado"])
                fec_ing = st.date_input("Fecha Ingreso Zonal", hoy_lima(), format="DD/MM/YYYY")
                
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
            # Lista del registro más reciente al más antiguo (orden en que se registraron en la hoja)
            ht_sel = st.selectbox("Seleccione Código HT a modificar:",
                                  df_f.sort_index(ascending=False)["HT"].tolist() if not df_f.empty else [])
            nuevo_est_z = st.selectbox("Nuevo Estado Zonal:", ["En revisión", "Opinión favorable", "Observado"])
            fec_op = st.date_input(
                "Fecha de Opinión Zonal:", hoy_lima(), format="DD/MM/YYYY",
                help="Si el estado es 'Opinión favorable' se guarda como Fecha de Opinión Zonal. "
                     "Si es 'Observado' se guarda como fecha de observación, y si una solicitud observada "
                     "vuelve a 'En revisión', como fecha de nuevo ingreso.")
            btn_act = st.form_submit_button("🔄 Actualizar Estado Zonal")
            if btn_act and ht_sel:
                try:
                    actualizar_fila(ht_sel, cambios_zonal(nuevo_est_z, fec_op),
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
        # Sede Central ve TODA solicitud registrada que aún no esté validada (cualquier estado zonal)
        cond_no_validado = df["Estado_GMS"].astype(str).str.strip().str.lower() != "validado"
        df_pendientes_validacion = df[cond_no_validado].sort_index(ascending=False)  # más reciente primero
    
    ht_mapping = {}
    if not df_pendientes_validacion.empty:
        for _, row in df_pendientes_validacion.iterrows():
            ht_val = str(row["HT"])
            prov_val = str(row.get("Provincia", "Sin Provincia"))
            mes_val = str(row.get("Mes", "Sin Mes"))
            est_z = str(row.get("Estado_Zonal", "")).strip() or "Sin estado"
            label_opcion = f"{ht_val} — {prov_val} ({mes_val}) · Zonal: {est_z}"
            ht_mapping[label_opcion] = ht_val

    lista_opciones_ht = list(ht_mapping.keys())
    
    with st.form("form_gms_central"):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            if lista_opciones_ht:
                sel_label = st.selectbox("Seleccionar Código HT a Validar:", lista_opciones_ht)
                ht_sel_central = ht_mapping[sel_label]
            else:
                st.selectbox("Seleccionar Código HT a Validar:", ["No hay HT pendientes de validación"])
                ht_sel_central = None
        with col_c2:
            nuevo_est_gms = st.selectbox("Estado GMS:", ["En revisión GMS", "Validado", "Observado GMS"])
        with col_c3:
            fec_gms = st.date_input("Fecha de Validación Central", hoy_lima(), format="DD/MM/YYYY")
            
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

# ALERTAS DE SOLICITUDES CRÍTICAS
DIAS_CRITICO = 5  # días en bandeja a partir de los cuales una solicitud se marca como crítica

def mostrar_alertas(df_base):
    st.markdown("### 🚨 Alertas de Solicitudes Críticas")
    if df_base.empty or "Estado_Zonal" not in df_base.columns:
        st.info("No hay solicitudes para evaluar.")
        return
    d = df_base.copy()

    def fecha(col):
        if col in d.columns:
            return pd.to_datetime(d[col], errors="coerce", dayfirst=True, format="mixed")
        return pd.Series(pd.NaT, index=d.index, dtype="datetime64[ns]")

    ez = d["Estado_Zonal"].astype(str).str.strip().str.lower()
    eg = d["Estado_GMS"].astype(str).str.strip().str.lower() if "Estado_GMS" in d.columns \
        else pd.Series("", index=d.index)
    ingreso, reingreso = fecha("Fecha_Ingreso_Zonal"), fecha("Fecha_NuevoIngreso_Zonal")
    opinion, observado = fecha("Fecha_Opinion_Zonal"), fecha("Fecha_Observado_Zonal")
    hoy = pd.Timestamp(hoy_lima())

    grupos = [
        ("🆕 Nueva / en revisión zonal", ez == "en revisión", reingreso.fillna(ingreso)),
        ("🟠 Observada (por subsanar)", ez == "observado", observado.fillna(ingreso)),
        ("🏛️ Pendiente de validación GMS", (ez == "opinión favorable") & (eg != "validado"), opinion.fillna(ingreso)),
    ]
    partes = []
    for etiqueta, mask, inicio in grupos:
        sub = d[mask].copy()
        if sub.empty:
            continue
        sub["Tipo de alerta"] = etiqueta
        sub["_inicio"] = inicio[mask]
        sub["Días en bandeja"] = (hoy - inicio[mask]).dt.days
        partes.append(sub)
    if not partes:
        st.success("No hay solicitudes pendientes: sin alertas.")
        return

    al = pd.concat(partes)
    al["Días en bandeja"] = al["Días en bandeja"].fillna(0).astype(int)
    al["Nivel"] = al["Días en bandeja"].apply(lambda x: "🔴 Crítica" if x > DIAS_CRITICO else "🟡 En plazo")
    al["Fecha de inicio"] = al["_inicio"].dt.strftime("%d/%m/%Y").fillna("")
    al = al.sort_values("Días en bandeja", ascending=False)

    n_crit = int((al["Nivel"] == "🔴 Crítica").sum())
    n_nuevas = int((al["Tipo de alerta"] == "🆕 Nueva / en revisión zonal").sum())
    if n_crit:
        st.error(f"{n_crit} solicitud(es) crítica(s): superan {DIAS_CRITICO} días en bandeja.")
    else:
        st.success(f"Sin solicitudes críticas (plazo de referencia: {DIAS_CRITICO} días).")
    if n_nuevas:
        st.warning(f"{n_nuevas} solicitud(es) nueva(s) en revisión zonal.")
    st.dataframe(al[["Nivel", "Tipo de alerta", "HT", "Region", "Provincia", "Fecha de inicio", "Días en bandeja"]],
                 use_container_width=True, hide_index=True)

# 5. MÓDULOS INFERIORES: SEDE CENTRAL (ANCHO COMPLETO Y 90°) VS ZONALES (DOS COLUMNAS)
if user["rol"] == "SEDE_CENTRAL":
    mostrar_alertas(df_f)
    
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
        mostrar_alertas(df_f)

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

# FIN DEL MÓDULO 1 -> MÓDULO 2
tab_m1.__exit__(None, None, None)
with tab_m2:
    if user["rol"] == "SEDE_CENTRAL":
        _df_m2 = df
    else:
        _provs = [p.strip().upper() for p in user["provincias"]]
        _df_m2 = df[df["Provincia"].astype(str).str.strip().str.upper().isin(_provs)] if "Provincia" in df.columns else df
    _hts = list(_df_m2.sort_index(ascending=False)["HT"]) if "HT" in _df_m2.columns else []
    modulo2.render(get_hoja().spreadsheet, user, st.session_state.usr_key, _hts)
