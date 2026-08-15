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

# --- Configuración y Constantes Globales ---
API_URL = "https://script.google.com/macros/s/AKfycbywyo3MzZpjpgx7W98nsjAsKHinQoi8RumnKUKikCqyRjqLyPmJybxevmRriF0PDrtWWw/exec"
URL_APP_PUBLICA = "https://generador-de-cotizaciones-r-pidas-ajlywaajuxc8kydphbmg23.streamlit.app"
ADMIN_EMAIL = "lianc603@gmail.com"

st.set_page_config(page_title="Cotizador PyME Pro Master", page_icon="🏢", layout="wide")

COLUMNAS_BASE = ["Tipo", "Concepto", "Detalle", "Cantidad", "P. Unitario", "Importe"]
LIMITE_FREE_MENSUAL = 3
DIAS_PRUEBA_GRATIS = 3
MAX_NEGOCIOS_PRO_ESTANDAR = 3
PRECIO_PRO_MENSUAL = 199

LISTA_BANCOS_MX = [
    "ACTINVER", "AFIRME", "albo", "ARCUS FI", "ASP INTEGRA OPC", "AZTECA", "BaBien", 
    "BAJIO", "BANAMEX", "BANCO COVALTO", "BANCOMEXT", "BANCOPPEL", "BANCO S3", 
    "BANCREA", "BANJERCITO", "BANKAOOL", "BANK OF AMERICA", "BANK OF CHINA", 
    "BANOBRAS", "BANORTE", "BANREGIO", "BANSI", "BANXICO", "BARCLAYS", "BBASE", 
    "BBVA MEXICO", "BMONEX", "CAJA POP MEXICA", "CAJA TELEFONIST", "CASHI CUENTA", 
    "CITI MEXICO", "Clip", "CLS", "CoDi Valida", "COMPARTAMOS", "CONSUBANCO", 
    "COOPDESARROLLO", "CREDICAPITAL", "CREDICLUB", "CRISTOBAL COLON", "Cuenca", 
    "Dep y Pag Dig", "DONDE", "FINAMEX", "FINCOMUN", "FINCO PAY", "FINTOC", 
    "FONDEADORA", "FONDO (FIRA)", "GBM", "HEY BANCO", "HIPOTECARIA FED", "HSBC", 
    "ICBC", "INBURSA", "INDEVAL", "INMOBILIARIO", "INTERCAM BANCO", "INVEX", 
    "JP MORGAN", "KAPITAL", "KLAR", "KUSPIT", "LIBERTAD", "MASARI", "Mercado Pago W", 
    "MexPago", "MIFEL", "MIZUHO BANK", "MONEXCB", "MUFG", "MULTIVA BANCO", "NAFIN", 
    "NUBANK", "NVIO", "PAGATODO", "Peibo", "PPBALANCEMX", "PROFUTURO", "SABADELL", 
    "SANTANDER", "SCOTIABANK", "SHINHAN", "SPIN BY OXXO", "STP", "TESORED", 
    "TRANSFER", "TRANSFER DIRECT", "TRF", "UALA", "UNAGRA", "VALMEX", "VALUE", 
    "VE POR MAS", "VOLKSWAGEN"
]

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# --- Funciones de Comunicación con Google Sheets ---
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

def obtener_negocios_usuario(user_email):
    try:
        res = requests.get(f"{API_URL}?action=get_negocios", timeout=15, allow_redirects=True)
        data = res.json()
        if isinstance(data, list) and len(data) > 1:
            headers = [str(h).strip() for h in data[0]]
            df = pd.DataFrame(data[1:], columns=headers)
            if "id_usuario" in df.columns:
                return df[df["id_usuario"].str.lower() == user_email.lower()]
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def agregar_nuevo_negocio_api(id_usuario, nombre_negocio, telefono):
    try:
        payload = {
            "action": "add_negocio", "id_usuario": id_usuario,
            "nombre_negocio": nombre_negocio, "telefono": telefono,
            "color": "#831843", "banco": "", "clabe": "", "titular": nombre_negocio,
            "pie_pdf": "Gracias por su preferencia."
        }
        res = requests.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
        return "success" in res.text
    except Exception:
        return False

def guardar_config_negocio_api(id_usuario, nombre_negocio, telefono, color, banco, clabe, titular, pie_pdf):
    try:
        payload = {
            "action": "update_negocio_config", "id_usuario": id_usuario,
            "nombre_negocio": nombre_negocio, "telefono": telefono,
            "color": color, "banco": banco, "clabe": clabe, "titular": titular, "pie_pdf": pie_pdf
        }
        res = requests.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
        return "success" in res.text
    except Exception:
        return False

def registrar_usuario_api(email, password_hashed, nombre_empresa, telefono):
    try:
        payload = {
            "action": "register_user", "email": email, "password": password_hashed,
            "nombre_empresa": nombre_empresa, "telefono": telefono, "plan": "Trial",
            "fecha_registro": datetime.date.today().strftime("%Y-%m-%d")
        }
        res = requests.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
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
        res = requests.post(API_URL, data=json.dumps(data_dict), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
        return "success" in res.text
    except Exception:
        return False

def actualizar_estatus_api(folio, id_empresa, nuevo_estatus):
    try:
        payload = {"action": "update_estatus", "folio": folio, "id_empresa": id_empresa, "nuevo_estatus": nuevo_estatus}
        res = requests.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
        return "success" in res.text
    except Exception:
        return False

def obtener_catalogo_api():
    try:
        res = requests.get(f"{API_URL}?action=get_catalogo", timeout=15, allow_redirects=True)
        data = res.json()
        if isinstance(data, list) and len(data) > 1:
            headers = [str(h).strip() for h in data[0]]
            return pd.DataFrame(data[1:], columns=headers)
        return pd.DataFrame(columns=["id_empresa", "id_negocio", "Tipo", "Nombre", "Unidad", "Precio", "Detalle"])
    except Exception:
        return pd.DataFrame(columns=["id_empresa", "id_negocio", "Tipo", "Nombre", "Unidad", "Precio", "Detalle"])

def guardar_item_catalogo_api(id_empresa, id_negocio, tipo, nombre, unidad, precio, detalle):
    try:
        payload = {
            "action": "save_item_catalogo", "id_empresa": id_empresa, "id_negocio": id_negocio,
            "Tipo": tipo, "Nombre": nombre, "Unidad": unidad, "Precio": precio, "Detalle": detalle
        }
        res = requests.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
        return "success" in res.text
    except Exception:
        return False

def eliminar_item_catalogo_api(id_empresa, id_negocio, nombre):
    try:
        payload = {"action": "delete_item_catalogo", "id_empresa": id_empresa, "id_negocio": id_negocio, "nombre": nombre}
        res = requests.post(API_URL, data=json.dumps(payload), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=15, allow_redirects=True)
        return "success" in res.text
    except Exception:
        return False

# --- Inicialización del Estado ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = None
    st.session_state["datos_empresa"] = {}
    st.session_state["negocio_activo"] = None

if "items" not in st.session_state or not isinstance(st.session_state["items"], list):
    st.session_state["items"] = []

# --- Clase de Generación PDF Multiestilo Profesional ---
class PDFCotizacion(FPDF):
    def __init__(self, emisor_nombre, emisor_tel, es_pro=False, logo_path=None, color_rgb=(30, 41, 59), pie_personalizado=None, logo_align="Izquierda", datos_banco=None, firma_path=None, estilo_plantilla="Ejecutiva"):
        super().__init__()
        self.emisor_nombre = str(emisor_nombre) if emisor_nombre else "Empresa / Emisor"
        self.emisor_tel = str(emisor_tel) if emisor_tel else ""
        self.es_pro = es_pro
        self.logo_path = logo_path
        self.color_rgb = color_rgb
        self.pie_personalizado = pie_personalizado
        self.logo_align = logo_align
        self.datos_banco = datos_banco
        self.firma_path = firma_path
        self.estilo_plantilla = estilo_plantilla

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
        self.set_line_width(0.8 if self.estilo_plantilla == "Moderna" else 0.4)
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
    hex_str = str(hex_str).lstrip("#")
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (30, 41, 59)

def generar_pdf(empresa, emisor_tel, cliente, cliente_tel, items_df, subtotal, descuento_monto, iva_monto, total, vigencia, notas, es_pro=False, logo_path=None, color_hex="#831843", pie_custom="", logo_align="Izquierda", datos_banco="", qr_path=None, firma_path=None, plantilla="Ejecutiva", etiqueta_iva=""):
    color_rgb = hex_a_rgb(color_hex)
    pdf = PDFCotizacion(empresa, emisor_tel, es_pro, logo_path, color_rgb, pie_custom, logo_align, datos_banco, firma_path, plantilla)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado Cliente
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

    # Cabecera de Tabla
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_text_color(*color_rgb)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(105, 7, "  Descripción / Detalle", border=1, fill=True)
    pdf.cell(25, 7, "Tipo / Cant.", border=1, align="C", fill=True)
    pdf.cell(30, 7, "P. Unitario", border=1, align="R", fill=True)
    pdf.cell(30, 7, "Subtotal", border=1, align="R", fill=True)
    pdf.ln()

    for _, row in items_df.iterrows():
        concepto = sanitizar_texto(str(row["Concepto"]))
        tipo_unidad = sanitizar_texto(f"{row['Tipo']} ({row['Cantidad']:.2f})")
        p_unit = f"${float(row['P. Unitario']):,.2f}"
        subtotal_row = f"${float(row['Importe']):,.2f}"
        detalle = sanitizar_texto(str(row.get("Detalle", "")).strip())

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(105, 6, f" {concepto}", border="LTR")
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(25, 6, tipo_unidad, border="LTR", align="C")
        pdf.cell(30, 6, p_unit, border="LTR", align="R")
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(30, 6, subtotal_row, border="LTR", align="R")
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

    # Totales Desglosados
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(71, 85, 105)
    
    if descuento_monto > 0 or "IVA" in etiqueta_iva:
        pdf.cell(160, 5, "Subtotal: ", border=0, align="R")
        pdf.cell(30, 5, f"${subtotal:,.2f}", border=0, align="R")
        pdf.ln()
        
        if descuento_monto > 0:
            pdf.cell(160, 5, "Descuento Comercial: ", border=0, align="R")
            pdf.cell(30, 5, f"-${descuento_monto:,.2f}", border=0, align="R")
            pdf.ln()
            
        if "IVA Incluido" in etiqueta_iva:
            pdf.cell(160, 5, "I.V.A. Trasladado 16% (Incluido): ", border=0, align="R")
            pdf.cell(30, 5, f"${iva_monto:,.2f}", border=0, align="R")
            pdf.ln()
        elif iva_monto > 0:
            pdf.cell(160, 5, f"I.V.A. ({etiqueta_iva}): ", border=0, align="R")
            pdf.cell(30, 5, f"+${iva_monto:,.2f}", border=0, align="R")
            pdf.ln()

    pdf.set_fill_color(248, 250, 252)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*color_rgb)
    pdf.cell(160, 8, "TOTAL A LIQUIDAR: ", border=1, align="R", fill=True)
    pdf.cell(30, 8, f"${total:,.2f}", border=1, align="R", fill=True)
    pdf.ln(7)

    if notas:
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(0, 4, "Notas y Condiciones de Entrega:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 3.8, sanitizar_texto(str(notas)))
        pdf.ln(4)

    if es_pro and (datos_banco or firma_path):
        y_bloque = pdf.get_y()
        if y_bloque > 230:
            pdf.add_page()
            y_bloque = pdf.get_y()

        if datos_banco:
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(10, y_bloque, 125, 28, "DF")
            
            pdf.set_xy(13, y_bloque + 2)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*color_rgb)
            pdf.cell(85, 4, "INFORMACIÓN PARA PAGO / SPEI:", ln=True)
            
            pdf.set_x(13)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(85, 3.5, sanitizar_texto(datos_banco))
            
            if qr_path and os.path.exists(qr_path):
                try:
                    pdf.image(qr_path, x=105, y=y_bloque + 2, w=24)
                except Exception:
                    pass

        if firma_path and os.path.exists(firma_path):
            try:
                pdf.image(firma_path, x=150, y=y_bloque + 1, w=35)
                pdf.set_xy(145, y_bloque + 22)
                pdf.set_font("Helvetica", "I", 7.5)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(45, 4, "Firma / Sello de Aprobación", align="C")
            except Exception:
                pass

    return bytes(pdf.output())

def link_google_calendar(titulo, descripcion, fecha_seguimiento):
    f_str = fecha_seguimiento.strftime("%Y%m%d")
    fechas = f"{f_str}T150000Z/{f_str}T160000Z"
    params = {"action": "TEMPLATE", "text": titulo, "details": descripcion, "dates": fechas}
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def generar_qr_spei(clabe, titular):
    if not clabe:
        return None
    datos = f"SPEI - Titular: {titular} | CLABE: {clabe}"
    url_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(datos)}"
    try:
        r = requests.get(url_qr, timeout=5)
        if r.status_code == 200:
            temp_dir = tempfile.gettempdir()
            path_qr = os.path.join(temp_dir, f"qr_{clabe}.png")
            with open(path_qr, "wb") as f:
                f.write(r.content)
            return path_qr
    except Exception:
        return None
    return None

# ==============================================================================
# VISTA: ACCESO Y REGISTRO
# ==============================================================================
if not st.session_state["autenticado"]:
    st.title("🔒 Portal de Cotizaciones PyME")
    st.caption(f"Inicia sesión o crea tu cuenta para disfrutar de **{DIAS_PRUEBA_GRATIS} días de prueba gratis Pro**.")

    tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", f"🎁 Registrar mi Cuenta ({DIAS_PRUEBA_GRATIS} Días Gratis)"])

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
            reg_empresa = st.text_input("Nombre de tu Primer Negocio / Marca Principal")
            reg_tel = st.text_input("Teléfono de Contacto", placeholder="Número telefónico a 10 dígitos")
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
                            st.success(f"¡Cuenta registrada con éxito con Prueba Pro de {DIAS_PRUEBA_GRATIS} días! Inicia sesión.")
                        else:
                            st.error("Hubo un error al registrar en la base de datos.")

# ==============================================================================
# VISTA: PANEL PRIVADO DEL USUARIO
# ==============================================================================
else:
    user_email = str(st.session_state["usuario_actual"]).lower().strip()
    empresa_data = st.session_state["datos_empresa"]
    
    es_super_admin = (user_email == ADMIN_EMAIL.lower())
    
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

    if es_super_admin:
        es_pro = True
        estado_plan_texto = "👑 Admin Master (Ilimitado Total)"
        limite_negocios_cuenta = 999
    elif plan_raw in ["PRO", "MULTI", "PRO_MULTI"]:
        es_pro = True
        estado_plan_texto = "⭐ Plan PRO"
        limite_negocios_cuenta = MAX_NEGOCIOS_PRO_ESTANDAR
    elif plan_raw == "TRIAL" and dias_restantes_trial > 0:
        es_pro = True
        estado_plan_texto = f"🎁 Prueba Pro ({dias_restantes_trial} días)"
        limite_negocios_cuenta = MAX_NEGOCIOS_PRO_ESTANDAR
    else:
        es_pro = False
        estado_plan_texto = "🏷️ Plan FREE"
        limite_negocios_cuenta = 1

    df_mis_negocios = obtener_negocios_usuario(user_email)
    
    if df_mis_negocios.empty:
        nombres_negocios = [empresa_data.get("nombre", "Mi Negocio")]
    else:
        nombres_negocios = df_mis_negocios["nombre_negocio"].tolist()

    # Barra lateral
    with st.sidebar:
        st.markdown("### 🏢 **Selector de Empresa**")
        negocio_seleccionado = st.selectbox("Trabajando actualmente en:", nombres_negocios, key="sb_negocio_activo")
        st.session_state["negocio_activo"] = negocio_seleccionado

        cfg_activa = {}
        if not df_mis_negocios.empty and negocio_seleccionado in df_mis_negocios["nombre_negocio"].values:
            cfg_activa = df_mis_negocios[df_mis_negocios["nombre_negocio"] == negocio_seleccionado].iloc[0].to_dict()

        st.caption(f"👤 Cuenta: {user_email}")
        
        if es_pro:
            st.success(f"**{estado_plan_texto}**")
        else:
            st.info(f"**{estado_plan_texto}**")
            
        st.divider()

        opciones_menu = [
            "📝 Nueva Cotización", 
            "🏢 Mis Negocios",
            "📦 Mi Catálogo por Marca",
            "🎨 Diseñar Hoja Membretada", 
            "📊 Control CRM & Ganancias", 
            "📢 Mensajes de Venta WhatsApp",
            "⭐ Planes y Precios"
        ]
        
        menu = st.radio("Secciones", opciones_menu)
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["usuario_actual"] = None
            st.session_state["datos_empresa"] = {}
            st.session_state["items"] = []
            st.rerun()

    # Cotizaciones de la cuenta y negocio activo
    df_todas = obtener_cotizaciones()
    df_mis_cotizaciones_negocio = pd.DataFrame()
    df_todas_mis_marcas = pd.DataFrame()
    cotizaciones_mes_actual = 0
    mes_actual_str = datetime.date.today().strftime("%Y-%m")

    if not df_todas.empty and "id_empresa" in df_todas.columns:
        filtro_usuario = df_todas["id_empresa"].str.lower() == user_email.lower()
        df_todas_mis_marcas = df_todas[filtro_usuario]
        
        if "id_negocio" in df_todas.columns:
            filtro_negocio = df_todas["id_negocio"].astype(str) == str(negocio_seleccionado)
            df_mis_cotizaciones_negocio = df_todas[filtro_usuario & filtro_negocio]
        else:
            df_mis_cotizaciones_negocio = df_todas_mis_marcas

        if not df_mis_cotizaciones_negocio.empty and "Fecha" in df_mis_cotizaciones_negocio.columns:
            cotizaciones_mes_actual = len(df_mis_cotizaciones_negocio[df_mis_cotizaciones_negocio["Fecha"].astype(str).str.startswith(mes_actual_str)])

    df_catalogo_todos = obtener_catalogo_api()
    df_mi_catalogo = pd.DataFrame()
    if not df_catalogo_todos.empty and "id_empresa" in df_catalogo_todos.columns:
        f_user_cat = df_catalogo_todos["id_empresa"].str.lower() == user_email.lower()
        if "id_negocio" in df_catalogo_todos.columns:
            f_neg_cat = df_catalogo_todos["id_negocio"].astype(str) == str(negocio_seleccionado)
            df_mi_catalogo = df_catalogo_todos[f_user_cat & f_neg_cat]
        else:
            df_mi_catalogo = df_catalogo_todos[f_user_cat]

    # --- PANTALLA 1: NUEVA COTIZACIÓN ---
    if menu == "📝 Nueva Cotización":
        st.title(f"📄 Generar Cotización — {negocio_seleccionado}")

        if not es_pro and cotizaciones_mes_actual >= LIMITE_FREE_MENSUAL:
            st.error(f"🚫 **Has alcanzado el límite de {LIMITE_FREE_MENSUAL} cotizaciones gratuitas de este mes.**")
            st.info("Para cotizaciones ilimitadas y manejar múltiples marcas, actualiza al Plan Pro.")
            st.stop()

        col_emisor, col_cliente = st.columns(2)
        with col_emisor:
            st.subheader(f"🏢 Emisor: {negocio_seleccionado}")
            mi_empresa = st.text_input("Nombre de la Marca Emisora", value=negocio_seleccionado)
            tel_sug = cfg_activa.get("telefono", empresa_data.get("telefono", ""))
            mi_telefono = st.text_input("Teléfono de Contacto del Negocio", value=str(tel_sug), placeholder="Número telefónico a 10 dígitos")

        with col_cliente:
            st.subheader("👤 Datos del Cliente")
            cliente_nombre = st.text_input("Nombre del Cliente o Empresa", placeholder="Nombre o Razón Social")
            cliente_telefono = st.text_input("Teléfono del Cliente", placeholder="Número telefónico a 10 dígitos")

        st.divider()

        if es_pro and not df_mi_catalogo.empty:
            st.subheader(f"⚡ Carga Rápida desde Catálogo ({negocio_seleccionado})")
            opciones_cat = ["-- Seleccionar del Catálogo --"] + df_mi_catalogo["Nombre"].tolist()
            item_sel = st.selectbox("Elige un producto/servicio para agregarlo en 1 clic:", opciones_cat)
            
            if item_sel != "-- Seleccionar del Catálogo --":
                row_sel = df_mi_catalogo[df_mi_catalogo["Nombre"] == item_sel].iloc[0]
                col_c1, col_c2, col_c3 = st.columns([1, 1, 2])
                with col_c1:
                    cant_cat = st.number_input("Cantidad a cotizar", min_value=1.0, value=1.0, step=1.0, key="cant_cat")
                with col_c2:
                    st.write("")
                    st.write("")
                    if st.button("➕ Insertar a la Cotización", use_container_width=True):
                        st.session_state["items"].append({
                            "Tipo": str(row_sel["Unidad"]),
                            "Concepto": str(row_sel["Nombre"]),
                            "Detalle": str(row_sel.get("Detalle", "")),
                            "Cantidad": float(cant_cat),
                            "P. Unitario": float(row_sel["Precio"]),
                            "Importe": float(cant_cat * float(row_sel["Precio"]))
                        })
                        st.rerun()
            st.divider()

        st.subheader("➕ Agregar Concepto Manual")
        tab_servicio, tab_producto = st.tabs(["💼 Servicios", "📦 Productos"])

        with tab_servicio:
            with st.form("form_serv", clear_on_submit=True):
                col_s1, col_s2, col_s3, col_s4 = st.columns([3, 1.2, 1.2, 1])
                with col_s1:
                    serv_nombre = st.text_input("Nombre del Servicio", placeholder="Descripción del servicio")
                with col_s2:
                    serv_unidad = st.selectbox("Unidad", ["Servicio", "Hora", "Proyecto", "Mes", "Evento", "Sesión"])
                with col_s3:
                    serv_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
                with col_s4:
                    serv_precio = st.number_input("Precio ($)", min_value=0.0, value=0.0, step=100.0)
                
                serv_detalle = st.text_area("¿Qué incluye este servicio? (Opcional)", placeholder="Entregables, especificaciones o detalles de trabajo.")
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
                    prod_nombre = st.text_input("Nombre del Producto", placeholder="Descripción del producto")
                with col_p2:
                    prod_unidad = st.selectbox("Presentación", ["Pieza", "Kit", "Paquete", "Caja", "Metro", "Lote"])
                with col_p3:
                    prod_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
                with col_p4:
                    prod_precio = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=50.0)
                
                prod_detalle = st.text_area("Especificaciones del producto (Opcional)", placeholder="Materiales, dimensiones o acabados.")
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
            
            subtotal_bruto = float(df_items["Importe"].sum())

            # Calculadora de Descuentos e IVA con soporte de IVA INCLUIDO
            col_calc1, col_calc2, col_calc3 = st.columns(3)
            with col_calc1:
                st.metric("Subtotal de Conceptos", f"${subtotal_bruto:,.2f} MXN")
            with col_calc2:
                porcentaje_desc = st.number_input("Descuento Comercial (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
                monto_descuento = subtotal_bruto * (porcentaje_desc / 100.0)
            with col_calc3:
                tipo_iva = st.selectbox(
                    "Aplicar Impuesto (I.V.A.)", 
                    [
                        "0% (Sin IVA / Precios Netos)",
                        "IVA Incluido (Precios ya tienen IVA 16%)", 
                        "16% (Agregar IVA General)", 
                        "8% (Agregar IVA Frontera)"
                    ]
                )
                
                base_con_descuento = subtotal_bruto - monto_descuento
                
                if "IVA Incluido" in tipo_iva:
                    # El total ya contiene el IVA
                    total_final = base_con_descuento
                    base_gravable = total_final / 1.16
                    monto_iva = total_final - base_gravable
                    etiqueta_iva_wa = "IVA Incluido"
                elif "16%" in tipo_iva:
                    monto_iva = base_con_descuento * 0.16
                    total_final = base_con_descuento + monto_iva
                    etiqueta_iva_wa = "+ 16% IVA"
                elif "8%" in tipo_iva:
                    monto_iva = base_con_descuento * 0.08
                    total_final = base_con_descuento + monto_iva
                    etiqueta_iva_wa = "+ 8% IVA"
                else:
                    monto_iva = 0.0
                    total_final = base_con_descuento
                    etiqueta_iva_wa = "Precios sin IVA"

            st.success(f"### 💰 **TOTAL FINAL A COBRAR: ${total_final:,.2f} MXN ({etiqueta_iva_wa})**")

            if st.button("🗑️ Limpiar lista de cotización"):
                st.session_state["items"] = []
                st.rerun()
        else:
            df_items = pd.DataFrame(columns=COLUMNAS_BASE)
            subtotal_bruto, monto_descuento, monto_iva, total_final = 0.0, 0.0, 0.0, 0.0
            etiqueta_iva_wa = "Precios sin IVA"
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
                cfg_color = cfg_activa.get("color", "#831843")
                cfg_pie = cfg_activa.get("pie_pdf", "Gracias por su preferencia.")
                cfg_align = st.session_state.get(f"align_{negocio_seleccionado}", "Izquierda")
                cfg_logo_path = st.session_state.get(f"logo_{negocio_seleccionado}", None)
                cfg_banco = cfg_activa.get("banco", "")
                cfg_clabe = cfg_activa.get("clabe", "")
                cfg_titular = cfg_activa.get("titular", negocio_seleccionado)
                cfg_firma_path = st.session_state.get(f"firma_{negocio_seleccionado}", None)
                plantilla_sel = st.session_state.get("cfg_plantilla", "Ejecutiva")

                texto_bancario = f"Banco: {cfg_banco}\nCLABE: {cfg_clabe}\nBeneficiario: {cfg_titular}" if (cfg_clabe and cfg_banco) else ""
                path_qr_pago = generar_qr_spei(cfg_clabe, cfg_titular) if (es_pro and cfg_clabe) else None

                pdf_bytes = generar_pdf(
                    mi_empresa if mi_empresa.strip() else negocio_seleccionado, 
                    mi_telefono, cliente_nombre, cliente_telefono, 
                    df_items, subtotal_bruto, monto_descuento, monto_iva, total_final, vigencia_dias, notas_adicionales,
                    es_pro=es_pro, logo_path=cfg_logo_path,
                    color_hex=cfg_color, pie_custom=cfg_pie, logo_align=cfg_align,
                    datos_banco=texto_bancario, qr_path=path_qr_pago, firma_path=cfg_firma_path, plantilla=plantilla_sel,
                    etiqueta_iva=etiqueta_iva_wa
                )
                
                st.download_button(
                    label="📥 Descargar Cotización en PDF",
                    data=pdf_bytes,
                    file_name=f"Cotizacion_{negocio_seleccionado}_{cliente_nombre.strip().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                # Resumen de WhatsApp estructurado con especificación de IVA
                resumen_lineas = [f"• *{it['Concepto']}* ({it['Cantidad']:.0f} {it['Tipo']}) -> ${it['Importe']:,.2f}" for _, it in df_items.iterrows()]
                
                # Desglose de impuesto para el mensaje
                info_impuesto_msg = f" ({etiqueta_iva_wa})"
                
                mensaje_wa = (
                    f"Hola *{cliente_nombre.strip()}*, te comparto el resumen de tu cotización con *{mi_empresa or negocio_seleccionado}*:\n\n"
                    f"{chr(10).join(resumen_lineas)}\n\n"
                    f"💰 *TOTAL:* ${total_final:,.2f} MXN{info_impuesto_msg}\n"
                    f"⏳ *Vigencia:* {vigencia_dias} días.\n\n"
                    f"Quedo a tu disposición si deseas confirmar o realizar algún ajuste."
                )
                tel_formateado = "".join(filter(str.isdigit, cliente_telefono))
                wa_url = f"https://wa.me/{tel_formateado}?text={urllib.parse.quote(mensaje_wa)}"
                st.link_button("📲 Enviar Resumen por WhatsApp", wa_url, use_container_width=True)

                cal_desc = f"Seguimiento de cotización enviada por ${total_final:,.2f} MXN ({etiqueta_iva_wa}). Tel: {cliente_telefono} ({negocio_seleccionado})"
                cal_url = link_google_calendar(f"Llamar a {cliente_nombre} - {negocio_seleccionado}", cal_desc, fecha_seg)
                st.link_button("📅 Agendar en Google Calendar", cal_url, use_container_width=True)

                if st.button("💾 Guardar en el Historial de este Negocio", use_container_width=True):
                    folio = f"COT-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
                    datos_a_guardar = {
                        "id_empresa": user_email,
                        "id_negocio": negocio_seleccionado,
                        "Folio": folio,
                        "Fecha": datetime.date.today().strftime("%Y-%m-%d"),
                        "Cliente": cliente_nombre.strip(),
                        "Telefono": cliente_telefono.strip(),
                        "Subtotal": subtotal_bruto,
                        "Descuento": monto_descuento,
                        "IVA": monto_iva,
                        "Total": total_final,
                        "Conceptos": " | ".join([f"{it['Concepto']} ({it['Cantidad']})" for _, it in df_items.iterrows()]),
                        "Vigencia_Dias": vigencia_dias,
                        "Fecha_Seguimiento": fecha_seg.strftime("%Y-%m-%d"),
                        "Estatus": "Pendiente",
                        "Notas": f"{notas_adicionales.strip()} | Impuesto: {etiqueta_iva_wa}"
                    }
                    guardado = guardar_cotizacion_api(datos_a_guardar)
                    if guardado:
                        st.success(f"✅ Cotización guardada en {negocio_seleccionado} con Folio {folio}")
                    else:
                        st.error("Error al guardar la cotización.")
            else:
                st.caption("Ingresa el nombre del cliente y al menos un concepto para habilitar la descarga del PDF y WhatsApp.")

    # --- PANTALLA 2: MIS NEGOCIOS (ILIMITADO EN ADMIN) ---
    elif menu == "🏢 Mis Negocios":
        st.title("🏢 Gestión de Mis Marcas y Negocios")
        if es_super_admin:
            st.success("👑 **Cuenta Administrador Master:** Tienes alta y gestión de **negocios ilimitados**.")
        else:
            st.caption(f"El **Plan Pro (${PRECIO_PRO_MENSUAL} MXN/mes)** te permite operar hasta **{MAX_NEGOCIOS_PRO_ESTANDAR} marcas independientes**.")

        if not es_pro:
            st.warning("🔒 La gestión de múltiples marcas está disponible en el Plan Pro.")
            st.stop()

        tab_lista_neg, tab_crear_neg = st.tabs(["📋 Mis Marcas Registradas", "➕ Dar de Alta Nuevo Negocio"])

        with tab_crear_neg:
            num_actual = len(df_mis_negocios) if not df_mis_negocios.empty else 1
            if not es_super_admin and num_actual >= limite_negocios_cuenta:
                st.info(f"ℹ️ Has alcanzado el límite de {limite_negocios_cuenta} negocios registrados.")
            else:
                with st.form("form_nuevo_negocio", clear_on_submit=True):
                    st.write(f"Tienes **{num_actual}** marcas activas.")
                    nuevo_neg_nombre = st.text_input("Nombre de la Nueva Empresa / Marca", placeholder="Nombre de la nueva marca")
                    nuevo_neg_tel = st.text_input("Teléfono de Contacto Oficial", placeholder="Número telefónico a 10 dígitos")
                    
                    if st.form_submit_button("🚀 Crear y Registrar este Negocio", use_container_width=True):
                        if nuevo_neg_nombre.strip():
                            ok = agregar_nuevo_negocio_api(user_email, nuevo_neg_nombre.strip(), nuevo_neg_tel.strip())
                            if ok:
                                st.success(f"✅ ¡Negocio '{nuevo_neg_nombre.strip()}' dado de alta exitosamente!")
                                st.rerun()
                            else:
                                st.error("Error al conectar con la base de datos.")
                        else:
                            st.warning("Escribe el nombre del negocio.")

        with tab_lista_neg:
            if not df_mis_negocios.empty:
                st.dataframe(df_mis_negocios[["nombre_negocio", "telefono", "color", "banco", "clabe", "titular"]], use_container_width=True, hide_index=True)
            else:
                st.info("Solo tienes tu negocio principal registrado.")

    # --- PANTALLA 3: MI CATÁLOGO POR MARCA ---
    elif menu == "📦 Mi Catálogo por Marca":
        st.title(f"📦 Catálogo Ilimitado — {negocio_seleccionado}")
        st.caption(f"Los productos y servicios guardados aquí solo pertenecerán a la marca **{negocio_seleccionado}**.")

        if not es_pro:
            st.warning("🔒 El catálogo guardado está disponible en el Plan Pro.")
            st.stop()

        tab_ver_cat, tab_nuevo_cat = st.tabs(["📋 Paquetes de este Negocio", f"➕ Agregar a {negocio_seleccionado}"])

        with tab_nuevo_cat:
            with st.form("form_nuevo_cat", clear_on_submit=True):
                col_cat1, col_cat2, col_cat3 = st.columns([2, 1, 1])
                with col_cat1:
                    cat_nombre = st.text_input("Nombre del Paquete o Producto", placeholder="Nombre del paquete")
                with col_cat2:
                    cat_tipo = st.selectbox("Categoría", ["Servicio", "Producto"])
                with col_cat3:
                    cat_unidad = st.selectbox("Presentación / Unidad", ["Servicio", "Proyecto", "Hora", "Mes", "Pieza", "Paquete", "Kit", "Lote"])
                
                cat_precio = st.number_input("Precio Base Sugerido ($ MXN)", min_value=0.0, step=100.0)
                cat_detalle = st.text_area("¿Qué incluye este paquete? (Detalle / Alcance)", placeholder="Entregables, horas de trabajo o especificaciones.")
                
                if st.form_submit_button(f"💾 Guardar en Catálogo de {negocio_seleccionado}", use_container_width=True):
                    if cat_nombre.strip():
                        ok = guardar_item_catalogo_api(user_email, negocio_seleccionado, cat_tipo, cat_nombre.strip(), cat_unidad, float(cat_precio), cat_detalle.strip())
                        if ok:
                            st.success(f"✅ '{cat_nombre.strip()}' guardado con éxito.")
                            st.rerun()
                        else:
                            st.error("Error al conectar con la base de datos.")
                    else:
                        st.warning("Escribe el nombre del ítem.")

        with tab_ver_cat:
            if not df_mi_catalogo.empty:
                st.dataframe(df_mi_catalogo[["Tipo", "Nombre", "Unidad", "Precio", "Detalle"]], use_container_width=True, hide_index=True)
                st.write("---")
                item_a_borrar = st.selectbox("Selecciona el ítem que deseas eliminar:", ["-- Seleccionar --"] + df_mi_catalogo["Nombre"].tolist())
                if item_a_borrar != "-- Seleccionar --":
                    if st.button(f"Eliminar '{item_a_borrar}' de {negocio_seleccionado}", type="primary"):
                        eliminar_item_catalogo_api(user_email, negocio_seleccionado, item_a_borrar)
                        st.success("Ítem eliminado.")
                        st.rerun()
            else:
                st.info(f"Aún no has registrado paquetes específicos para {negocio_seleccionado}.")

    # --- PANTALLA 4: PERSONALIZADOR Y SELECCIÓN DE PLANTILLAS ---
    elif menu == "🎨 Diseñar Hoja Membretada":
        st.title(f"🎨 Personalizar Hoja Membretada — {negocio_seleccionado}")
        st.caption("Configura colores, logotipos, cuentas bancarias y el estilo de plantilla para tus cotizaciones.")

        if not es_pro:
            st.warning("🔒 Esta sección está disponible en el Plan Pro.")
            st.stop()
        
        col_d1, col_d2 = st.columns([1.1, 1.2])

        with col_d1:
            st.subheader(f"1. Identidad Visual: {negocio_seleccionado}")
            
            plantilla_elegida = st.selectbox("Plantilla / Maquetación del PDF", ["Ejecutiva (Clásica)", "Moderna (Línea Gruesa)", "Minimalista"], index=0)
            st.session_state["cfg_plantilla"] = plantilla_elegida

            color_actual = cfg_activa.get("color", "#831843")
            color_seleccionado = st.color_picker(f"Color Oficial de {negocio_seleccionado}", value=color_actual)

            logo_subido = st.file_uploader(f"Subir Logo de {negocio_seleccionado} (PNG/JPG)", type=["png", "jpg", "jpeg"], key=f"up_{negocio_seleccionado}")
            if logo_subido:
                temp_dir = tempfile.gettempdir()
                path_logo = os.path.join(temp_dir, f"logo_{user_email.replace('@','_')}_{negocio_seleccionado}.png")
                with open(path_logo, "wb") as f:
                    f.write(logo_subido.getbuffer())
                st.session_state[f"logo_{negocio_seleccionado}"] = path_logo
                st.success("✅ Logotipo cargado.")
            
            align_val = st.radio("Alineación del Logotipo", ["Izquierda", "Derecha"], horizontal=True, key=f"align_r_{negocio_seleccionado}")
            st.session_state[f"align_{negocio_seleccionado}"] = align_val

            st.write("---")
            st.subheader("2. Datos de Cobro Bancario (SPEI y QR)")
            
            banco_guardado = cfg_activa.get("banco", None)
            idx_banco = LISTA_BANCOS_MX.index(banco_guardado) if (banco_guardado in LISTA_BANCOS_MX) else None
            
            banco_in = st.selectbox(
                "Banco Receptor", 
                LISTA_BANCOS_MX, 
                index=idx_banco,
                placeholder="Escribe o selecciona tu institución bancaria..."
            )
            
            clabe_in = st.text_input("CLABE Interbancaria (18 dígitos)", value=str(cfg_activa.get("clabe", "")), placeholder="Número de CLABE a 18 dígitos")
            titular_in = st.text_input("Nombre del Beneficiario / Titular", value=str(cfg_activa.get("titular", negocio_seleccionado)))

            st.write("---")
            st.subheader("3. Firma y Pie de Página")
            firma_subida = st.file_uploader("Subir Firma Digital / Sello", type=["png", "jpg", "jpeg"], key=f"firma_{negocio_seleccionado}")
            if firma_subida:
                temp_dir = tempfile.gettempdir()
                path_firma = os.path.join(temp_dir, f"firma_{user_email.replace('@','_')}_{negocio_seleccionado}.png")
                with open(path_firma, "wb") as f:
                    f.write(firma_subida.getbuffer())
                st.session_state[f"firma_{negocio_seleccionado}"] = path_firma
                st.success("✅ Firma/Sello cargado.")

            pie_texto = st.text_area(
                "Texto personalizado al pie del PDF", 
                value=str(cfg_activa.get("pie_pdf", "Gracias por su preferencia - Documento emitido para fines presupuestarios.")),
                key=f"pie_in_{negocio_seleccionado}"
            )

            tel_negocio_in = st.text_input("Teléfono del Negocio", value=str(cfg_activa.get("telefono", "")), placeholder="Número telefónico a 10 dígitos")

            if st.button(f"💾 Guardar Ajustes para {negocio_seleccionado}", use_container_width=True, type="primary"):
                ok = guardar_config_negocio_api(
                    user_email, negocio_seleccionado, tel_negocio_in, 
                    color_seleccionado, banco_in or "", clabe_in, titular_in, pie_texto
                )
                if ok:
                    st.success("✅ Configuración guardada en la base de datos.")
                    st.rerun()

        with col_d2:
            st.subheader(f"👁️ Vista Previa: {negocio_seleccionado}")
            st.caption(f"Estilo visual: **{plantilla_elegida}**")

            with st.container(border=True):
                col_hdr1, col_hdr2 = st.columns([3, 1])
                with col_hdr1:
                    st.markdown(f"<h3 style='color:{color_seleccionado}; margin-bottom:0;'>{negocio_seleccionado.upper()}</h3>", unsafe_allow_html=True)
                    st.caption(f"Contacto: {tel_negocio_in or 'Contacto no registrado'}")
                with col_hdr2:
                    st.markdown(f"<div style='text-align:right; font-weight:bold; color:{color_seleccionado}; border:1px solid #cbd5e1; padding:4px 8px; border-radius:4px; font-size:12px;'>COTIZACIÓN</div>", unsafe_allow_html=True)
                
                grosor_linea = "4px" if "Moderna" in plantilla_elegida else "2px"
                st.markdown(f"<div style='height:{grosor_linea}; background-color:{color_seleccionado}; margin-top:5px; margin-bottom:12px;'></div>", unsafe_allow_html=True)

                col_c_info1, col_c_info2 = st.columns(2)
                with col_c_info1:
                    st.markdown("**CLIENTE:** Ejemplo de Cliente S.A.")
                    st.caption("Tel: Contacto del cliente")
                with col_c_info2:
                    st.markdown(f"**Fecha:** {datetime.date.today().strftime('%d/%m/%Y')}")
                    st.caption("Vigencia: 7 días")

                st.write("")
                df_demo = pd.DataFrame([
                    {"Descripción": f"Servicio especializado ({negocio_seleccionado})", "Cant.": "1.00", "P. Unitario": "$3,500.00", "Subtotal": "$3,500.00"},
                    {"Descripción": "Paquete complementario", "Cant.": "2.00", "P. Unitario": "$600.00", "Subtotal": "$1,200.00"}
                ])
                st.dataframe(df_demo, use_container_width=True, hide_index=True)

                st.markdown(f"<div style='text-align:right; font-size:16px; font-weight:bold; color:{color_seleccionado}; margin-top:8px;'>TOTAL A LIQUIDAR: $4,700.00 MXN</div>", unsafe_allow_html=True)

                if banco_in and clabe_in:
                    st.write("")
                    with st.container(border=True):
                        st.markdown(f"<div style='font-size:11px; font-weight:bold; color:{color_seleccionado};'>INFORMACIÓN PARA PAGO / SPEI</div>", unsafe_allow_html=True)
                        st.markdown(f"**Banco:** {banco_in}  \n**CLABE:** `{clabe_in}`  \n**Beneficiario:** {titular_in}")

                st.write("---")
                st.markdown(f"<div style='text-align:center; font-size:11px; color:#94a3b8;'>{pie_texto}</div>", unsafe_allow_html=True)

    # --- PANTALLA 5: CRM DIVIDIDO POR NEGOCIO Y GANANCIAS NETAS ---
    elif menu == "📊 Control CRM & Ganancias":
        st.title(f"📊 Control Comercial & Ganancias — {negocio_seleccionado}")
        
        tab_crm_marca, tab_crm_global = st.tabs([f"🏢 Métricas de {negocio_seleccionado}", "🌐 Consolidado Global de Todas Mis Marcas"])

        with tab_crm_marca:
            if not df_mis_cotizaciones_negocio.empty:
                totales_num = pd.to_numeric(df_mis_cotizaciones_negocio['Total'], errors='coerce').fillna(0)
                subtotales_num = pd.to_numeric(df_mis_cotizaciones_negocio['Subtotal'], errors='coerce').fillna(0) if 'Subtotal' in df_mis_cotizaciones_negocio.columns else totales_num
                
                total_cotizado = float(totales_num.sum())
                
                df_cobradas = df_mis_cotizaciones_negocio[df_mis_cotizaciones_negocio["Estatus"].isin(["Cobrada", "Aprobada"])]
                ganancias_netas_cobradas = float(pd.to_numeric(df_cobradas['Total'], errors='coerce').fillna(0).sum())
                
                pendientes = len(df_mis_cotizaciones_negocio[df_mis_cotizaciones_negocio["Estatus"] == "Pendiente"])
                ganadas = len(df_cobradas)

                col_k1, col_k2, col_k3, col_k4 = st.columns(4)
                with col_k1:
                    st.metric("💰 Ganancia Neta Cobrada", f"${ganancias_netas_cobradas:,.2f} MXN")
                with col_k2:
                    st.metric("📈 Total Propuesto", f"${total_cotizado:,.2f} MXN")
                with col_k3:
                    st.metric("🟡 Cotizaciones Pendientes", pendientes)
                with col_k4:
                    st.metric("🟢 Cierres Ganados", ganadas)

                st.write("---")
                st.subheader(f"🔄 Actualizar Estatus de Cotización ({negocio_seleccionado})")
                col_crm1, col_crm2, col_crm3 = st.columns([2, 2, 1])
                with col_crm1:
                    folio_sel = st.selectbox("Folio:", df_mis_cotizaciones_negocio["Folio"].tolist(), key="crm_fol_1")
                with col_crm2:
                    nuevo_estatus = st.selectbox("Estatus Comercial:", ["Pendiente", "Aprobada", "Cobrada", "Rechazada"], key="crm_est_1")
                with col_crm3:
                    st.write("")
                    st.write("")
                    if st.button("Actualizar", use_container_width=True, key="btn_act_1"):
                        ok = actualizar_estatus_api(folio_sel, user_email, nuevo_estatus)
                        if ok:
                            st.success("¡Estatus actualizado!")
                            st.rerun()

                st.write("---")
                st.subheader(f"📋 Registro de {negocio_seleccionado}")
                cols_crm = ["Folio", "Fecha", "Cliente", "Telefono", "Total", "Conceptos", "Fecha_Seguimiento", "Estatus"]
                st.dataframe(df_mis_cotizaciones_negocio[cols_crm], use_container_width=True, hide_index=True)

                csv_data = df_mis_cotizaciones_negocio.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Exportar Ventas de {negocio_seleccionado} (CSV)",
                    data=csv_data,
                    file_name=f"Ventas_{negocio_seleccionado}.csv",
                    mime="text/csv"
                )
            else:
                st.info(f"Aún no hay cotizaciones registradas para {negocio_seleccionado}.")

        with tab_crm_global:
            if not df_todas_mis_marcas.empty:
                st.subheader("🌐 Visión Financiera Consolidada (Todas tus Marcas)")
                
                totales_all = pd.to_numeric(df_todas_mis_marcas['Total'], errors='coerce').fillna(0)
                total_global_propuesto = float(totales_all.sum())
                
                df_all_cobradas = df_todas_mis_marcas[df_todas_mis_marcas["Estatus"].isin(["Cobrada", "Aprobada"])]
                ganancias_globales_cobradas = float(pd.to_numeric(df_all_cobradas['Total'], errors='coerce').fillna(0).sum())

                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    st.metric("💰 Ganancia Total Consolidada", f"${ganancias_globales_cobradas:,.2f} MXN")
                with col_g2:
                    st.metric("📈 Cotizado Total (Todas las Marcas)", f"${total_global_propuesto:,.2f} MXN")
                with col_g3:
                    st.metric("📑 Total de Folios Emitidos", len(df_todas_mis_marcas))

                st.write("---")
                st.dataframe(df_todas_mis_marcas[["Folio", "id_negocio", "Fecha", "Cliente", "Total", "Estatus"]], use_container_width=True, hide_index=True)

                csv_all = df_todas_mis_marcas.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar Reporte Maestro Completo (CSV)",
                    data=csv_all,
                    file_name=f"Consolidado_Ventas_{user_email}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No hay registros en tu cuenta.")

    # --- PANTALLA 6: MENSAJES DE VENTA WHATSAPP ---
    elif menu == "📢 Mensajes de Venta WhatsApp":
        st.title("📢 Enviar Mensaje de Venta por WhatsApp")
        st.caption("Prospección directa: envía un mensaje personalizado a dueños de negocios con enlace directo a la plataforma.")

        col_v1, col_v2 = st.columns([1, 1.2])

        with col_v1:
            st.subheader("1. Datos del Prospecto")
            dest_nombre = st.text_input("Nombre del Contacto / Dueño de Negocio", placeholder="Nombre del prospecto")
            dest_tel = st.text_input("Número de WhatsApp", placeholder="Número telefónico a 10 dígitos")
            
            st.write("---")
            st.subheader("2. Estilo de Mensaje")
            tipo_msg = st.radio("Enfoque de prospección:", [
                "🚀 Directo y Profesional (Recomendado)",
                "💼 Enfoque en Ahorro de Tiempo y Cobro SPEI",
                "🎁 Invitación a Prueba Gratis de 3 Días"
            ])

        nombre_saludo = dest_nombre.strip() if dest_nombre.strip() else "amigo(a)"
        
        if "Directo" in tipo_msg:
            texto_venta = (
                f"¡Hola {nombre_saludo}! 👋 Espero que estés teniendo un excelente día.\n\n"
                f"Te escribo para compartirte *Cotizador PyME Pro*, una plataforma diseñada para generar cotizaciones formales en PDF membretadas con tu logotipo, código QR SPEI para transferencias y envío directo por WhatsApp en menos de 1 minuto.\n\n"
                f"Puedes registrar tu negocio y probarlo gratis por 3 días aquí:\n"
                f"👉 {URL_APP_PUBLICA}\n\n"
                f"Quedo a tu disposición si deseas que te ayude a configurarlo con la identidad de tu marca."
            )
        elif "Ahorro" in tipo_msg:
            texto_venta = (
                f"Hola {nombre_saludo}, ¿cómo estás? Te contacto brevemente porque desarrollamos una solución para PyMEs y emprendedores:\n\n"
                f"Con *Cotizador PyME* dejas de hacer cotizaciones manuales y generas propuestas ejecutivas con catálogo precargado, desglose de IVA y tus datos bancarios listos para cobrar.\n\n"
                f"Pruébalo sin costo aquí:\n"
                f"📲 {URL_APP_PUBLICA}\n\n"
                f"¡Saludos!"
            )
        else:
            texto_venta = (
                f"¡Hola {nombre_saludo}! 🎁 Te obsequiamos un acceso de prueba gratis por 3 días a *Cotizador PyME Pro*.\n\n"
                f"Crea propuestas comerciales elegantes, descarga tus PDFs membretados y gestiona el seguimiento de tus clientes en tiempo real.\n\n"
                f"Ingresa y regístrate en 30 segundos:\n"
                f"🔗 {URL_APP_PUBLICA}"
            )

        with col_v2:
            st.subheader("👁️ Vista Previa del Mensaje")
            msg_editado = st.text_area("Puedes editar el texto antes de enviar:", value=texto_venta, height=220)

            tel_limpio = "".join(filter(str.isdigit, dest_tel))
            if tel_limpio:
                wa_share_url = f"https://wa.me/{tel_limpio}?text={urllib.parse.quote(msg_editado)}"
                st.link_button("📲 Abrir WhatsApp y Enviar Mensaje", wa_share_url, use_container_width=True, type="primary")
            else:
                st.info("Ingresa el número de WhatsApp del prospecto para activar el botón de envío directo.")

    # --- PANTALLA 7: PLANES Y PRECIOS ---
    elif menu == "⭐ Planes y Precios":
        st.title("⭐ Planes y Precios")
        st.write("Planes comerciales diseñados para profesionalizar cualquier tipo de negocio.")
        
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            st.markdown(f"""
            ### 🟢 Plan Free
            **$0 MXN / mes**
            - **1 solo negocio**
            - Hasta **{LIMITE_FREE_MENSUAL} cotizaciones al mes**
            - Formato estándar con marca de agua en PDF
            - Soporte estándar
            """)

        with col_p2:
            st.markdown(f"""
            ### ⭐ Plan Pro
            **${PRECIO_PRO_MENSUAL} MXN / mes** *(Completo)*
            - **Hasta {MAX_NEGOCIOS_PRO_ESTANDAR} Negocios / Marcas independientes**
            - **Cotizaciones Ilimitadas** en todas tus marcas
            - **Catálogo Ilimitado** aislado por cada negocio
            - **Hoja Membretada con Colores y Logotipo oficial** por marca
            - **Cuentas Bancarias + QR SPEI de pago directo** independientes
            - **Calculadora de IVA (Incluido o Desglosado) y Descuentos**
            - **Firma digital / Sello escaneado**
            - **Pipeline CRM, ganancias netas y reportes en Excel**
            - **Sin marcas de agua**
            """)

        st.divider()
        st.info("💡 Para activar tu suscripción Pro permanente, contáctanos directamente vía WhatsApp.")
        wa_upgrade = f"https://wa.me/529817360428?text=Hola,%20quiero%20activar%20mi%20Plan%20Pro%20(${PRECIO_PRO_MENSUAL}/mes)%20en%20Cotizador%20PyME%20para%20la%20cuenta%20{user_email}"
        st.link_button("📲 Solicitar Activación Pro por WhatsApp", wa_upgrade, use_container_width=True)
