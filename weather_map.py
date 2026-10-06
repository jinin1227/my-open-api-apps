"""
Interactive Weather Dashboard
-----------------------------
지도에서 클릭한 위치의 시간별 기온(48시간)을 Open-Meteo API로 불러와
표, 요약 지표, 선 그래프로 보여주는 Streamlit 앱.

실행 방법:
    pip install -r requirements.txt
    streamlit run weather_dashboard.py
"""

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

# ── 1. 설정값 ────────────────────────────────────────────────
API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10                     # 서버 응답을 최대 10초까지만 기다림
KOREA_CENTER = (36.5, 127.5)     # 지도 처음 중심 좌표
START_ZOOM = 6

st.set_page_config(page_title="Interactive Weather Dashboard", page_icon="🌡️", layout="wide")


# ── 2. 날씨 데이터 불러오기 (결과를 10분 동안 캐시) ────────────
@st.cache_data(ttl=600, show_spinner=False)
def load_hourly_temperature(lat: float, lon: float) -> pd.DataFrame:
    """위도·경도로 시간별 기온을 받아 시간을 인덱스로 한 DataFrame을 돌려준다."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "forecast_days": 2,
        "timezone": "auto",      # 클릭한 지역의 현지 시간으로 받아옴
    }
    response = requests.get(API_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()                  # 오류 코드(400, 500 등)면 예외 발생
    hourly = response.json()["hourly"]           # 응답에 hourly가 없으면 KeyError 발생

    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "Temperature (°C)": hourly["temperature_2m"],
    })
    return df.set_index("time")


# ── 3. 지도 그리기 ───────────────────────────────────────────
st.title("Interactive Weather Dashboard")
st.write("Click anywhere on the map to see the hourly temperature forecast for the next 48 hours.")

weather_map = folium.Map(location=KOREA_CENTER, zoom_start=START_ZOOM)
map_state = st_folium(
    weather_map,
    height=450,
    use_container_width=True,
    returned_objects=["last_clicked"],   # 클릭했을 때만 앱이 다시 실행되도록 함
)

clicked = map_state.get("last_clicked") if map_state else None
if not clicked:
    st.info("Click a location on the map to load its temperature forecast.")
    st.stop()

# 클릭 좌표를 소수점 3자리로 반올림
lat = round(clicked["lat"], 3)
# 지도를 옆으로 계속 넘기면 경도가 180을 넘어갈 수 있어서 -180~180 범위로 되돌림
lon = round((clicked["lng"] + 180) % 360 - 180, 3)


# ── 4. 데이터 요청 ───────────────────────────────────────────
try:
    with st.spinner("Loading the forecast..."):
        df = load_hourly_temperature(lat, lon)
except (requests.RequestException, KeyError, ValueError):
    st.error("The Open-Meteo weather service can't be reached right now. "
             "Check your internet connection and try again in a minute.")
    st.stop()

temps = df["Temperature (°C)"]
if temps.dropna().empty:
    st.warning(f"No temperature data is available for {lat}, {lon}. Try a different location.")
    st.stop()


# ── 5. 요약 지표 3개 ─────────────────────────────────────────
st.subheader(f"Forecast for {lat}, {lon}")

first_time, first_temp = temps.index[0], temps.iloc[0]
high_time, high_temp = temps.idxmax(), temps.max()
low_time, low_temp = temps.idxmin(), temps.min()

col1, col2, col3 = st.columns(3)
col1.metric("First hour", f"{first_temp:.1f} °C")
col1.caption(first_time.strftime("%b %d, %H:%M"))
col2.metric("Highest", f"{high_temp:.1f} °C")
col2.caption(high_time.strftime("%b %d, %H:%M"))
col3.metric("Lowest", f"{low_temp:.1f} °C")
col3.caption(low_time.strftime("%b %d, %H:%M"))


# ── 6. 그래프와 표 ───────────────────────────────────────────
st.line_chart(temps)

with st.expander("Hourly data table"):
    st.dataframe(df)


# ── 7. 출처 표기 ─────────────────────────────────────────────
st.divider()
st.caption("Weather data by Open-Meteo.com (CC BY 4.0). Map data © OpenStreetMap contributors.")
