"""
Met Museum Artwork Search
-------------------------
The Metropolitan Museum of Art 컬렉션 API로 작품을 검색해
이미지와 함께 3열 그리드로 보여주는 Streamlit 앱.

실행 방법:
    pip install streamlit requests
    streamlit run met_art_search.py
"""

import requests
import streamlit as st

# ── 1. 설정값 ────────────────────────────────────────────────
# 과제 프롬프트에 적힌 v1.1 주소를 먼저 시도하고,
# 실패하면 Met 공식 문서에 나온 v1 주소로 다시 시도한다.
SEARCH_URLS = [
    "https://collectionapi.metmuseum.org/public/collection/v1.1/search",
    "https://collectionapi.metmuseum.org/public/collection/v1/search",
]
OBJECT_URL = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{}"

TIMEOUT = 10          # 서버 응답을 최대 10초까지만 기다림
CANDIDATES = 60       # 이미지 없는 작품을 건너뛸 여유분까지 포함해 확인할 최대 작품 수
HEADERS = {"User-Agent": "met-art-search-streamlit/1.0"}

st.set_page_config(page_title="Met Artwork Search", page_icon="🖼️", layout="wide")


# ── 2. API 호출 함수 (결과를 1시간 동안 캐시) ─────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def search_artworks(query: str, limit: int):
    """검색어로 작품 ID 목록을 받아온다. 반환값: (전체 개수, ID 리스트)"""
    params = {"q": query, "hasImages": "true", "limit": limit}
    last_error = None
    for url in SEARCH_URLS:
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()          # 404, 500 같은 오류 코드면 예외 발생
            data = response.json()
            total = data.get("total", 0)
            ids = data.get("objectIDs") or []    # 결과가 없으면 null이 오므로 빈 리스트로 바꿈
            return total, ids[:limit]
        except (requests.RequestException, ValueError) as error:
            last_error = error                   # 이 주소는 실패 → 다음 주소로 시도
    raise ConnectionError(last_error)            # 두 주소 모두 실패


@st.cache_data(ttl=3600, show_spinner=False)
def get_artwork(object_id: int) -> dict:
    """작품 ID 하나로 상세 정보를 받아온다."""
    response = requests.get(OBJECT_URL.format(object_id), headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


# ── 3. 화면 입력 부분 ────────────────────────────────────────
st.title("Met Museum Artwork Search")
st.write("Search The Metropolitan Museum of Art's open collection and browse the results.")

query = st.text_input("Search for Artworks", value="flower").strip()
count = st.slider("Number of artworks to show", min_value=3, max_value=12, value=6)

if not query:
    st.info("Enter a search word to see artworks.")
    st.stop()


# ── 4. 검색 실행 ─────────────────────────────────────────────
try:
    with st.spinner("Searching the collection..."):
        total, object_ids = search_artworks(query, CANDIDATES)
except ConnectionError:
    st.error("The Met collection service can't be reached right now. "
             "Check your internet connection and try again in a minute.")
    st.stop()

if not object_ids:
    st.warning(f'No artworks with images match "{query}". Try a different word, such as "cat" or "landscape".')
    st.stop()


# ── 5. 이미지가 있는 작품만 원하는 개수만큼 모으기 ────────────
artworks = []
with st.spinner("Loading artworks..."):
    for object_id in object_ids:
        if len(artworks) >= count:
            break
        try:
            art = get_artwork(object_id)
        except (requests.RequestException, ValueError):
            continue                              # 이 작품만 불러오기 실패 → 건너뜀
        if art.get("primaryImageSmall"):          # 이미지가 없는 작품은 건너뜀
            artworks.append(art)

if not artworks:
    st.warning(f'Artworks were found for "{query}", but none of them could be loaded with an image. Try another word.')
    st.stop()

st.caption(f"{total:,} matching artworks in the collection · showing {len(artworks)}")


# ── 6. 3열 그리드로 출력 ─────────────────────────────────────
for row_start in range(0, len(artworks), 3):
    columns = st.columns(3)                       # 한 줄마다 새로 3칸을 만들어 줄 높이를 맞춤
    for column, art in zip(columns, artworks[row_start:row_start + 3]):
        with column:
            st.image(art["primaryImageSmall"])
            st.markdown(f"**{art.get('title') or 'Untitled'}**")
            st.write(art.get("artistDisplayName") or "Unknown artist")
            st.write(art.get("objectDate") or "Date unknown")
            if art.get("objectURL"):
                st.markdown(f"[View on the Met website]({art['objectURL']})")


# ── 7. 출처 표기 ─────────────────────────────────────────────
st.divider()
st.caption("Data and images: The Metropolitan Museum of Art Open Access (CC0), "
           "via the Met Collection API — metmuseum.github.io")
