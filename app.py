import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
import time
from pyproj import Transformer
import ezdxf
import io

st.set_page_config(page_title="برداشت فیبر نوری", layout="wide")

st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

st.title("📍 ابزار برداشت میدانی فیبر نوری")

# حافظه برنامه
if 'points' not in st.session_state:
    st.session_state.points = []
if 'draw_line' not in st.session_state:
    st.session_state.draw_line = False

# --- تابع تبدیل مختصات WGS84 به UTM ---
def get_utm_zone(lon):
    return int((lon + 180) / 6) + 1

def convert_to_utm(lat, lon):
    zone = get_utm_zone(lon)
    epsg_code = f"epsg:326{zone:02d}" if lat >= 0 else f"epsg:327{zone:02d}"
    transformer = Transformer.from_crs("epsg:4326", epsg_code, always_xy=True)
    utm_x, utm_y = transformer.transform(lon, lat)
    return utm_x, utm_y, zone

# --- تابع تولید فایل DXF ---
def generate_dxf(points):
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    
    # تعریف لایه‌ها
    doc.layers.add(name="PATH_LINE", color=5)      # آبی - مسیر
    doc.layers.add(name="POINTS", color=1)          # قرمز - نقاط
    doc.layers.add(name="LABELS", color=3)          # سبز - برچسب‌ها

    # رسم نقاط
    for p in points:
        x, y = p['utm_x'], p['utm_y']
        msp.add_point((x, y), dxfattribs={"layer": "POINTS"})
        msp.add_text(
            f"P{p['index']}",
            dxfattribs={"layer": "LABELS", "height": 0.5}
        ).set_placement((x, y + 0.5, 0))

    # رسم خط مسیر
    if len(points) > 1:
        polyline = [(p['utm_x'], p['utm_y']) for p in points]
        msp.add_lwpolyline(polyline, dxfattribs={"layer": "PATH_LINE"})

    # ذخیره در حافظه موقت
    stream = io.StringIO()
    doc.write_text(stream)
    return stream.getvalue().encode('utf-8')

# --- دریافت لوکیشن ---
location = get_geolocation()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🎛️ کنترل پنل")

    if location:
        lat = location['coords']['latitude']
        lon = location['coords']['longitude']
        acc = location['coords']['accuracy']

        # رنگ‌بندی دقت
        if acc <= 5:
            st.success(f"✅ دقت GPS: {acc:.1f} متر (عالی)")
        elif acc <= 15:
            st.warning(f"⚠️ دقت GPS: {acc:.1f} متر (متوسط)")
        else:
            st.error(f"❌ دقت GPS: {acc:.1f} متر (ضعیف - توصیه نمی‌شود)")

        if st.button("📌 ثبت نقطه (باکس/تغییر مسیر)", use_container_width=True):
            ux, uy, zone = convert_to_utm(lat, lon)
            st.session_state.points.append({
                "index": len(st.session_state.points) + 1,
                "time": time.strftime("%H:%M:%S"),
                "lat": lat, "lon": lon,
                "utm_x": ux, "utm_y": uy,
                "zone": zone,
                "acc": acc
            })
            st.toast(f"نقطه P{len(st.session_state.points)} ثبت شد | UTM Zone: {zone}")

        if st.button("🛤️ رسم مسیر", use_container_width=True):
            st.session_state.draw_line = True

        if st.button("↩️ حذف آخرین نقطه", use_container_width=True):
            if st.session_state.points:
                st.session_state.points.pop()
                st.rerun()

        if st.button("🗑️ پاکسازی همه", type="primary", use_container_width=True):
            st.session_state.points = []
            st.session_state.draw_line = False
            st.rerun()

    else:
        st.info("🔄 در حال دریافت لوکیشن... لطفاً دسترسی موقعیت را تایید کنید.")

    # جدول نقاط
    if st.session_state.points:
        st.write("---")
        st.write("📊 نقاط ثبت شده:")
        df = pd.DataFrame(st.session_state.points)
        st.dataframe(
            df[["index", "time", "lat", "lon", "utm_x", "utm_y", "acc"]],
            hide_index=True,
            use_container_width=True
        )

        st.write("---")
        st.write("📥 خروجی:")
        # خروجی CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📄 دانلود CSV",
            csv,
            "fiber_points.csv",
            "text/csv"
        )
        # خروجی DXF
        dxf_data = generate_dxf(st.session_state.points)
        st.download_button(
            "📐 دانلود DXF (اتوکد)",
            dxf_data,
            "fiber_route.dxf",
            "application/dxf"
        )

with col2:
    center = [st.session_state.points[-1]['lat'], st.session_state.points[-1]['lon']] \
        if st.session_state.points else [35.6892, 51.3890]

    m = folium.Map(location=center, zoom_start=18, control_scale=True)

    path_coords = []
    for p in st.session_state.points:
        path_coords.append([p['lat'], p['lon']])
        # رنگ مارکر بر اساس دقت
        color = 'green' if p['acc'] <= 5 else 'orange' if p['acc'] <= 15 else 'red'
        folium.Marker(
            location=[p['lat'], p['lon']],
            popup=f"P{p['index']} | دقت: {p['acc']:.1f}m",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)

    if st.session_state.draw_line and len(path_coords) > 1:
        folium.PolyLine(path_coords, color="blue", weight=5, opacity=0.7).add_to(m)

    st_folium(m, width="100%", height=600, key="main_map")
