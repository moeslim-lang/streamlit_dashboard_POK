import warnings
warnings.simplefilter(action='ignore', category=UserWarning)

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import plotly.express as px

FILE_NAME = "POK contoh.xlsx"

# =======================
# Load Data
# =======================
@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)

        required_cols = ['UNIT', 'JUMLAH', 'KODE']
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Kolom '{col}' tidak ditemukan dalam file Excel.")
                return pd.DataFrame()

        df['UNIT'] = df['UNIT'].fillna("")
        df['KODE'] = df['KODE'].fillna("").astype(str)
        if 'JUMLAH' in df.columns:
            df['JUMLAH'] = pd.to_numeric(df['JUMLAH'], errors='coerce')
        if 'HARGA' in df.columns:
            df['HARGA'] = pd.to_numeric(df['HARGA'], errors='coerce')
        if 'VOL' in df.columns:
            df['VOL'] = pd.to_numeric(df['VOL'], errors='coerce')
        if 'URAIAN' in df.columns:
            df['URAIAN'] = df['URAIAN'].fillna("")
        # Kolom tambahan
        for col in ['SAT','RO','SD']:
            if col in df.columns:
                df[col] = df[col].fillna("")

        return df
    except:
        return pd.DataFrame()

# =======================
# Format ribuan
# =======================
def format_ribuan(n):
    return "{:,.0f}".format(n).replace(",", ".")

# =======================
# Tampil AgGrid dengan kolom fix (Halaman Rincian)
# =======================
def display_aggrid(df, right_align_cols=None):
    df_copy = df.copy()

    # Konversi numerik agar JSON serializable
    for col in df_copy.columns:
        if pd.api.types.is_integer_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].apply(lambda x: int(x) if pd.notnull(x) else "")
        elif pd.api.types.is_float_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].apply(lambda x: float(x) if pd.notnull(x) else "")

    gb = GridOptionsBuilder.from_dataframe(df_copy)
    gb.configure_default_column(resizable=True, wrapText=True, autoHeight=False,
                                cellStyle={'padding':'2px 4px', 'line-height':'1.2'})

    # Right align kolom angka
    if right_align_cols:
        for col in right_align_cols:
            if col in df_copy.columns:
                gb.configure_column(col, type=["numericColumn","numberColumnFilter"],
                                    cellStyle={'textAlign': 'right', 'padding':'2px 4px', 'line-height':'1.2'})

    gb.configure_grid_options(rowHeight=25)

    # Lebar kolom fix sesuai request
    width_map = {
        'UNIT': 120,
        'MAK': 120,
        'KODE': 60,
        'URAIAN': 550,
        'VOL': 80,
        'SAT': 70,
        'HARGA': 80,
        'JUMLAH': 120,
        'RO': 50,
        'SD': 50
    }
    for col, w in width_map.items():
        if col in df_copy.columns:
            gb.configure_column(col, minWidth=w, maxWidth=w)

    gridOptions = gb.build()

    AgGrid(
        df_copy,
        gridOptions=gridOptions,
        height=500,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False
    )

# =======================
# Halaman Rekap (Tabel + Grafik)
# =======================
def show_rekap(df):
    st.header("Rekapitulasi Total Anggaran Per Unit Kerja")

    # Ambil KODE 6 digit untuk rekap
    df_rekap = df[df['KODE'].str.match(r'^\d{6}$', na=False)]
    df_rekap = df_rekap.groupby('UNIT', as_index=False)['JUMLAH'].sum()
    df_rekap = df_rekap[df_rekap['UNIT'] != '']

    # Tambahkan TOTAL
    total_anggaran = df_rekap['JUMLAH'].sum()
    total_row = pd.DataFrame({'UNIT':['TOTAL'], 'JUMLAH':[total_anggaran]})
    df_display = pd.concat([df_rekap, total_row], ignore_index=True)

    # Format ribuan untuk tabel
    df_display['JUMLAH'] = df_display['JUMLAH'].apply(lambda x: format_ribuan(x))

    # Layout 2 kolom: tabel + grafik (grafik lebih besar)
    col1, col2 = st.columns([1, 2])  # proporsi tabel: grafik = 1:2

    with col1:
        # Tampilkan tabel
        gb = GridOptionsBuilder.from_dataframe(df_display[['UNIT','JUMLAH']])
        gb.configure_default_column(resizable=True, wrapText=True, autoHeight=False,
                                    cellStyle={'padding':'2px 4px', 'line-height':'1.2'})
        gb.configure_column('JUMLAH', type=["numericColumn","numberColumnFilter"],
                            cellStyle={'textAlign': 'right', 'padding':'2px 4px', 'line-height':'1.2'})
        gb.configure_grid_options(rowHeight=25)
        gridOptions = gb.build()

        AgGrid(
            df_display[['UNIT','JUMLAH']],
            gridOptions=gridOptions,
            height=500,
            fit_columns_on_grid_load=True,
            update_mode=GridUpdateMode.NO_UPDATE,
            enable_enterprise_modules=False
        )

    with col2:
        # Grafik batang total anggaran per unit
        fig = px.bar(df_rekap, x='UNIT', y='JUMLAH',
                     labels={'UNIT':'Unit','JUMLAH':'Total Anggaran'},
                     text=df_rekap['JUMLAH'].apply(lambda x: format_ribuan(x)))
        fig.update_traces(textposition='outside', marker_color='teal')
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=500)
        st.plotly_chart(fig, width='stretch')  # perbaiki warning

# =======================
# Halaman Rincian (tidak diubah)
# =======================
def show_rincian(df):
    st.header("Rincian Data Anggaran Per Unit Kerja")
    st.sidebar.header("Filter Data Rincian")

    units = df['UNIT'][df['UNIT'] != ''].unique().tolist()
    selected = st.sidebar.selectbox("Pilih Unit Kerja:", ["Semua Unit"] + units)
    df_filtered = df if selected=="Semua Unit" else df[df['UNIT']==selected]

    # Total hanya untuk KODE 1–2 huruf
    mask_total = df_filtered['KODE'].str.match(r'^[A-Za-z]{1,2}$', na=False)
    total = pd.to_numeric(df_filtered.loc[mask_total,'JUMLAH'], errors='coerce').sum(skipna=True)
    st.metric(f"Total Anggaran Unit ({selected})", format_ribuan(total))

    df_display = df_filtered.fillna("")
    for col in ['JUMLAH','HARGA']:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: format_ribuan(float(x)) if x!="" else "")
    if 'VOL' in df_display.columns:
        df_display['VOL'] = df_display['VOL'].apply(lambda x: str(int(x)) if x!="" else "")

    right_cols = [col for col in ['JUMLAH','HARGA','VOL'] if col in df_display.columns]
    display_aggrid(df_display, right_align_cols=right_cols)

# =======================
# Main App
# =======================
def main():
    st.set_page_config(layout="wide", page_title="Dashboard POK TA 2025 - DIPA 7")
    df = load_data(FILE_NAME)
    if df.empty:
        st.error("Data kosong")
        return

    st.title("💸 Dashboard Data POK Satker TA 2025 - DIPA 7")
    st.sidebar.header("Pilihan Tampilan")
    page = st.sidebar.radio("Pilih Halaman:", ["Rekap Per Satker","Rincian Unit"])

    if page=="Rekap Per Satker":
        show_rekap(df)
    else:
        show_rincian(df)

if __name__=="__main__":
    main()
