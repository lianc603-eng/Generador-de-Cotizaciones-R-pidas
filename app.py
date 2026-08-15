import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import urllib.parse
import hashlib
import requests
import json
import os
import tempfile

# --- URL de Google Apps Script Webhook ---
API_URL = "https://script.google.com/macros/s/AKfycbywyo3MzZpjpgx7W98nsjAsKHinQoi8RumnKUKikCqyRjqLyPmJybxevmRriF0PDrtWWw/exec"

# --- Configuración de Página ---
st.set_page_config(page_title="Cotizador PyME Pro", page_icon="🏢", layout="wide")

COLUMNAS_BASE = ["Tipo", "Concepto", "Detalle", "Cantidad", "P. Unitario", "Importe"]
LIMITE_FREE_MENSUAL = 3
DIAS_PRUEBA_GRATIS = 3  # <-- 3 días de prueba gratis Pro

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# --- Funciones de Conexión con Google Sheets ---
def obtener_usuarios():
    try:
        res = requests.get(f"{API_URL}?action=get_users", timeout=15, allow_redirects=True)
        data = res.json()
        if isinstance(data, list) and len(data) > 1:
            headers = [str(h).strip().lower() for h in data[0]]
            return pd.DataFrame(data[1:], columns=headers)
        return pd.DataFrame(columns=["email", "password", "nombre_empresa", "telefono", "plan", "fecha_registro"])
    except Exception:
        return pd.DataFrame(columns=["email", "password", "nombre_empresa", "telefono", "plan", "fecha_registro"])

def registrar_usuario_api(email, password_hashed, nombre_empresa, telefono):
    try:
        payload = {
            "action": "register_user",
            "email": email,
            "password": password_hashed,
            "nombre_empresa": nombre_empresa,
            "telefono": telefono,
            "plan": "Trial",  # Inicia con prueba gratis Pro por 3 días
            "fecha_registro": datetime.date.today().strftime("%Y-%m-%d")
        }
        res = requests.post(
            API_URL, 
            data=json.dumps(payload), 
            headers={"Content-Type": "text/plain;charset=utf-8"}, 
            timeout=15, 
            allow_redirects=True
        )
        return "success" in res.text
    except Exception:
        return False

def obtener_cotizaciones():
    try:
        res = requests.get(f"{API_URL}?action=get_cotizaciones", timeout=15, allow_redirects=True)
        data = res.json()
        if isinstance(data, list) and len(data) > 1:
            headers = [str(h).strip() for h in data[0]]
            return pd.DataFrame(data[1:], columns=headers)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def guardar_cotizacion_api(data_dict):
    try:
        data_dict["action"] = "save_cotizacion"
        res = requests.post(
            API_URL, 
            data=json.dumps(data_dict), 
            headers={"Content-Type": "text/plain;charset=utf-8"}, 
            timeout=15, 
            allow_redirects=True
        )
        return "success" in res.text
    except Exception:
        return False

# --- Inicialización del Estado de Sesión ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = None
    st.session_state["datos_empresa"] = {}

if "items" not in st.session_state or not isinstance(st.session_state["items"], list):
    st.session_state["items"] = []

# --- Clase de Generación PDF con Hoja Membretada Personalizable ---
class PDFCotizacion(FPDF):
    def __init__(self, emisor_nombre, emisor_tel, es_pro=False, logo_path=None, color_rgb=(30, 41, 59), pie_personalizado=None, logo_align="Izquierda"):
        super().__init__()
        self.emisor_nombre = str(emisor_nombre) if emisor_nombre else "Empresa / Emisor"
        self.emisor_tel = str(emisor_tel) if emisor_tel else ""
        self.es_pro = es_pro
        self.logo_path = logo_path
        self.color_rgb = color_rgb
        self.pie_personalizado = pie_personalizado
        self.logo_align = logo_align

    def header(self):
        tiene_logo = self.es_pro and self.logo_path and os.path.exists(self.logo_path)
        
        if tiene_logo:
            try:
                if self.logo_align == "Derecha":
                    self.image(self.logo_path, x=165, y=10, w=25)
                    self.set_xy(10, 10)
                else:
                    self.image(self.logo_path, x=10, y=10, w=25)
                    self.set_xy(38, 10)
            except Exception:
                self.set_xy(10, 10)
        else:
            self.set_xy(10, 10)

        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*self.color_rgb)
        self.cell(0, 7, self.emisor_nombre.upper(), new_x="LMARGIN", new_y="NEXT", align="L")
        
        if tiene_logo and self.logo_align == "Izquierda":
            self.set_x(38)
            
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        if self.emisor_tel:
            self.cell(0, 5, f"Contacto / Tel: {self.emisor_tel}", new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(4)
        
        self.set_draw_color(*self.color_rgb)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_line_width(0.2)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        if self.es_pro and self.pie_personalizado:
            self.cell(0, 10, sanitizar_texto(self.pie_personalizado), align="C")
        elif not self.es_pro:
            self.cell(0, 10, "Documento sin validez fiscal directa - Generado con Cotizador PyME Free", align="C")
        else:
            self.cell(0, 10, "Documento oficial de cotización - Gracias por su preferencia", align="C")

def sanitizar_texto(texto):
    if not texto:
        return ""
    reemplazos = {"–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "*"}
    for orig, rep in reemplazos.items():
        texto = texto.replace(orig, rep)
    return str(texto).encode("latin-1", "replace").decode("latin-1")

def hex_a_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (30, 41, 59)

def generar_pdf(empresa, emisor_tel, cliente, cliente_tel, items_df, total, vigencia, notas, es_pro=False, logo_path=None, color_hex="#1e293b", pie_custom="", logo_align="Izquierda"):
    color_rgb = hex_a_rgb(color_hex)
    pdf = PDFCotizacion(empresa, emisor_tel, es_pro, logo_path, color_rgb, pie_custom, logo_align)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*color_rgb)
    pdf.cell(110, 6, sanitizar_texto(f"CLIENTE: {cliente}"))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(80, 6, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT", align="R")
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(110, 5, sanitizar_texto(f"Tel: {cliente_tel}"))
    pdf.cell(80, 5, f"Válido por: {vigencia} días", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(5)

    # Cabecera de la Tabla
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_text_color(*color_rgb)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(105, 7, "  Descripción / Detalle", border=1, fill=True)
    pdf.cell(25, 7, "Tipo / Cant.", border=1, align="C", fill=True)
    pdf.cell(30, 7, "P. Unitario", border=1, align="R", fill=True)
    pdf.cell(30, 7, "Subtotal", border=1, align="R", fill=True)
    pdf.ln()

    # Filas
    for _, row in items_df.iterrows():
        concepto = sanitizar_texto(str(row["Concepto"]))
        tipo_unidad = sanitizar_texto(f"{row['Tipo']} ({row['Cantidad']:.2f})")
        p_unit = f"${float(row['P. Unitario']):,.2f}"
        subtotal = f"${float(row['Importe']):,.2f}"
        detalle = sanitizar_texto(str(row.get("Detalle", "")).strip())

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(105, 6, f" {concepto}", border="LTR")
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(25, 6, tipo_unidad, border="LTR", align="C")
        pdf.cell(30, 6, p_unit, border="LTR", align="R")
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(30, 6, subtotal, border="LTR", align="R")
        pdf.ln()

        if detalle and detalle != "nan":
            pdf.set_font("Helvetica", "I", 7.5)
            pdf.set_text_color(100, 116, 139)
            y_start = pdf.get_y()
            pdf.set_x(10)
            pdf.multi_cell(105, 4, f"   Incluye: {detalle}", border="LBR")
            y_end = pdf.get_y()
            h_extra = y_end - y_start
            pdf.set_xy(115, y_start)
            pdf.cell(25, h_extra, "", border="LBR")
            pdf.cell(30, h_extra, "", border="LBR")
            pdf.cell(30, h_extra, "", border="LBR")
            pdf.ln()
        else:
            pdf.set_x(10)
            pdf.cell(105, 1, "", border="LBR")
            pdf.cell(25, 1, "", border="LBR")
            pdf.cell(30, 1, "", border="LBR")
            pdf.cell(30, 1, "", border="LBR")
            pdf.ln()

    # Total
    pdf.set_fill_color(248, 250, 252)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*color_rgb)
    pdf.cell(160, 8, "TOTAL: ", border=1, align="R", fill=True)
    pdf.cell(30, 8, f"${total:,.2f}", border=1, align="R", fill=True)
    pdf.ln(8)

    if notas:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, "Notas y Condiciones de Pago:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 4, sanitizar_texto(str(notas)))

    return bytes(pdf.output())

def link_google_calendar(titulo, descripcion, fecha_seguimiento):
    f_str = fecha_seguimiento.strftime("%Y%m%d")
    fechas = f"{f_str}T150000Z/{f_str}T160000Z"
    params = {"action": "TEMPLATE", "text": titulo, "details": descripcion, "dates": fechas}
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

# ==============================================================================
# VISTA: ACCESO Y REGISTRO
# ==============================================================================
if not st.session_state["autenticado"]:
    st.title("🔒 Portal de Cotizaciones PyME")
    st.caption(f"Inicia sesión o crea tu cuenta para disfrutar de **{DIAS_PRUEBA_GRATIS} días de prueba gratis Pro** sin compromiso.")

    tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", f"🎁 Registrar mi Negocio ({DIAS_PRUEBA_GRATIS} Días Gratis)"])

    with tab_login:
        with st.form("form_login"):
            correo_login = st.text_input("Correo Electrónico").strip().lower()
            pass_login = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Ingresar", use_container_width=True)

            if btn_login:
                if not correo_login or not pass_login:
                    st.error("Por favor completa todos los campos.")
                else:
                    df_users = obtener_usuarios()
                    if not df_users.empty and "email" in df_users.columns:
                        pass_hashed = hash_password(pass_login)
                        usuario_match = df_users[(df_users["email"].str.lower() == correo_login) & (df_users["password"] == pass_hashed)]
                        
                        if not usuario_match.empty:
                            user_row = usuario_match.iloc[0]
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = correo_login
                            st.session_state["datos_empresa"] = {
                                "nombre": str(user_row.get("nombre_empresa", "Mi Negocio")),
                                "telefono": str(user_row.get("telefono", "")),
                                "plan": str(user_row.get("plan", "Trial")),
                                "fecha_registro": str(user_row.get("fecha_registro", datetime.date.today().strftime("%Y-%m-%d")))
                            }
                            st.success("¡Bienvenido!")
                            st.rerun()
                        else:
                            st.error("Correo o contraseña incorrectos.")
                    else:
                        st.warning("No hay usuarios registrados aún. Crea tu cuenta en la pestaña de registro.")

    with tab_registro:
        with st.form("form_reg"):
            reg_empresa = st.text_input("Nombre de tu Negocio / Marca")
            reg_tel = st.text_input("Teléfono de Contacto (10 dígitos)")
            reg_email = st.text_input("Correo Electrónico (será tu usuario)").strip().lower()
            reg_pass = st.text_input("Crear Contraseña", type="password")
            btn_reg = st.form_submit_button(f"🎁 Comenzar mis {DIAS_PRUEBA_GRATIS} Días de Prueba Gratis", use_container_width=True)

            if btn_reg:
                if not reg_email or not reg_pass or not reg_empresa:
                    st.error("Todos los campos obligatorios deben completarse.")
                else:
                    df_users = obtener_usuarios()
                    if not df_users.empty and "email" in df_users.columns and reg_email in df_users["email"].str.lower().values:
                        st.warning("Este correo ya se encuentra registrado. Inicia sesión.")
                    else:
                        ok = registrar_usuario_api(reg_email, hash_password(reg_pass), reg_empresa.strip(), reg_tel.strip())
                        if ok:
                            st.success(f"¡Negocio registrado con éxito con tu Prueba Pro de {DIAS_PRUEBA_GRATIS} días! Ya puedes iniciar sesión.")
                        else:
                            st.error("Hubo un error al registrar en la base de datos.")

# ==============================================================================
# VISTA: PANEL PRIVADO DEL USUARIO
# ==============================================================================
else:
    user_email = st.session_state["usuario_actual"]
    empresa_data = st.session_state["datos_empresa"]
    
    # Lógica de Evaluación de Plan y Prueba de 3 días
    plan_raw = str(empresa_data.get("plan", "Trial")).strip().upper()
    fecha_reg_str = empresa_data.get("fecha_registro", datetime.date.today().strftime("%Y-%m-%d"))
    
    try:
        fecha_reg = datetime.datetime.strptime(str(fecha_reg_str)[:10], "%Y-%m-%d").date()
    except Exception:
        fecha_reg = datetime.date.today()

    dias_transcurridos = (datetime.date.today() - fecha_reg).days
    dias_restantes_trial = max(0, DIAS_PRUEBA_GRATIS - dias_transcurridos)

    es_pro = False
    estado_plan_texto = ""

    if plan_raw == "PRO":
        es_pro = True
        estado_plan_texto = "⭐ Plan PRO Activo (Ilimitado)"
    elif plan_raw == "TRIAL" and dias_restantes_trial > 0:
        es_pro = True
        estado_plan_texto = f"🎁 Prueba Pro ({dias_restantes_trial} días restantes)"
    else:
        es_pro = False
        estado_plan_texto = "🏷️ Plan FREE"

    # Consumo del mes actual
    df_todas = obtener_cotizaciones()
    df_mis_cotizaciones = pd.DataFrame()
    cotizaciones_mes_actual = 0
    mes_actual_str = datetime.date.today().strftime("%Y-%m")

    if not df_todas.empty and "id_empresa" in df_todas.columns:
        df_mis_cotizaciones = df_todas[df_todas["id_empresa"].str.lower() == user_email.lower()]
        if not df_mis_cotizaciones.empty and "Fecha" in df_mis_cotizaciones.columns:
            cotizaciones_mes_actual = len(df_mis_cotizaciones[df_mis_cotizaciones["Fecha"].astype(str).str.startswith(mes_actual_str)])

    # Barra lateral
    with st.sidebar:
        st.markdown(f"### 🏢 **{empresa_data.get('nombre', 'Mi Empresa')}**")
        st.caption(f"👤 Usuario: {user_email}")
        
        if es_pro:
            st.success(f"**{estado_plan_texto}**")
        else:
            st.info(f"**{estado_plan_texto}** ({cotizaciones_mes_actual} / {LIMITE_FREE_MENSUAL} este mes)")
            if cotizaciones_mes_actual >= LIMITE_FREE_MENSUAL:
                st.warning("⚠️ Límite mensual alcanzado")
            
        st.divider()
        menu = st.radio("Secciones", ["📝 Nueva Cotización", "🎨 Diseñar Hoja Membretada", "📊 Mis Cotizaciones", "⭐ Plan Pro"])
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["usuario_actual"] = None
            st.session_state["datos_empresa"] = {}
            st.session_state["items"] = []
            st.rerun()

    # --- PANTALLA 1: NUEVA COTIZACIÓN ---
    if menu == "📝 Nueva Cotización":
        st.title("📄 Generar Cotización")

        # Bloqueo si es Free y consumió sus 3 del mes
        if not es_pro and cotizaciones_mes_actual >= LIMITE_FREE_MENSUAL:
            st.error(f"🚫 **Has alcanzado el límite de {LIMITE_FREE_MENSUAL} cotizaciones gratuitas de este mes.**")
            st.info(f"Tus {DIAS_PRUEBA_GRATIS} días de prueba gratuita han concluido. Para seguir cotizando de manera ilimitada y conservar tu membrete personalizado, actualiza al Plan Pro.")
            st.divider()
            col_b1, col_b2 = st.columns([1, 2])
            with col_b1:
                st.metric("Consumo mensual", f"{cotizaciones_mes_actual} / {LIMITE_FREE_MENSUAL}")
            with col_b2:
                st.write("### Beneficios Plan Pro:")
                st.markdown("- Cotizaciones Ilimitadas\n- Hoja Membretada con Colores y Logotipo\n- Sin marcas de agua en tus PDFs")
            st.stop()

        col_emisor, col_cliente = st.columns(2)
        with col_emisor:
            st.subheader("🏢 Datos de tu Empresa")
            mi_empresa = st.text_input("Nombre del Negocio", value=empresa_data.get("nombre", ""))
            mi_telefono = st.text_input("Teléfono del Negocio", value=empresa_data.get("telefono", ""))

        with col_cliente:
            st.subheader("👤 Datos del Cliente")
            cliente_nombre = st.text_input("Nombre del Cliente o Empresa", placeholder="Ej. Juan Pérez")
            cliente_telefono = st.text_input("Teléfono del Cliente (10 dígitos)", placeholder="Ej. 9811064023")

        st.divider()

        st.subheader("➕ Agregar a la Cotización")
        tab_servicio, tab_producto = st.tabs(["💼 Servicios", "📦 Productos"])

        with tab_servicio:
            with st.form("form_serv", clear_on_submit=True):
                col_s1, col_s2, col_s3, col_s4 = st.columns([3, 1.2, 1.2, 1])
                with col_s1:
                    serv_nombre = st.text_input("Nombre del Servicio", placeholder="Ej. Cobertura de Evento / Mantenimiento")
                with col_s2:
                    serv_unidad = st.selectbox("Unidad", ["Servicio", "Hora", "Proyecto", "Mes", "Evento", "Sesión"])
                with col_s3:
                    serv_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
                with col_s4:
                    serv_precio = st.number_input("Precio ($)", min_value=0.0, value=0.0, step=100.0)
                
                serv_detalle = st.text_area("¿Qué incluye este servicio? (Opcional)", placeholder="Ej. Entregables, horas de trabajo o especificaciones.")
                if st.form_submit_button("➕ Agregar Servicio", use_container_width=True):
                    if serv_nombre.strip():
                        st.session_state["items"].append({
                            "Tipo": str(serv_unidad), "Concepto": serv_nombre.strip(),
                            "Detalle": serv_detalle.strip(), "Cantidad": float(serv_cant),
                            "P. Unitario": float(serv_precio), "Importe": float(serv_cant * serv_precio)
                        })
                        st.rerun()

        with tab_producto:
            with st.form("form_prod", clear_on_submit=True):
                col_p1, col_p2, col_p3, col_p4 = st.columns([3, 1.2, 1.2, 1])
                with col_p1:
                    prod_nombre = st.text_input("Nombre del Producto", placeholder="Ej. Cuadro Canvas / Kit de Insumos")
                with col_p2:
                    prod_unidad = st.selectbox("Presentación", ["Pieza", "Kit", "Paquete", "Caja", "Metro", "Lote"])
                with col_p3:
                    prod_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
                with col_p4:
                    prod_precio = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=50.0)
                
                prod_detalle = st.text_area("Especificaciones del producto (Opcional)", placeholder="Ej. Materiales, dimensiones o acabados.")
                if st.form_submit_button("➕ Agregar Producto", use_container_width=True):
                    if prod_nombre.strip():
                        st.session_state["items"].append({
                            "Tipo": str(prod_unidad), "Concepto": prod_nombre.strip(),
                            "Detalle": prod_detalle.strip(), "Cantidad": float(prod_cant),
                            "P. Unitario": float(prod_precio), "Importe": float(prod_cant * prod_precio)
                        })
                        st.rerun()

        st.divider()

        lista_actual = st.session_state.get("items", [])
        items_normalizados = []
        if isinstance(lista_actual, list):
            for it in lista_actual:
                if isinstance(it, dict):
                    items_normalizados.append({
                        "Tipo": it.get("Tipo", "Servicio"), "Concepto": it.get("Concepto", ""),
                        "Detalle": it.get("Detalle", ""), "Cantidad": float(it.get("Cantidad", 1.0)),
                        "P. Unitario": float(it.get("P. Unitario", 0.0)), "Importe": float(it.get("Importe", 0.0))
                    })

        if len(items_normalizados) > 0:
            st.subheader("📋 Resumen de la Cotización")
            df_items = pd.DataFrame(items_normalizados)
            st.dataframe(df_items[COLUMNAS_BASE], use_container_width=True, hide_index=True)
            total_cotizacion = float(df_items["Importe"].sum())
            st.metric(label="Total a Cobrar", value=f"${total_cotizacion:,.2f} MXN")

            if st.button("🗑️ Limpiar lista de cotización"):
                st.session_state["items"] = []
                st.rerun()
        else:
            df_items = pd.DataFrame(columns=COLUMNAS_BASE)
            total_cotizacion = 0.0
            st.info("Aún no has agregado servicios o productos a la cotización.")

        st.divider()

        col_opt, col_actions = st.columns([1, 1])

        with col_opt:
            vigencia_dias = st.slider("Días de vigencia", 1, 30, 7)
            fecha_seg = st.date_input("Fecha para seguimiento / llamada", value=datetime.date.today() + datetime.timedelta(days=2))
            notas_adicionales = st.text_area("Condiciones de entrega y pago", value="Anticipo del 50% para inicio y 50% al entregar.")

        with col_actions:
            st.subheader("🚀 Acciones Rápidas")
            if not df_items.empty and cliente_nombre and cliente_nombre.strip():
                cfg_color = st.session_state.get("cfg_color", "#1e293b")
                cfg_pie = st.session_state.get("cfg_pie", "")
                cfg_align = st.session_state.get("cfg_align", "Izquierda")
                cfg_logo_path = st.session_state.get("cfg_logo_path", None)

                pdf_bytes = generar_pdf(
                    mi_empresa if mi_empresa.strip() else "Mi Empresa", 
                    mi_telefono, cliente_nombre, cliente_telefono, 
                    df_items, total_cotizacion, vigencia_dias, notas_adicionales,
                    es_pro=es_pro, logo_path=cfg_logo_path,
                    color_hex=cfg_color, pie_custom=cfg_pie, logo_align=cfg_align
                )
                
                st.download_button(
                    label="📥 Descargar Cotización en PDF",
                    data=pdf_bytes,
                    file_name=f"Cotizacion_{cliente_nombre.strip().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                # WhatsApp
                resumen_lineas = [f"• *{it['Concepto']}* ({it['Cantidad']:.0f} {it['Tipo']}) -> ${it['Importe']:,.2f}" for _, it in df_items.iterrows()]
                mensaje_wa = (
                    f"Hola *{cliente_nombre.strip()}*, te comparto el resumen de tu cotización con *{mi_empresa or 'nosotros'}*:\n\n"
                    f"{chr(10).join(resumen_lineas)}\n\n"
                    f"💰 *TOTAL:* ${total_cotizacion:,.2f} MXN\n⏳ *Vigencia:* {vigencia_dias} días.\n\n"
                    f"Quedo a tu disposición si deseas confirmar o realizar algún ajuste."
                )
                tel_formateado = "".join(filter(str.isdigit, cliente_telefono))
                wa_url = f"https://wa.me/{tel_formateado}?text={urllib.parse.quote(mensaje_wa)}"
                st.link_button("📲 Enviar Resumen por WhatsApp", wa_url, use_container_width=True)

                # Google Calendar
                cal_desc = f"Seguimiento de cotización enviada por ${total_cotizacion:,.2f} MXN. Tel: {cliente_telefono}"
                cal_url = link_google_calendar(f"Llamar a {cliente_nombre} (Seguimiento Cotización)", cal_desc, fecha_seg)
                st.link_button("📅 Agendar en Google Calendar", cal_url, use_container_width=True)

                # Guardado
                if st.button("💾 Guardar en mi Historial", use_container_width=True):
                    folio = f"COT-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
                    datos_a_guardar = {
                        "id_empresa": user_email,
                        "Folio": folio,
                        "Fecha": datetime.date.today().strftime("%Y-%m-%d"),
                        "Cliente": cliente_nombre.strip(),
                        "Telefono": cliente_telefono.strip(),
                        "Total": total_cotizacion,
                        "Conceptos": " | ".join([f"{it['Concepto']} ({it['Cantidad']})" for _, it in df_items.iterrows()]),
                        "Vigencia_Dias": vigencia_dias,
                        "Fecha_Seguimiento": fecha_seg.strftime("%Y-%m-%d"),
                        "Estatus": "Pendiente",
                        "Notas": notas_adicionales.strip()
                    }
                    guardado = guardar_cotizacion_api(datos_a_guardar)
                    if guardado:
                        st.success(f"✅ Cotización guardada con Folio {folio}")
                    else:
                        st.error("Error al guardar la cotización.")
            else:
                st.caption("Ingresa el nombre del cliente y al menos un concepto para habilitar la descarga del PDF y WhatsApp.")

    # --- PANTALLA 2: PERSONALIZADOR DE HOJA MEMBRETADA ---
    elif menu == "🎨 Diseñar Hoja Membretada":
        st.title("🎨 Personaliza tu Hoja Membretada y PDF")
        st.caption(f"Configura la identidad visual de tu marca. Disponible en Plan Pro y durante tus {DIAS_PRUEBA_GRATIS} días de prueba gratis.")

        if not es_pro:
            st.warning(f"🔒 Esta sección está disponible en el **Plan Pro** y durante los **{DIAS_PRUEBA_GRATIS} días de prueba gratis**.")
        
        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.subheader("1. Identidad de Marca")
            paletas = {
                "Azul Ejecutivo": "#1e3a8a",
                "Verde Esmeralda / Bosque": "#065f46",
                "Vino / Borgoña": "#831843",
                "Gris Grafito / Carbón": "#1e293b",
                "Dorado Elegante": "#b45309",
                "Personalizado": "#1e293b"
            }
            eleccion_paleta = st.selectbox("Paleta de Color Principal", list(paletas.keys()))
            if eleccion_paleta == "Personalizado":
                color_seleccionado = st.color_picker("Elige tu color hexadecimal", value="#1e293b")
            else:
                color_seleccionado = paletas[eleccion_paleta]
            
            st.session_state["cfg_color"] = color_seleccionado

            st.write("---")
            st.subheader("2. Logotipo Oficial")
            logo_subido = st.file_uploader("Subir Logo (PNG sin fondo recomendado)", type=["png", "jpg", "jpeg"])
            if logo_subido:
                temp_dir = tempfile.gettempdir()
                path_logo = os.path.join(temp_dir, f"logo_{user_email.replace('@','_')}.png")
                with open(path_logo, "wb") as f:
                    f.write(logo_subido.getbuffer())
                st.session_state["cfg_logo_path"] = path_logo
                st.success("✅ Logotipo cargado correctamente.")
            
            pos_logo = st.radio("Alineación del Logotipo", ["Izquierda", "Derecha"], horizontal=True)
            st.session_state["cfg_align"] = pos_logo

        with col_d2:
            st.subheader("3. Pie de Página y Textos Legales")
            pie_texto = st.text_area(
                "Texto personalizado al pie del documento", 
                value=st.session_state.get("cfg_pie", "Gracias por su preferencia - Documento emitido para fines presupuestarios."),
                placeholder="Ej. Precios sujetos a cambio sin previo aviso. / R.F.C. y Cuentas de Transferencia..."
            )
            st.session_state["cfg_pie"] = pie_texto

            st.write("---")
            st.subheader("👁️ Vista Previa de tu Hoja Membretada")
            st.markdown(
                f"""
                <div style="border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; background-color: #ffffff; color: #1e293b;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid {color_seleccionado}; padding-bottom: 10px;">
                        <div>
                            <h3 style="margin: 0; color: {color_seleccionado};">{empresa_data.get('nombre', 'MI EMPRESA').upper()}</h3>
                            <small style="color: #64748b;">Contacto: {empresa_data.get('telefono', '9811234567')}</small>
                        </div>
                        <span style="background-color: #f1f5f9; padding: 6px 12px; border-radius: 4px; font-weight: bold; color: {color_seleccionado};">COTIZACIÓN</span>
                    </div>
                    <div style="margin-top: 15px; font-size: 13px; color: #475569;">
                        <b>Cliente:</b> Ejemplo de Cliente S.A.<br>
                        <b>Detalle:</b> Servicios profesionales con tu paleta de color oficial.
                    </div>
                    <div style="margin-top: 25px; border-top: 1px dashed #cbd5e1; padding-top: 8px; text-align: center; font-size: 11px; color: #94a3b8;">
                        {pie_texto}
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )

        st.success("✅ Cambios de diseño guardados para tus próximas cotizaciones.")

    # --- PANTALLA 3: HISTORIAL PRIVADO ---
    elif menu == "📊 Mis Cotizaciones":
        st.title(f"📊 Historial de Cotizaciones - {empresa_data.get('nombre', 'Mi Empresa')}")
        
        if not df_mis_cotizaciones.empty:
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            with col_kpi1:
                total_sum = pd.to_numeric(df_mis_cotizaciones['Total'], errors='coerce').sum()
                st.metric("Total Cotizado", f"${total_sum:,.2f} MXN")
            with col_kpi2:
                st.metric("Cotizaciones Totales", len(df_mis_cotizaciones))
            with col_kpi3:
                pendientes = len(df_mis_cotizaciones[df_mis_cotizaciones["Estatus"] == "Pendiente"])
                st.metric("Cotizaciones Pendientes", pendientes)

            st.subheader("Listado de Cotizaciones")
            cols_mostrar = ["Folio", "Fecha", "Cliente", "Telefono", "Total", "Conceptos", "Fecha_Seguimiento", "Estatus"]
            st.dataframe(df_mis_cotizaciones[cols_mostrar], use_container_width=True, hide_index=True)
        else:
            st.info("Aún no tienes cotizaciones guardadas en tu cuenta.")

    # --- PANTALLA 4: PLAN PRO ---
    elif menu == "⭐ Plan Pro":
        st.title("⭐ Potencia tu Negocio con el Plan Pro")
        st.write("Elimina límites y proyecta una imagen 100% corporativa ante tus clientes.")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown(f"""
            ### 🟢 Plan Free (Después de {DIAS_PRUEBA_GRATIS} días)
            - Hasta **{LIMITE_FREE_MENSUAL} cotizaciones al mes**
            - Marca de agua genérica en PDF
            - Soporte estándar
            """)
        with col_c2:
            st.markdown("""
            ### ⭐ Plan Pro ($149 MXN / mes)
            - **Cotizaciones Ilimitadas**
            - **Hoja Membretada Personalizada** con Colores y Logotipo
            - **Textos Legales y Pie de Página propio**
            - **Sin marcas de agua**
            - Agendado de seguimiento en Google Calendar
            - Historial en la nube
            """)

        st.divider()
        st.info("💡 Para activar tu suscripción Pro permanente, contáctanos directamente.")
        wa_upgrade = f"https://wa.me/529817360428?text=Hola,%20quiero%20activar%20mi%20suscripción%20Pro%20en%20Cotizador%20PyME%20para%20la%20cuenta%20{user_email}"
        st.link_button("📲 Activar Plan Pro por WhatsApp", wa_upgrade, use_container_width=True)
