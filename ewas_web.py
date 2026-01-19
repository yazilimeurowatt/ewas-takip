import streamlit as st
import pandas as pd
import os
import time
import requests
import io

# --- Sayfa Ayarları (En Başta Olmalı) ---
st.set_page_config(
    page_title="E.W.A.S Web Paneli",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Özel CSS (Dark Mode & Modern Görünüm) ---
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    
    /* Tablo Başlıkları */
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    /* Metrik Kutuları */
    div[data-testid="stMetric"] {
        background-color: #2d2d2d;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #3498db;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #ffffff;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 16px;
        color: #aaaaaa;
    }
    
    /* Tablo */
    div[data-testid="stDataFrame"] {
        background-color: #2d2d2d;
        padding: 10px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Dosya Yolu ve Ayarlar ---
CONFIG_FILE = "config.txt"
DEFAULT_FILE = "SİPARİŞ LİSTESİ.xlsx"

# --- GİRİŞ GÜVENLİĞİ ---
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "eurowatt54": # Şifre buraya tanımlandı
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Şifreyi session'dan sil
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # İlk açılış, şifre sor
        st.text_input(
            "🔑 Lütfen Giriş Şifresini Girin:", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Hatalı şifre
        st.text_input(
            "🔑 Lütfen Giriş Şifresini Girin:", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Şifre hatalı.")
        return False
    else:
        # Şifre doğru
        return True

if not check_password():
    st.stop()

# --- Google Drive Link Dönüştürücü ---
def get_drive_download_url(url):
    """Google Drive view linkini direkt indirme linkine çevirir."""
    if "drive.google.com" in url and "/d/" in url:
        file_id = url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def get_excel_path():
    # 1. Önce Config dosyasına bak (Link veya Dosya Yolu olabilir)
    if os.path.exists(CONFIG_FILE):
        try:
            # Önce utf-8 dene
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except UnicodeDecodeError:
            try:
                # Olmazsa utf-16 dene (Windows bazen böyle kaydeder)
                with open(CONFIG_FILE, "r", encoding="utf-16") as f:
                    content = f.read().strip()
            except Exception:
                return None # Okunamazsa dosyayı yok say
        
        # Eğer içerik http ile başlıyorsa (Link ise)
        if content.startswith("http"):
            return get_drive_download_url(content)
        # Yerel dosya yolu ise ve varsa
        if os.path.exists(content):
            return content
    
    # 2. Varsayılan yerel dosyaya bak
    if os.path.exists(DEFAULT_FILE):
        return DEFAULT_FILE
    
    return None

excel_path = get_excel_path()

# --- Başlık ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("🏭 E.W.A.S - Açık Sipariş Takibi")
    st.markdown("*Üretim ve Takip Yönetim Paneli*")
with col_head2:
    if st.button("Çıkış Yap"):
        del st.session_state["password_correct"]
        st.rerun()

if not excel_path:
    st.error(f"⚠️ Veri kaynağı bulunamadı! 'config.txt' içine dosya yolu veya Google Drive linki yapıştırın.")
    st.stop()

# --- Veri Yükleme Fonksiyonu ---
@st.cache_data(ttl=60) # Drive için süreyi biraz artırdık (60s)
def load_data(path):
    try:
        # URL Kontrolü (Drive vb.)
        if str(path).startswith("http"):
            response = requests.get(path)
            if response.status_code == 200:
                file_stream = io.BytesIO(response.content)
                df = pd.read_excel(file_stream, engine="openpyxl")
            else:
                st.error(f"Dosya indirilemedi. Hata Kodu: {response.status_code}")
                return pd.DataFrame()
        else:
            # Yerel Dosya
            df = pd.read_excel(path, engine="openpyxl")
        
        # Filtreleme: Sadece Boru ve Özel
        if "Bölüm" in df.columns:
            df["Bölüm_Lower"] = df["Bölüm"].astype(str).str.lower()
            df = df[df["Bölüm_Lower"].isin(["boru", "özel", "ozel"])]
            
            # Tarih Formatı Düzeltme
            if "Termin Süresi" in df.columns:
                df["Termin Süresi"] = pd.to_datetime(df["Termin Süresi"], dayfirst=False, errors='coerce')

            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Dosya okunurken hata oluştu: {e}")
        return pd.DataFrame()

# Veriyi Yükle
df = load_data(excel_path)

if df.empty:
    st.warning("📭 Gösterilecek veri bulunamadı veya Excel dosyası boş.")
    st.stop()

# --- Arayüz Kontrolleri ---
col1, col2 = st.columns([3, 1])
with col1:
    search_input = st.text_input("🔍 Hızlı Arama", placeholder="Fiş No, Firma veya Dosya Adı yazın...")
with col2:
    if st.button("🔄 LİSTEYİ YENİLE", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Filtreleme Mantığı ---
df_display = df.copy()

if search_input:
    # Tüm sütunlarda arama yap
    mask = df_display.astype(str).apply(lambda x: x.str.contains(search_input, case=False, na=False)).any(axis=1)
    df_display = df_display[mask]

# --- İstatistikler ---
total_orders = len(df_display)
count_boru = len(df_display[df_display["Bölüm_Lower"] == "boru"])
count_ozel = len(df_display[df_display["Bölüm_Lower"].isin(["özel", "ozel"])])

# Yaklaşan Termin Hesaplama
today = pd.Timestamp.now().normalize()
next_week = today + pd.Timedelta(days=7)
upcoming_orders = df_display[
    (df_display["Termin Süresi"] <= next_week) & 
    (df_display["Termin Süresi"].notna())
]
count_upcoming = len(upcoming_orders)

# Metrikleri Göster
m1, m2, m3, m4 = st.columns(4)
m1.metric("Toplam Sipariş", total_orders, delta="Adet", delta_color="off")
m2.metric("Boru Bölümü", count_boru, delta="Adet", delta_color="off")
m3.metric("Özel Bölüm", count_ozel, delta="Adet", delta_color="off")
m4.metric("🚨 Yaklaşan / Geciken", count_upcoming, delta=f"{count_upcoming} Acil", delta_color="inverse")

# --- Tabloyu Düzenleme ---
# Gösterilecek Sütunlar
cols_to_show = ["Bölüm", "Dosya Adı", "Fiş No", "Mail Tarihi", "Resim Kodu", "Açıklaması", "Miktar", "Birimi", "Termin Süresi"]
# Mevcut olanları seç
final_cols = [c for c in cols_to_show if c in df_display.columns]

# Tarihi okunabilir formata çevir (YYYY-MM-DD yerine DD.MM.YYYY)
if "Termin Süresi" in final_cols:
    df_display["Termin Süresi"] = df_display["Termin Süresi"].dt.strftime('%d.%m.%Y')
    # NaT (Tarih yok) olanları boş string yap
    df_display["Termin Süresi"] = df_display["Termin Süresi"].fillna("")

st.markdown("### 📋 Sipariş Listesi")
st.dataframe(
    df_display[final_cols],
    use_container_width=True,
    hide_index=True,
    height=600
)

# --- Footer ---
st.divider()
st.caption(f"Veri Kaynağı: `{excel_path}` | Sistem Saati: {time.strftime('%H:%M:%S')}")
if count_upcoming > 0:
    st.warning(f"⚠️ DİKKAT: Toplam {count_upcoming} adet siparişin teslim tarihi geçmiş veya 7 günden az kalmış!")
