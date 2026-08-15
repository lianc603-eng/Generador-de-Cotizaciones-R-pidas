import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import urllib.parse

# --- Configuración de página ---
st.set_page_config(page_title="Cotizador PyME Pro", page_icon="📄", layout="wide")

# --- Columnas oficiales requeridas ---
COLUMNAS_BASE = ["Tipo", "Concepto", "Detalle", "Cantidad", "P. Unitario", "Importe"]

# --- Inicialización de Estado ---
if "items" not in st.session_state or not isinstance(st.session_state["items"], list):
    st.session_state["items"] = []

# --- Clase para Generación de PDF Profesional ---
class PDFCotizacion(FPDF):
    def __init__(self, emisor_nombre, emisor_tel):
        super().__init__()
        self.emisor_nombre = str(emisor_nombre) if emisor_nombre else "Mi Empresa"
        self.emisor_tel = str(emisor_tel) if emisor_tel else ""

    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(30, 41, 59)
        self.cell(0, 7, self.emisor_nombre.upper(), new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
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
    """Convierte texto a codificación segura para fuentes estándar FPDF (latin-1)."""
    if not texto:
        return ""
    reemplazos = {
        "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "*"
    }
    for orig, rep in reemplazos.items():
        texto = texto.replace(orig, rep)
    return str(texto).encode("latin-1", "replace").decode("latin-1")

def generar_pdf(empresa, emisor_tel, cliente, cliente_tel, items_df, total, vigencia, notas):
    pdf = PDFCotizacion(empresa, emisor_tel)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado de Cliente y Fecha
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

    # Filas de Productos y Servicios
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

        # Detalle / Alcance si existe
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

    # Notas
    if notas:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, "Notas y Condiciones de Pago:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 4, sanitizar_texto(str(notas)))

    return bytes(pdf.output())

# --- Interfaz Principal ---
st.title("📄 Cotizador PyME: Productos y Servicios")

col_emisor, col_cliente = st.columns(2)

with col_emisor:
    st.subheader("🏢 Datos de tu Empresa")
    mi_empresa = st.text_input("Nombre de tu Negocio / Marca", value="Mi Empresa")
    mi_telefono = st.text_input("Tu Teléfono de Contacto", value="9811234567")

with col_cliente:
    st.subheader("👤 Datos del Cliente")
    cliente_nombre = st.text_input("Nombre del Cliente o Empresa")
    cliente_telefono = st.text_input("Teléfono del Cliente (10 dígitos)", placeholder="9810000000")

st.divider()

# --- Pestañas para Agregar Conceptos ---
st.subheader("➕ Agregar a la Cotización")
tab_servicio, tab_producto = st.tabs(["💼 Servicios", "📦 Productos"])

# --- TAB SERVICIOS ---
with tab_servicio:
    st.caption("Cotiza asesorías, desarrollos, sesiones, proyectos, mano de obra o mantenimientos.")
    col_s1, col_s2, col_s3, col_s4 = st.columns([3, 1.2, 1.2, 1])
    with col_s1:
        serv_nombre = st.text_input("Nombre del Servicio", placeholder="Ej. Gestión de Redes / Sesión de Fotos")
    with col_s2:
        serv_unidad = st.selectbox("Unidad", ["Servicio", "Hora", "Proyecto", "Mes", "Evento"])
    with col_s3:
        serv_cant = st.number_input("Cantidad ", min_value=1.0, value=1.0, step=1.0, key="s_cant")
    with col_s4:
        serv_precio = st.number_input("Precio ($)", min_value=0.0, value=0.0, step=100.0, key="s_precio")
    
    serv_detalle = st.text_area("¿Qué incluye este servicio? (Opcional)", placeholder="Ej. Incluye entregables, revisiones y reportes.", key="s_det")
    
    if st.button("➕ Agregar Servicio", use_container_width=True):
        if serv_nombre.strip():
            st.session_state["items"].append({
                "Tipo": str(serv_unidad),
                "Concepto": serv_nombre.strip(),
                "Detalle": serv_detalle.strip(),
                "Cantidad": float(serv_cant),
                "P. Unitario": float(serv_precio),
                "Importe": float(serv_cant * serv_precio)
            })
            st.rerun()
        else:
            st.warning("Escribe el nombre del servicio antes de agregar.")

# --- TAB PRODUCTOS ---
with tab_producto:
    st.caption("Cotiza artículos físicos, suministros, piezas, paquetes o materiales.")
    col_p1, col_p2, col_p3, col_p4 = st.columns([3, 1.2, 1.2, 1])
    with col_p1:
        prod_nombre = st.text_input("Nombre del Producto", placeholder="Ej. Cuadro Canvas / Kit de Accesorios")
    with col_p2:
        prod_unidad = st.selectbox("Presentación", ["Pieza", "Kit", "Paquete", "Caja", "Metro", "Lote"])
    with col_p3:
        prod_cant = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0, key="p_cant")
    with col_p4:
        prod_precio = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=50.0, key="p_precio")
    
    prod_detalle = st.text_area("Especificaciones o contenido del producto (Opcional)", placeholder="Ej. Materiales, dimensiones o acabados.", key="p_det")
    
    if st.button("➕ Agregar Producto", use_container_width=True):
        if prod_nombre.strip():
            st.session_state["items"].append({
                "Tipo": str(prod_unidad),
                "Concepto": prod_nombre.strip(),
                "Detalle": prod_detalle.strip(),
                "Cantidad": float(prod_cant),
                "P. Unitario": float(prod_precio),
                "Importe": float(prod_cant * prod_precio)
            })
            st.rerun()
        else:
            st.warning("Escribe el nombre del producto antes de agregar.")

st.divider()

# --- Normalización y Resumen de Datos ---
lista_actual = st.session_state.get("items", [])

# Asegurar que cada registro tenga las columnas obligatorias
items_normalizados = []
if isinstance(lista_actual, list):
    for it in lista_actual:
        if isinstance(it, dict):
            items_normalizados.append({
                "Tipo": it.get("Tipo", "General"),
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

    if st.button("🗑️ Limpiar todos los conceptos"):
        st.session_state["items"] = []
        st.rerun()
else:
    df_items = pd.DataFrame(columns=COLUMNAS_BASE)
    total_cotizacion = 0.0
    st.info("Aún no has agregado servicios o productos a la cotización.")

st.divider()

# --- Opciones Finales y Exportación ---
col_opt, col_actions = st.columns([1, 1])

with col_opt:
    vigencia_dias = st.slider("Días de vigencia", 1, 30, 7)
    notas_adicionales = st.text_area(
        "Condiciones de entrega y pago", 
        value="Anticipo del 50% para inicio y 50% al entregar.\nTiempo de entrega: 3 a 5 días hábiles."
    )

with col_actions:
    st.subheader("🚀 Exportar y Compartir")
    if not df_items.empty and cliente_nombre and cliente_nombre.strip():
        pdf_bytes = generar_pdf(
            mi_empresa, mi_telefono, cliente_nombre, 
            cliente_telefono, df_items, total_cotizacion, 
            vigencia_dias, notas_adicionales
        )
        
        # Botón de Descarga PDF
        st.download_button(
            label="📥 Descargar Cotización en PDF",
            data=pdf_bytes,
            file_name=f"Cotizacion_{cliente_nombre.strip().replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        # Enlace a WhatsApp con desglose
        resumen_lineas = []
        for _, item in df_items.iterrows():
            resumen_lineas.append(f"• *{item['Concepto']}* ({item['Cantidad']:.0f} {item['Tipo']}) -> ${item['Importe']:,.2f}")
        resumen_texto = "\n".join(resumen_lineas)

        mensaje_wa = (
            f"Hola *{cliente_nombre.strip()}*, te comparto el resumen de tu cotización con *{mi_empresa}*:\n\n"
            f"{resumen_texto}\n\n"
            f"💰 *TOTAL:* ${total_cotizacion:,.2f} MXN\n"
            f"⏳ *Vigencia:* {vigencia_dias} días.\n\n"
            f"Quedo a tu disposición si deseas confirmar o ajustar algún detalle."
        )
        mensaje_encoded = urllib.parse.quote(mensaje_wa)
        tel_formateado = "".join(filter(str.isdigit, cliente_telefono))
        wa_url = f"https://wa.me/{tel_formateado}?text={mensaje_encoded}"

        st.link_button("📲 Enviar Resumen por WhatsApp", wa_url, use_container_width=True)
    else:
        st.caption("Completa los datos del cliente y agrega al menos un concepto para habilitar la descarga del PDF y el botón de WhatsApp.")
