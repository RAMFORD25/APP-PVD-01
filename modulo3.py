"""Módulo 3 - Tablero territorial del mantenimiento vial (matriz PIA).

Fase 1: lectura y validación de las hojas PIA_AAAA / PIA_AAAA_CAMINOS de Google Sheets,
        pantalla de Inicio (indicadores y gráficos con filtros en cascada) y Lista de caminos con ficha.
La programación mensual, el estado de conciliación y los controles se CALCULAN aquí; no se escriben en la hoja.
"""
import io
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from gspread.utils import ValueRenderOption

TITULO = "TABLERO TERRITORIAL DE MANTENIMIENTO VIAL"
TOL_CONCILIACION = 0.10  # soles de diferencia aceptados por redondeo mensual
ROJO, ROJO_OSC, GRIS, AZUL, VERDE = "#dc2626", "#991b1b", "#cbd5e1", "#1e3a8a", "#15803d"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]

# clave, encabezado EXACTO de la plantilla, tipo
SCHEMA = [
    ("id", "ID", "txt"), ("nro", "N° (MATRIZ)", "txt"), ("zona", "UNIDAD ZONAL", "txt"), ("convenio", "N° CONVENIO", "txt"),
    ("tipo_gob", "TIPO DE GOBIERNO", "txt"), ("pliego", "PLIEGO / GOBIERNO", "txt"), ("tipo_mant", "TIPO DE MANTENIMIENTO", "txt"),
    ("superficie", "TIPO DE SUPERFICIE", "txt"), ("depto", "DEPARTAMENTO", "txt"), ("prov", "PROVINCIA", "txt"),
    ("distrito", "DISTRITO", "txt"), ("codigos", "CÓDIGOS DE RUTA", "txt"),
    ("denom", "DENOMINACIÓN DE INTERVENCIÓN (caminos separados por |)", "txt"),
    ("km", "LONGITUD TOTAL (km)", "num"), ("ancho_min", "ANCHO MÍN (m)", "num"), ("ancho_max", "ANCHO MÁX (m)", "num"),
    ("costo", "COSTO (S/ por Km/Mes; periódico: S/ por Km)", "num"), ("plazo", "PLAZO (dc)", "num"),
    ("ajuste_ejec", "AJUSTE DE REDONDEO EJECUCIÓN (S/)", "num"), ("ejec", "EJECUCIÓN (S/)", "num"),
    ("ajuste", "AJUSTE DE REDONDEO GASTOS (S/)", "num"), ("gastos", "GASTOS OPERATIVOS / SUPERVISIÓN (S/)", "num"),
    ("total", "TOTAL (S/)", "num"), ("se_ejecuta", "¿SE EJECUTARÁ?", "txt"), ("n_contrato", "N° CONTRATO / O.S.", "txt"),
    ("modalidad", "MODALIDAD DE CONVOCATORIA", "txt"), ("contratista", "CONTRATISTA", "txt"),
    ("f_contrato", "FECHA DE CONTRATO", "fecha"), ("f_terreno", "FECHA DE ENTREGA DE TERRENO", "fecha"),
    ("f_inicio", "FECHA DE INICIO", "fecha"), ("plazo_ctr", "PLAZO CONTRACTUAL (dc)", "num"),
    ("f_fin", "FECHA DE TÉRMINO", "fecha"), ("monto", "MONTO CONTRATADO (S/)", "num"), ("n_adenda", "N° DE ADENDA", "txt"),
    ("f_adenda", "FECHA DE ADENDA", "fecha"), ("plazo_ad", "PLAZO DE ADENDA (dc)", "num"), ("f_ini_ad", "INICIO DE ADENDA", "fecha"),
    ("f_fin_ad", "TÉRMINO DE ADENDA", "fecha"), ("monto_ad", "MONTO DE ADENDA (S/)", "num"),
    ("s_contrato", "SUP. N° CONTRATO", "txt"), ("s_modalidad", "SUP. MODALIDAD", "txt"), ("s_supervisor", "SUP. SUPERVISOR", "txt"),
    ("s_f_contrato", "SUP. FECHA DE CONTRATO", "fecha"), ("s_f_inicio", "SUP. FECHA DE INICIO", "fecha"),
    ("s_plazo", "SUP. PLAZO (dc)", "num"), ("s_f_fin", "SUP. FECHA DE TÉRMINO", "fecha"),
    ("s_monto", "SUP. MONTO CONTRATADO (S/)", "num"), ("obs", "OBSERVACIONES", "txt")]
REQUERIDAS = ["id", "zona", "depto", "prov", "tipo_mant", "km", "costo", "plazo", "ejec", "gastos", "total", "se_ejecuta",
              "n_contrato", "f_inicio", "plazo_ctr", "f_fin", "monto", "plazo_ad", "f_ini_ad", "f_fin_ad", "monto_ad"]
CAMINOS_PREFIJOS = [("id", "ID"), ("orden", "ORDEN"), ("codigo", "CÓDIGO DE RUTA"), ("denom", "DENOMINACIÓN"),
                    ("km", "LONGITUD"), ("revisar", "REVISAR"), ("obs", "OBSERVACIONES")]


# ---------------------------------------------------------------- utilidades de lectura
def _norm(s):
    return re.sub(r"\s+", " ", str(s if s is not None else "")).strip().upper()


def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").upper().strip()


def _txt(v):
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _num(v):
    if v is None or v == "":
        return float("nan")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return float("nan")


def _fecha(v):
    if v is None or v == "":
        return pd.NaT
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%Y-%m-%d %H:%M:%S"):
        try:
            return pd.Timestamp(datetime.strptime(s, fmt))
        except ValueError:
            continue
    return pd.NaT


def _redondear(x):
    return int(Decimal(str(x)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def parse_servicios(valores):
    """Convierte las filas de la hoja PIA_AAAA en un DataFrame. Devuelve (df, faltantes)."""
    hdr_i = next((i for i, r in enumerate(valores[:6]) if r and _norm(r[0]) == "ID"), None)
    if hdr_i is None:
        return pd.DataFrame(), ["ID"]
    enc = [_norm(h) for h in valores[hdr_i]]
    pos, faltan = {}, []
    for key, hdr, _t in SCHEMA:
        h = _norm(hdr)
        j = enc.index(h) if h in enc else next((k for k, e in enumerate(enc) if e and e[:18] == h[:18]), None)
        if j is None:
            faltan.append(hdr)
        else:
            pos[key] = j
    filas = []
    for n, fila in enumerate(valores[hdr_i + 1:], start=hdr_i + 2):
        if not fila or not _txt(fila[pos["id"]] if "id" in pos and pos["id"] < len(fila) else ""):
            continue
        d = {"fila": n}
        for key, _h, t in SCHEMA:
            v = fila[pos[key]] if key in pos and pos[key] < len(fila) else None
            d[key] = _txt(v) if t == "txt" else (_num(v) if t == "num" else _fecha(v))
        filas.append(d)
    df = pd.DataFrame(filas)
    return df, [f for f in faltan if next(k for k, h, _ in SCHEMA if h == f) in REQUERIDAS]


def parse_caminos(valores):
    if not valores:
        return pd.DataFrame(columns=[k for k, _ in CAMINOS_PREFIJOS])
    enc = [_norm(h) for h in valores[0]]
    pos = {}
    for key, pref in CAMINOS_PREFIJOS:
        j = next((i for i, e in enumerate(enc) if e.startswith(pref)), None)
        if j is not None:
            pos[key] = j
    filas = []
    for n, fila in enumerate(valores[1:], start=2):
        g = lambda k: (fila[pos[k]] if k in pos and pos[k] < len(fila) else None)  # noqa: E731
        if not _txt(g("id")):
            continue
        filas.append({"fila": n, "id": _txt(g("id")), "orden": _num(g("orden")), "codigo": _txt(g("codigo")),
                      "denom": _txt(g("denom")), "km": _num(g("km")), "revisar": _txt(g("revisar")), "obs": _txt(g("obs"))})
    return pd.DataFrame(filas, columns=["fila", "id", "orden", "codigo", "denom", "km", "revisar", "obs"])


# ---------------------------------------------------------------- cálculos
def enriquecer(df, anio):
    """Agrega los valores vigentes (considerando adenda), la programación mensual y la conciliación."""
    d = df.copy()
    if d.empty:
        return d
    ad = (d["plazo_ad"] > 0) & (d["monto_ad"] > 0)
    d["tiene_adenda"] = ad
    ejecuta = d["se_ejecuta"].str.upper().ne("NO")
    contrato = ejecuta & (d["monto"] > 0) & d["f_inicio"].notna() & (d["plazo_ctr"] > 0)
    d["estado_ejec"] = "Con contrato"
    d.loc[~contrato, "estado_ejec"] = "Sin contrato"
    d.loc[~ejecuta, "estado_ejec"] = "No se ejecutará"
    d["plazo_vig"] = d["plazo_ctr"].where(~ad, d["plazo_ad"])
    d["monto_vig"] = d["monto"].where(~ad, d["monto_ad"]).where(contrato, 0.0).fillna(0.0)
    fin_ctr = d["f_fin"].where(d["f_fin"].notna(), d["f_inicio"] + pd.to_timedelta(d["plazo_ctr"] - 1, unit="D"))
    fin_ad = d["f_fin_ad"].where(d["f_fin_ad"].notna(), d["f_ini_ad"] + pd.to_timedelta(d["plazo_ad"] - 1, unit="D"))
    d["fin_ctr"] = fin_ctr
    d["fin_vig"] = fin_ctr.where(~ad, fin_ad)
    d["reduccion"] = (d["monto"] - d["monto_ad"]).where(ad & contrato, 0.0).fillna(0.0)
    d["go_vig"] = (d["monto_vig"] * 0.1).round(2)
    d["total_vig"] = d["monto_vig"] + d["go_vig"]
    d["saldo"] = (d["ejec"].fillna(0) - d["monto_vig"]).where(contrato, d["ejec"].fillna(0))
    # programación mensual (como la matriz original: monto vigente x días del mes / plazo vigente)
    prog = []
    for _, r in d.iterrows():
        fila = [0.0] * 12
        if r["estado_ejec"] == "Con contrato" and pd.notna(r["fin_vig"]) and r["plazo_vig"] > 0:
            for m in range(1, 13):
                a = pd.Timestamp(anio, m, 1)
                b = a + pd.offsets.MonthEnd(0)
                dias = (min(r["fin_vig"], b) - max(r["f_inicio"], a)).days + 1
                if dias > 0:
                    fila[m - 1] = round(r["monto_vig"] * dias / r["plazo_vig"], 2)
        prog.append(fila)
    pm = pd.DataFrame(prog, columns=[f"p{m:02d}" for m in range(1, 13)], index=d.index)
    d = pd.concat([d, pm], axis=1)
    d["prog_total"] = pm.sum(axis=1)
    d["dif_conc"] = (d["monto_vig"] - d["prog_total"]).where(d["estado_ejec"] == "Con contrato", 0.0)
    d["estado_conc"] = d["estado_ejec"]
    con = d["estado_ejec"] == "Con contrato"
    d.loc[con & (d["dif_conc"].abs() <= TOL_CONCILIACION), "estado_conc"] = "Conciliado"
    d.loc[con & (d["dif_conc"] > TOL_CONCILIACION), "estado_conc"] = "Pendiente"
    d.loc[con & (d["dif_conc"] < -TOL_CONCILIACION), "estado_conc"] = "Exceso"
    return d


def control_calidad(d, caminos, anio):
    """Lista de mensajes (nivel, id, tipo, detalle). Niveles: error, aviso, info."""
    out = []
    if d.empty:
        return out
    limite = pd.Timestamp(anio, 12, 31)
    dup = d["id"][d["id"].duplicated()].unique()
    for i in dup:
        out.append(("error", i, "ID duplicado", "El ID aparece más de una vez en la hoja."))
    for _, r in d.iterrows():
        i = r["id"]
        if r["estado_ejec"] == "Con contrato" and pd.notna(r["fin_vig"]) and r["fin_vig"] > limite:
            out.append(("error", i, "Pasa del 31 de diciembre", f"Término vigente {r['fin_vig']:%d/%m/%Y}: el servicio no puede pasar del año fiscal."))
        if r["estado_ejec"] == "Sin contrato":
            out.append(("aviso", i, "Sin contrato", "Se ejecutará pero falta el contrato (monto, fecha de inicio o plazo)."))
        if r["estado_conc"] in ("Pendiente", "Exceso"):
            out.append(("aviso", i, f"Conciliación: {r['estado_conc']}",
                        f"Monto vigente S/ {r['monto_vig']:,.2f} frente a S/ {r['prog_total']:,.2f} programado (diferencia S/ {r['dif_conc']:,.2f})."))
        if pd.notna(r["km"]) and pd.notna(r["costo"]) and pd.notna(r["plazo"]):
            base = (_redondear(Decimal(str(r["km"])) * Decimal(str(r["costo"])))
                    if r["tipo_mant"].upper().startswith("PERI") else
                    _redondear(Decimal(str(r["km"])) * Decimal(str(r["costo"])) * Decimal(str(r["plazo"])) / 30))
            calc = base + (r["ajuste_ejec"] if pd.notna(r["ajuste_ejec"]) else 0)
            if pd.notna(r["ejec"]) and abs(calc - r["ejec"]) > 1:
                out.append(("aviso", i, "Ejecución distinta de la fórmula", f"En la hoja S/ {r['ejec']:,.0f}; por fórmula S/ {calc:,.0f}."))
        else:
            out.append(("aviso", i, "Datos de presupuesto incompletos", "Falta longitud, costo o plazo."))
        if r["tiene_adenda"] and r["estado_ejec"] == "Con contrato" and pd.notna(r["f_ini_ad"]) and pd.notna(r["f_inicio"]) \
                and r["f_ini_ad"] != r["f_inicio"]:
            out.append(("info", i, "Adenda con inicio distinto",
                        f"Inicio de adenda {r['f_ini_ad']:%d/%m/%Y} ≠ inicio del servicio {r['f_inicio']:%d/%m/%Y}."))
        if (r["plazo_ad"] > 0) != (r["monto_ad"] > 0):
            out.append(("aviso", i, "Adenda incompleta", "La adenda necesita plazo y monto."))
        if r["tipo_gob"].upper() == "LOCAL" and r["tipo_mant"].upper().startswith("PERI"):
            out.append(("aviso", i, "Periódico en gobierno local", "El mantenimiento periódico solo aplica a vías departamentales."))
        if r["estado_ejec"] == "Con contrato" and pd.notna(r["fin_ctr"]) and r["fin_ctr"] > limite and r["tiene_adenda"]:
            out.append(("info", i, "Ajustado por adenda", f"El contrato original terminaba {r['fin_ctr']:%d/%m/%Y}; la adenda lo lleva a {r['fin_vig']:%d/%m/%Y}."))
    if caminos is not None and not caminos.empty:
        ids = set(d["id"])
        for i in sorted(set(caminos["id"]) - ids):
            out.append(("error", i, "Camino sin servicio", "El ID de PIA_CAMINOS no existe en la hoja de servicios."))
        for i in sorted(ids - set(caminos["id"])):
            out.append(("aviso", i, "Servicio sin caminos", "No tiene filas en la hoja de caminos."))
        rev = caminos[caminos["revisar"].str.upper() == "SÍ"].groupby("id").size()
        for i, n in rev.items():
            out.append(("info", i, "Códigos por revisar", f"{n} camino(s) con código por confirmar."))
    return out


# ---------------------------------------------------------------- lectura con caché
@st.cache_data(ttl=120, show_spinner=False)
def anios_disponibles(_libro):
    return sorted({int(m.group(1)) for ws in _libro.worksheets() if (m := re.fullmatch(r"PIA_(\d{4})", ws.title))}, reverse=True)


@st.cache_data(ttl=60, show_spinner="Leyendo la matriz PIA…")
def cargar(_libro, anio):
    v = ValueRenderOption.unformatted
    vals = _libro.worksheet(f"PIA_{anio}").get_all_values(value_render_option=v)
    df, faltan = parse_servicios(vals)
    try:
        caminos = parse_caminos(_libro.worksheet(f"PIA_{anio}_CAMINOS").get_all_values(value_render_option=v))
    except gspread.WorksheetNotFound:
        caminos = parse_caminos([])
    d = enriquecer(df, anio) if len(faltan) == 0 else df
    msgs = control_calidad(d, caminos, anio) if len(faltan) == 0 else []
    return d, caminos, msgs, faltan, datetime.now().strftime("%H:%M:%S")


def filtrar_usuario(d, user):
    """Sede Central ve todo; el especialista zonal solo su(s) región(es)."""
    if user["rol"] == "SEDE_CENTRAL" or d.empty:
        return d
    regs = {sin_acentos(r) for r in user["regiones"]}
    return d[d["depto"].map(sin_acentos).isin(regs)]


# ---------------------------------------------------------------- formato
def soles(x, corto=True):
    x = 0 if pd.isna(x) else x
    if not corto:
        return f"S/ {x:,.2f}"
    if abs(x) >= 1e6:
        return f"S/ {x / 1e6:,.2f} M"
    if abs(x) >= 1e3:
        return f"S/ {x / 1e3:,.1f} mil"
    return f"S/ {x:,.0f}"


def _m3():
    st.session_state["modulo_activo"] = "Módulo 3"


def _banner(titulo):
    st.markdown(f'<div class="header-container"><div class="header-title">{titulo}</div></div>', unsafe_allow_html=True)


def _kpi(col, titulo, valor, ayuda=""):
    col.markdown(f'<div class="kpi-card" title="{ayuda}"><div class="kpi-title">{titulo}</div><div class="kpi-value">{valor}</div></div>',
                 unsafe_allow_html=True)


def _selector(col, etiqueta, clave, opciones):
    opciones = ["Todas"] + [o for o in opciones if o]
    if st.session_state.get(clave) not in opciones:
        st.session_state[clave] = "Todas"
    return col.selectbox(etiqueta, opciones, key=clave, on_change=_m3)


def _restablecer():
    for k in ("m3_zona", "m3_depto", "m3_prov", "m3_dist"):
        st.session_state[k] = "Todas"
    st.session_state["m3_q"] = ""
    _m3()


def _filtros(d):
    c = st.columns([1.2, 1.2, 1.3, 1.5, 1.8, 0.8], vertical_alignment="bottom")
    f = d
    zona = _selector(c[0], "Unidad zonal", "m3_zona", sorted(f["zona"].unique()))
    f = f if zona == "Todas" else f[f["zona"] == zona]
    depto = _selector(c[1], "Departamento", "m3_depto", sorted(f["depto"].unique()))
    f = f if depto == "Todas" else f[f["depto"] == depto]
    prov = _selector(c[2], "Provincia", "m3_prov", sorted(f["prov"].unique()))
    f = f if prov == "Todas" else f[f["prov"] == prov]
    dist = _selector(c[3], "Distrito", "m3_dist", sorted(f["distrito"].unique()))
    f = f if dist == "Todas" else f[f["distrito"] == dist]
    q = c[4].text_input("Buscar (ID, código, contratista, N° contrato…)", key="m3_q", on_change=_m3).strip()
    c[5].button("Restablecer", key="m3_reset", on_click=_restablecer, use_container_width=True)
    if q:
        qs = sin_acentos(q)
        campos = f[["id", "codigos", "denom", "contratista", "n_contrato", "pliego"]].astype(str).agg(" ".join, axis=1).map(sin_acentos)
        f = f[campos.str.contains(re.escape(qs))]
    return f


def _fig_base(fig, alto=290):
    fig.update_layout(height=alto, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Source Sans Pro, Arial", size=12, color="#1e293b"), legend=dict(orientation="h", y=-0.15))
    return fig


# ---------------------------------------------------------------- pantallas
def _vista_inicio(f, caminos, msgs, anio):
    n_cam = int(caminos["id"].isin(f["id"]).sum()) if not caminos.empty else 0
    ejec_pia, contr = f["ejec"].fillna(0).sum(), f["monto_vig"].sum()
    k = st.columns(7)
    _kpi(k[0], "SERVICIOS", f"{len(f):,}", "Cada N° de la matriz: puede agrupar varios caminos")
    _kpi(k[1], "CAMINOS", f"{n_cam:,}", "Filas de la hoja PIA_AAAA_CAMINOS")
    _kpi(k[2], "LONGITUD", f"{f['km'].sum():,.1f} km")
    _kpi(k[3], "PRESUPUESTO PIA", soles(f["total"].fillna(0).sum()), "Ejecución + gastos operativos / supervisión")
    _kpi(k[4], "CONTRATADO VIGENTE", soles(contr), "Ejecución contratada (con adendas)")
    _kpi(k[5], "SALDO NO CONTRATADO", soles(f["saldo"].sum()), "Presupuesto de ejecución - contratado vigente")
    _kpi(k[6], "CON ADENDA", f"{int(f['tiene_adenda'].sum()):,}", "Servicios cuyo plazo y monto fueron modificados")
    st.write("")

    c1, c2, c3 = st.columns([1, 1.25, 1.25])
    with c1:
        st.markdown("##### Situación de la cartera")
        cuenta = f["estado_ejec"].value_counts()
        fig = go.Figure(go.Pie(labels=list(cuenta.index), values=list(cuenta.values), hole=0.62, sort=False,
                               marker=dict(colors=[{"Con contrato": ROJO_OSC, "Sin contrato": "#f59e0b", "No se ejecutará": GRIS}[x] for x in cuenta.index]),
                               textinfo="value"))
        fig.add_annotation(text=f"<b>{len(f)}</b><br>servicios", showarrow=False, font=dict(size=15))
        st.plotly_chart(_fig_base(fig), use_container_width=True, key="m3_g_estado")
    with c2:
        st.markdown("##### Presupuesto y contratado por provincia (ejecución)")
        g = f.groupby("prov").agg(pia=("ejec", "sum"), contr=("monto_vig", "sum")).sort_values("pia")
        fig = go.Figure()
        fig.add_bar(y=g.index, x=g["pia"], orientation="h", name="Presupuesto PIA", marker_color=GRIS)
        fig.add_bar(y=g.index, x=g["contr"], orientation="h", name="Contratado vigente", marker_color=ROJO_OSC)
        fig.update_layout(barmode="group")
        fig.update_xaxes(tickformat=",.2s")
        st.plotly_chart(_fig_base(fig), use_container_width=True, key="m3_g_prov")
    with c3:
        st.markdown(f"##### Programación mensual {anio} (ejecución)")
        mens = [f[f"p{m:02d}"].sum() for m in range(1, 13)]
        fig = go.Figure(go.Bar(x=MESES, y=mens, marker_color=ROJO, hovertemplate="%{x}: S/ %{y:,.0f}<extra></extra>"))
        fig.update_yaxes(tickformat=",.2s")
        st.plotly_chart(_fig_base(fig), use_container_width=True, key="m3_g_mes")

    c4, c5 = st.columns([1, 1.6])
    with c4:
        st.markdown("##### Modalidad de contratación")
        mod = f[f["estado_ejec"] == "Con contrato"]["modalidad"].replace("", "Sin dato").value_counts()
        fig = go.Figure(go.Bar(x=list(mod.values), y=list(mod.index), orientation="h", marker_color=AZUL, text=list(mod.values)))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(_fig_base(fig, 230), use_container_width=True, key="m3_g_mod")
        cc = f["estado_conc"].value_counts()
        st.caption("Conciliación (monto vigente frente a lo programado): " + " · ".join(f"{k}: **{v}**" for k, v in cc.items()))
    with c5:
        st.markdown("##### Alertas y control de la matriz")
        ids = set(f["id"])
        m = [x for x in msgs if x[1] in ids]
        e, a, i = (sum(1 for x in m if x[0] == n) for n in ("error", "aviso", "info"))
        st.markdown(f"🔴 **{e}** errores · 🟠 **{a}** avisos · 🔵 **{i}** informativos")
        if m:
            tabla = pd.DataFrame(m, columns=["Nivel", "ID", "Control", "Detalle"])
            tabla["Nivel"] = tabla["Nivel"].map({"error": "🔴 Error", "aviso": "🟠 Aviso", "info": "🔵 Info"})
            orden = {"🔴 Error": 0, "🟠 Aviso": 1, "🔵 Info": 2}
            tabla = tabla.sort_values("Nivel", key=lambda s: s.map(orden))
            st.dataframe(tabla, hide_index=True, use_container_width=True, height=230)
        else:
            st.success("Sin alertas para el filtro actual.")


def _a_excel(f):
    cols = {"id": "ID", "zona": "Unidad zonal", "convenio": "N° convenio", "pliego": "Pliego", "depto": "Departamento", "prov": "Provincia",
            "distrito": "Distrito", "codigos": "Códigos de ruta", "denom": "Denominación", "km": "Longitud (km)", "costo": "Costo",
            "plazo": "Plazo (dc)", "ejec": "Ejecución (S/)", "gastos": "Gastos operativos / supervisión (S/)", "total": "Total (S/)",
            "n_contrato": "N° contrato", "contratista": "Contratista", "monto_vig": "Monto vigente (S/)", "f_inicio": "Inicio",
            "fin_vig": "Término vigente", "estado_conc": "Conciliación"}
    out = f[list(cols)].rename(columns=cols)
    for c in ("Inicio", "Término vigente"):
        out[c] = out[c].dt.strftime("%d/%m/%Y")
    buf = io.BytesIO()
    out.to_excel(buf, index=False, sheet_name="Servicios")
    return buf.getvalue()


def _vista_lista(f, caminos, anio):
    st.markdown("##### Lista de caminos (servicios)")
    if f.empty:
        st.info("No hay servicios para el filtro actual.")
        return
    t = f[["id", "prov", "distrito", "codigos", "denom", "km", "costo", "plazo", "ejec", "n_contrato", "monto_vig", "f_inicio", "fin_vig",
           "tiene_adenda", "estado_conc"]].copy()
    t["tiene_adenda"] = t["tiene_adenda"].map({True: "Sí", False: ""})
    for c in ("f_inicio", "fin_vig"):
        t[c] = t[c].dt.strftime("%d/%m/%Y").fillna("")
    cc = st.column_config
    st.dataframe(t, hide_index=True, use_container_width=True, height=330, column_config={
        "id": "ID", "prov": "Provincia", "distrito": "Distrito", "codigos": "Códigos", "denom": cc.TextColumn("Denominación", width="large"),
        "km": cc.NumberColumn("Km", format="%.3f"), "costo": cc.NumberColumn("Costo", format="%.2f"), "plazo": cc.NumberColumn("Plazo", format="%d"),
        "ejec": cc.NumberColumn("Ejecución PIA", format="%d"), "n_contrato": "Contrato", "monto_vig": cc.NumberColumn("Monto vigente", format="%.2f"),
        "f_inicio": "Inicio", "fin_vig": "Término vigente", "tiene_adenda": "Adenda", "estado_conc": "Conciliación"})
    st.download_button("⬇️ Exportar lista (Excel)", data=_a_excel(f), file_name=f"servicios_PIA_{anio}.xlsx", key="m3_xls",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")
    ids = list(f["id"])
    etiquetas = {r["id"]: f"{r['id']} · {r['prov']} · {r['codigos'] or r['denom'][:40]}" for _, r in f.iterrows()}
    if st.session_state.get("m3_ficha") not in ids:
        st.session_state["m3_ficha"] = ids[0]
    sel = st.selectbox("Ficha del servicio", ids, format_func=lambda i: etiquetas[i], key="m3_ficha", on_change=_m3)
    r = f[f["id"] == sel].iloc[0]
    cam = caminos[caminos["id"] == sel] if not caminos.empty else caminos

    st.markdown(f"#### {r['id']} · {r['prov']} · {r['pliego']}")
    st.caption(r["denom"].replace(" | ", "  ·  "))
    c1, c2, c3 = st.columns(3)
    ancho = "—" if pd.isna(r["ancho_min"]) else "%.2f – %.2f m" % (r["ancho_min"], r["ancho_max"])
    c1.markdown(
        f"**Ubicación y alcance**  \n- Unidad zonal: {r['zona']}  \n- Convenio N° {r['convenio'] or '—'}  \n"
        f"- {r['depto']} / {r['prov']} / {r['distrito']}  \n- {r['tipo_mant']} · {r['superficie']}  \n- Códigos: {r['codigos'] or '—'}  \n"
        f"- Caminos: {len(cam)}  \n- Longitud: {r['km']:,.3f} km  \n- Ancho: {ancho}")
    c2.markdown(
        f"**Presupuesto PIA**  \n- Costo: S/ {r['costo']:,.2f} {'por km' if str(r['tipo_mant']).upper().startswith('PERI') else 'por km/mes'}  \n"
        f"- Plazo: {r['plazo']:,.0f} días  \n- Ejecución: S/ {r['ejec']:,.0f}  \n- Gastos operativos: S/ {r['gastos']:,.0f}  \n- Total: S/ {r['total']:,.0f}")
    ctr = "—"
    if r["estado_ejec"] == "Con contrato":
        ctr = (f"{r['n_contrato']} · {r['modalidad']}  \n- Contratista: {r['contratista']}  \n- Inicio: {r['f_inicio']:%d/%m/%Y} · Plazo: {r['plazo_ctr']:,.0f} días · "
               f"Término: {r['fin_ctr']:%d/%m/%Y}  \n- Monto contratado: S/ {r['monto']:,.2f}")
        if r["tiene_adenda"]:
            ctr += (f"  \n- **Adenda {r['n_adenda'] or ''}**: plazo {r['plazo_ad']:,.0f} días, monto S/ {r['monto_ad']:,.2f}, "
                    f"término vigente {r['fin_vig']:%d/%m/%Y}")
    elif r["estado_ejec"] == "No se ejecutará":
        ctr = "No se ejecutará"
    else:
        ctr = "Sin contrato (por contratar)"
    c3.markdown(f"**Contrato y adenda**  \n- {ctr}  \n- Monto vigente: S/ {r['monto_vig']:,.2f}  \n- Conciliación: **{r['estado_conc']}**")
    if r["s_contrato"]:
        c3.markdown(f"**Supervisión**  \n- {r['s_contrato']} · {r['s_supervisor']}  \n- Monto: S/ {r['s_monto']:,.2f}")

    st.markdown(f"##### Programación mensual {anio}")
    mens = [r[f"p{m:02d}"] for m in range(1, 13)]
    g1, g2 = st.columns([1.4, 1])
    fig = go.Figure(go.Bar(x=MESES, y=mens, marker_color=ROJO, hovertemplate="%{x}: S/ %{y:,.2f}<extra></extra>"))
    g1.plotly_chart(_fig_base(fig, 240), use_container_width=True, key="m3_g_ficha")
    prog = pd.DataFrame({"Mes": MESES, "Ejecución (S/)": mens})
    prog["Gastos operativos (S/)"] = (prog["Ejecución (S/)"] * 0.1).round(2)
    prog["Total (S/)"] = prog["Ejecución (S/)"] + prog["Gastos operativos (S/)"]
    prog = prog[prog["Ejecución (S/)"] > 0]
    g2.dataframe(prog, hide_index=True, use_container_width=True, height=240)
    st.markdown("##### Caminos del servicio")
    if cam.empty:
        st.info("Este servicio no tiene filas en la hoja de caminos.")
    else:
        st.dataframe(cam[["orden", "codigo", "denom", "km", "revisar"]].rename(columns={"orden": "N°", "codigo": "Código", "denom": "Denominación",
                     "km": "Km", "revisar": "Revisar código"}), hide_index=True, use_container_width=True)


def render(libro, user, usr_key):
    _banner(TITULO)
    try:
        anios = anios_disponibles(libro)
    except Exception as e:
        st.error(f"No se pudo leer el archivo de Google Sheets: {e}")
        return
    if not anios:
        st.warning("No encontré hojas con nombre PIA_AAAA (por ejemplo PIA_2026). Importe la plantilla a su Google Sheets.")
        return
    c = st.columns([1, 3, 1.2], vertical_alignment="bottom")
    if st.session_state.get("m3_anio") not in anios:
        st.session_state["m3_anio"] = anios[0]
    anio = c[0].selectbox("PIA", anios, key="m3_anio", on_change=_m3)
    try:
        d, caminos, msgs, faltan, hora = cargar(libro, anio)
    except Exception as e:
        st.error(f"No se pudo leer la hoja PIA_{anio}: {e}")
        return
    if c[2].button("🔄 Actualizar datos", key="m3_act", use_container_width=True):
        cargar.clear()
        anios_disponibles.clear()
        _m3()
        st.rerun()
    if faltan:
        st.error("A la hoja PIA_%s le faltan columnas obligatorias: %s. No cambie los encabezados de la plantilla." % (anio, "; ".join(faltan)))
        return
    d = filtrar_usuario(d, user)
    if d.empty:
        st.info("No hay servicios para mostrar con su perfil.")
        return
    n_err, n_av = sum(1 for m in msgs if m[0] == "error"), sum(1 for m in msgs if m[0] == "aviso")
    n_cam_user = int(caminos["id"].isin(d["id"]).sum()) if not caminos.empty else 0
    c[1].caption(f"Datos leídos a las {hora} · {len(d)} servicios · {n_cam_user} caminos · "
                 f"{'🔴 ' + str(n_err) + ' errores · ' if n_err else ''}🟠 {n_av} avisos de control")
    vista = st.radio("Vista", ["Inicio", "Lista de caminos"], horizontal=True, key="m3_vista", label_visibility="collapsed", on_change=_m3)
    f = _filtros(d)
    if f.empty:
        st.info("No hay servicios con los filtros elegidos.")
        return
    ids = set(d["id"])
    msgs = [m for m in msgs if m[1] in ids]
    if vista == "Inicio":
        _vista_inicio(f, caminos, msgs, anio)
    else:
        _vista_lista(f, caminos, anio)
    st.caption("Próximas etapas: Mapa interactivo, Convenios y Comparativo.")
