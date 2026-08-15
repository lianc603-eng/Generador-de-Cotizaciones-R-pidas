import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import urllib.parse
from streamlit_gsheets import GSheetsConnection

# --- Configuración de página ---
st.set_page_config(page_title="Cotizador PyME Pro", page_icon="📄", layout="wide")

COLUMNAS_BASE = ["Tipo", "Concepto", "Detalle", "Cantidad", "P. Unitario", "Importe"]

# --- Inicialización de Estado ---
if "items" not in st.session_state or not isinstance(st.session_state["items"], list):
    st.session_state["items"] = []

# --- Conexión con Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn = None

# --- Funciones Utilitarias ---
class PDFCotizacion(FPDF):
    def __init__(self, emisor_nombre, emisor_tel):
        super().__init__()
        self.emisor_nombre = str(emisor_nombre) if emisor_nombre else "Empresa / Emisor"
        self.emisor_tel = str(emisor_tel) if emisor_tel else ""

    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(30, 41, 59)
        self.cell(0, 7, self.emisor_nombre.upper(), new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        if self.emisor_tel:
            self.cell(0, 5, f"Contacto / Tel: {self.emisor_tel}", new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(3)
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, "Documento emitido sin validez fiscal directa - Generado con Cotizador PyME", align="C")

def sanitizar_texto(texto):
    if not texto:
        return ""
    reemplazos = {"–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "*"}
    for orig, rep in reemplazos.items():
        texto = texto.replace(orig, rep)
    return str(texto).encode("latin-1", "replace").decode("latin-1")

def generar_pdf(empresa, emisor_tel, cliente, cliente_tel, items_df, total, vigencia, notas):
    pdf = PDFCotizacion(empresa, emisor_tel)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
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
    pdf.set_text_color(15, 23, 42)
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
    pdf.set_text_color(15, 23, 42)
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
    # Agendar bloque de 9:00 AM a 10:00 AM
    fechas = f"{f_str}T150000Z/{f_str}T160000Z"
    params = {
        "action": "TEMPLATE",
        "text": titulo,
        "details": descripcion,
        "dates": fechas,
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

# --- Navegación Principal ---
menu = st.sidebar.radio("Navegación", ["📝 Nueva Cotización", "📊 Historial y Seguimiento"])

if menu == "📝 Nueva Cotización":
    st.title("📄 Cotizador PyME Pro")
    
    col_emisor, col_cliente = st.columns(2)
    with col_emisor:
        st.subheader("🏢 Datos de tu Empresa")
        mi_empresa = st.text_input("Nombre del Negocio / Marca", placeholder="Ej. Alfa & Omega")
        mi_telefono = st.text_input("Tu Teléfono de Contacto", placeholder="Ej. 9811234567")

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
                serv_nombre = st.text_input("Nombre del Servicio", placeholder="Ej. Paquete XV Años")
            with col_s2:
                serv_unidad = st.selectbox("Unidad", ["Servicio", "Hora", "Proyecto", "Mes", "Evento", "Sesión"])
            with col_s3:
                serv_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
            with col_s4:
                serv_precio = st.number_input("Precio ($)", min_value=0.0, value=0.0, step=100.0)
            
            serv_detalle = st.text_area("¿Qué incluye este servicio? (Opcional)", placeholder="Ej. Cobertura de 5 horas y entrega digital de fotos.")
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
                prod_nombre = st.text_input("Nombre del Producto", placeholder="Ej. Cuadro Canvas 60x40cm")
            with col_p2:
                prod_unidad = st.selectbox("Presentación", ["Pieza", "Kit", "Paquete", "Caja", "Metro", "Lote"])
            with col_p3:
                prod_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
            with col_p4:
                prod_precio = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=50.0)
            
            prod_detalle = st.text_area("Especificaciones o contenido del producto (Opcional)", placeholder="Ej. Bastidor de pino y barniz protector.")
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
                    "Tipo": it.get("Tipo", "Servicio"),
                    "Concepto": it.get("Concepto", ""),
                    "Detalle": it.get("Detalle", ""),
                    "Cantidad": float(it.get("Cantidad", 1.0)),
                    "P. Unitario": float(it.get("P. Unitario", 0.0)),
                    "Importe": float(it.get("Importe", 0.0))
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
        fecha_seg = st.date_input("Fecha para dar seguimiento / llamada", value=datetime.date.today() + datetime.timedelta(days=2))
        notas_adicionales = st.text_area("Condiciones de entrega y pago", value="Anticipo del 50% para inicio y 50% al entregar.")

    with col_actions:
        st.subheader("🚀 Exportar y Agendar")
        if not df_items.empty and cliente_nombre and cliente_nombre.strip():
            pdf_bytes = generar_pdf(
                mi_empresa if mi_empresa.strip() else "Mi Empresa", 
                mi_telefono, cliente_nombre, cliente_telefono, 
                df_items, total_cotizacion, vigencia_dias, notas_adicionales
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
                f"Quedo a tu disposición si deseas confirmar."
            )
            tel_formateado = "".join(filter(str.isdigit, cliente_telefono))
            wa_url = f"https://wa.me/{tel_formateado}?text={urllib.parse.quote(mensaje_wa)}"
            st.link_button("📲 Enviar Resumen por WhatsApp", wa_url, use_container_width=True)

            # Botón de Google Calendar
            cal_desc = f"Seguimiento de cotización enviada por ${total_cotizacion:,.2f} MXN. Tel: {cliente_telefono}"
            cal_url = link_google_calendar(f"Llamar a {cliente_nombre} (Seguimiento Cotización)", cal_desc, fecha_seg)
            st.link_button("📅 Agendar Recordatorio en Google Calendar", cal_url, use_container_width=True)

            # Guardar en Google Sheets
            if conn:
                if st.button("💾 Guardar Cotización en Google Sheets", use_container_width=True):
                    try:
                        folio = f"COT-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
                        nueva_data = pd.DataFrame([{
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
                        }])
                        conn.create(spreadsheet="Cotizaciones_PyME", worksheet="Cotizaciones", data=nueva_data)
                        st.success(f"✅ Cotización guardada con Folio {folio}")
                    except Exception as e:
                        st.error(f"Error al guardar en Sheets: {e}")
        else:
            st.caption("Ingresa el nombre del cliente y al menos un concepto para habilitar las acciones.")

elif menu == "📊 Historial y Seguimiento":
    st.title("📊 Panel de Seguimiento de Cotizaciones")
    if conn:
        try:
            df_historial = conn.read(spreadsheet="Cotizaciones_PyME", worksheet="Cotizaciones", ttl="0m")
            if not df_historial.empty:
                st.dataframe(df_historial, use_container_width=True)
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("Total Cotizado", f"${df_historial['Total'].sum():,.2f} MXN")
                with col_m2:
                    pendientes = len(df_historial[df_historial["Estatus"] == "Pendiente"])
                    st.metric("Cotizaciones Pendientes", pendientes)
            else:
                st.info("No hay registros en la hoja de Google Sheets.")
        except Exception as e:
            st.warning(f"Conecta tus credenciales de Google Sheets para consultar el historial. Detalle: {e}")
    else:
        st.info("Configura los secretos de conexión en Streamlit Cloud para ver el historial en vivo.")
