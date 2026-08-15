import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import urllib.parse

# --- Configuración de página ---
st.set_page_config(page_title="Cotizador PyME Pro", page_icon="📄", layout="wide")

# --- Inicialización de Estado ---
if "items" not in st.session_state or not isinstance(st.session_state["items"], list):
    st.session_state["items"] = []

# --- Clase para Generación de PDF ---
class PDFCotizacion(FPDF):
    def __init__(self, emisor_nombre, emisor_tel):
        super().__init__()
        self.emisor_nombre = str(emisor_nombre) if emisor_nombre else "Mi Empresa"
        self.emisor_tel = str(emisor_tel) if emisor_tel else ""

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 8, self.emisor_nombre.upper(), new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Contacto: {self.emisor_tel}", new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(0, 0, 0)
        self.ln(5)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "Documento emitido sin validez fiscal directa - Generado con Cotizador PyME", align="C")

def generar_pdf(empresa, emisor_tel, cliente, cliente_tel, items_df, total, vigencia, notas):
    pdf = PDFCotizacion(empresa, emisor_tel)
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(100, 6, f"CLIENTE: {cliente}")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.cell(100, 6, f"Tel: {cliente_tel}")
    pdf.cell(90, 6, f"Válido por: {vigencia} días", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(6)

    # Tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(100, 7, "Descripción", border=1, fill=True)
    pdf.cell(25, 7, "Cant.", border=1, align="C", fill=True)
    pdf.cell(30, 7, "P. Unitario", border=1, align="R", fill=True)
    pdf.cell(35, 7, "Subtotal", border=1, align="R", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for _, row in items_df.iterrows():
        pdf.cell(100, 6, str(row["Concepto"]), border=1)
        pdf.cell(25, 6, f"{float(row['Cantidad']):.2f}", border=1, align="C")
        pdf.cell(30, 6, f"${float(row['P. Unitario']):,.2f}", border=1, align="R")
        pdf.cell(35, 6, f"${float(row['Importe']):,.2f}", border=1, align="R")
        pdf.ln()

    # Total
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(155, 7, "TOTAL:", border=1, align="R")
    pdf.cell(35, 7, f"${total:,.2f}", border=1, align="R")
    pdf.ln(8)

    # Notas
    if notas:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, "Notas y Condiciones:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 4, str(notas))

    return bytes(pdf.output())

# --- Interfaz Principal ---
st.title("📄 Generador de Cotizaciones para PyMEs")

col_emisor, col_cliente = st.columns(2)

with col_emisor:
    st.subheader("Tus Datos")
    mi_empresa = st.text_input("Nombre de tu Negocio / Marca", value="Mi Empresa")
    mi_telefono = st.text_input("Tu Teléfono de Contacto", value="9811234567")

with col_cliente:
    st.subheader("Datos del Cliente")
    cliente_nombre = st.text_input("Nombre del Cliente")
    cliente_telefono = st.text_input("Teléfono del Cliente (10 dígitos)", placeholder="9810000000")

st.divider()

# --- Agregar Conceptos ---
st.subheader("Agregar Productos / Servicios")
col_c1, col_c2, col_c3, col_c4 = st.columns([3, 1, 1, 1])

with col_c1:
    concepto = st.text_input("Descripción del servicio o producto")
with col_c2:
    cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
with col_c3:
    precio = st.number_input("Precio Unitario ($)", min_value=0.0, value=0.0, step=50.0)
with col_c4:
    st.write("")
    st.write("")
    if st.button("➕ Agregar", use_container_width=True):
        if concepto and concepto.strip():
            st.session_state["items"].append({
                "Concepto": concepto.strip(),
                "Cantidad": float(cantidad),
                "P. Unitario": float(precio),
                "Importe": float(cantidad * precio)
            })
            st.rerun()

# --- Visualización de Datos ---
lista_actual = st.session_state.get("items", [])

if isinstance(lista_actual, list) and len(lista_actual) > 0:
    df_items = pd.DataFrame(lista_actual)
    st.dataframe(df_items, use_container_width=True, hide_index=True)
    
    total_cotizacion = float(df_items["Importe"].sum())
    st.metric(label="Total Cotización", value=f"${total_cotizacion:,.2f}")

    if st.button("🗑️ Limpiar lista de conceptos"):
        st.session_state["items"] = []
        st.rerun()
else:
    df_items = pd.DataFrame(columns=["Concepto", "Cantidad", "P. Unitario", "Importe"])
    total_cotizacion = 0.0
    st.info("Aún no has agregado productos o servicios a la cotización.")

st.divider()

# --- Opciones Finales y Exportación ---
col_opt, col_actions = st.columns([1, 1])

with col_opt:
    vigencia_dias = st.slider("Días de vigencia", 1, 30, 7)
    notas_adicionales = st.text_area("Condiciones de pago o notas", value="Pago 50% anticipo y 50% contra entrega.")

with col_actions:
    st.subheader("Exportar y Notificar")
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

        # Enlace a WhatsApp
        mensaje_wa = (
            f"Hola {cliente_nombre.strip()}, te comparto el resumen de tu cotización de *{mi_empresa}*:\n\n"
            f"💰 *Total:* ${total_cotizacion:,.2f} MXN\n"
            f"⏳ *Vigencia:* {vigencia_dias} días.\n\n"
            f"Quedo a tu disposición para confirmar el pedido."
        )
        mensaje_encoded = urllib.parse.quote(mensaje_wa)
        tel_formateado = "".join(filter(str.isdigit, cliente_telefono))
        wa_url = f"https://wa.me/{tel_formateado}?text={mensaje_encoded}"

        st.link_button("📲 Enviar Resumen por WhatsApp", wa_url, use_container_width=True)
    else:
        st.caption("Completa los datos del cliente y agrega al menos un concepto para habilitar la descarga del PDF y el envío por WhatsApp.")
