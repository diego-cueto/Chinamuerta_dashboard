# -*- coding: utf-8 -*-
"""
Dashboard tipo compendio de abundancia de flora (QGIS+Python GIS power).
Cargue el Excel 'flora_abundancia_graficos.xlsx' (hoja 'conteo_agregado').

Versión: 1.2 — Arregla saltos en el eje X (Categorías) y desbordamiento de color (range_color).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).resolve().parent
DEFAULT_XLSX = BASE / "flora_abundancia_graficos.xlsx"

# Función para ordenar textos con números de forma humana (1, 2, 3, 10, 11... no 1, 10, 11, 2, 3)
def orden_natural(texto):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(texto))]


@st.cache_data
def load_conteo(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="conteo_agregado")
    
    # Limpieza a prueba de balas: Extraer solo los números por si vienen con espacios o letras
    df["total"] = df["total"].astype(str).str.extract(r'(\d+\.?\d*)')[0]
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0).astype(int)
    
    # Asegurar que la parcela sea texto para que Plotly no invente espacios en blanco
    df["parcela (par)"] = df["parcela (par)"].astype(str).str.strip()
    return df


def main() -> None:
    st.set_page_config(page_title="Compendio abundancia flora", layout="wide")
    st.title("Compendio — abundancia por parcela y especie")
    st.caption(
        "Vista única de toda la información: calor global, detalle por parcela y tablas descargables."
    )

    xlsx_path = st.sidebar.text_input(
        "Ruta al Excel",
        value=str(DEFAULT_XLSX),
    )
    path = Path(xlsx_path)
    if not path.is_file():
        st.error(f"No se encuentra el archivo: {path}")
        return

    df = load_conteo(str(path))
    col_par = "parcela (par)"
    col_sp = "especie.wrk"
    col_tot = "total"

    # =========================================================================================
    # SIDEBAR
    # =========================================================================================
    st.sidebar.markdown("---")
    st.sidebar.subheader("Diseño del Mapa de Calor")
    
    max_individuos_db = int(df[col_tot].max())
    zmax_slider = st.sidebar.slider(
        "Tope de color (zmax)",
        min_value=1,
        max_value=max_individuos_db,
        value=min(200, max_individuos_db),
        step=1,
        help="Cualquier valor sobre este tope se verá del verde más oscuro. "
             "Evita que un solo outlier (ej. 2000) decolore el resto del mapa.",
    )

    # Matriz pivot
    matrix = df.pivot_table(
        index=col_sp,
        columns=col_par,
        values=col_tot,
        aggfunc="sum",
        fill_value=0,
    )
    
    # Ordenar especies alfabéticamente y parcelas de forma natural
    matrix = matrix.sort_index()
    parcelas_ordenadas = sorted(matrix.columns, key=orden_natural)
    matrix = matrix[parcelas_ordenadas]

    tab_heat, tab_bar, tab_tbl = st.tabs(
        ["Mapa de calor (compendio)", "Barras por parcela", "Tabla larga"]
    )

    with tab_heat:
        st.markdown(
            "**Todas las parcelas y taxones en un solo panel.** "
            "Controle el contraste del color en la barra lateral."
        )
        
        fig = px.imshow(
            matrix,
            labels=dict(x="Parcela", y="Especie", color="Individuos"),
            aspect="auto",
            height=min(900, 400 + 12 * len(matrix.index)),
            color_continuous_scale=["white", "yellow", "green"],
            # SOLUCIÓN 1: range_color fuerza estrictamente los límites, evitando renderizados en blanco
            range_color=[0, zmax_slider] 
        )
        
        # SOLUCIÓN 2: type='category' le prohíbe a Plotly crear ejes matemáticos con saltos vacíos
        fig.update_xaxes(type='category', side="bottom", tickangle=-45)
        
        st.plotly_chart(fig, use_container_width=True)

    with tab_bar:
        # Usamos el mismo orden natural para el selector de parcelas
        p_sel = st.selectbox("Seleccionar parcela", parcelas_ordenadas, index=0)
        sub = df[df[col_par] == p_sel].sort_values(col_tot, ascending=False)
        
        fig2 = px.bar(
            sub,
            x=col_sp,
            y=col_tot,
            color=col_sp,
            text=col_tot,
        )
        fig2.update_traces(textposition="outside", texttemplate="%{text}")
        fig2.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Individuos (total)",
            title=f"Parcela {p_sel}",
            height=520,
        )
        fig2.update_xaxes(tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.subheader(f"Datos crudos para Parcela {p_sel}")
        csv_bar = sub.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            f"Descargar datos de Parcela {p_sel} como CSV",
            data=csv_bar,
            file_name=f"flora_abundancia_parcela_{p_sel}.csv",
            mime="text/csv",
        )

    with tab_tbl:
        st.dataframe(df, use_container_width=True, height=420)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Descargar conteo_agregado como CSV",
            data=csv,
            file_name="conteo_agregado.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()