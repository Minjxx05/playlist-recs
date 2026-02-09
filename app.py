import time
import requests
import streamlit as st

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

st.set_page_config(page_title="🎧 기분 기반 음악 추천", page_icon="🎧", layout="wide")

# -----------------------
# Mood mapping (검색어/장르/추천이유)
# -----------------------
MOODS = {
    "행복🙂": {
        "seed_genres": ["pop", "dance", "k-pop"],
        "search_terms": ["happy", "feel good", "upbeat", "party", "신나는", "기분좋은"],
        "reason": "기분이 좋을 땐 에너지와 리듬감이 있는 곡이 잘 어울려요!",
        "targets": {"target_valence": 0.85, "target_energy": 0.75, "target_danceability": 0.75},
    },
    "평온😌": {
        "seed_genres": ["chill", "acoustic", "indie", "jazz"],
        "search_terms": ["chill", "calm", "relax", "peaceful", "잔잔한", "편안한"],
        "reason": "차분한 날엔 잔잔하고 따뜻한 톤의 곡이 집중과 휴식에 좋아요.",
        "targets": {"target_valence": 0.55, "target_energy": 0.35, "target_acousticness": 0.7},
    },
    "우울😢": {
        "seed_genres": ["sad", "indie", "acoustic", "r-n-b"],
        "search_terms": ["sad", "melancholy", "ballad", "위로", "감성", "슬픈"],
        "reason": "마음이 가라앉을 땐 감정을 정리해주는 감성적인 곡이 도움이 돼요.",
        "targets": {"target_valence": 0.25, "target_energy": 0.3, "target_acousticness": 0.55},
    },
    "분노😡": {
        "seed_genres": ["rock", "metal", "hip-hop", "punk"],
        "search_terms": ["angry", "rage", "intense", "빡센", "강렬한", "분노"],
        "reason": "화가 난 날엔 강한 비트/기타 사운드로 에너지를 안전하게 배출해보자!",
        "targets": {"target_valence": 0.35, "target_energy": 0.9, "target_tempo": 140},
    },
    "피곤😴": {
        "seed_genres": ["sleep", "ambient", "chill", "lofi"],
        "search_terms": ["sleep", "lofi", "study", "ambient", "잠", "힐링", "로파이"],
        "reason": "피곤한 날엔 자극이 적고 반복적인 사운드가 부담을 덜어줘요.",
        "targets": {"target_valence": 0.45, "target_energy": 0.2, "target_instrumentalness": 0.6},
    },
}


# -----------------------
# Spotify Auth (Client Credentials)
# -----------------------
@st.cache_data(show_spinner=False)
def get_access_token(client_id: str, client_secret: str) -> dict:
    """
    Returns dict: {access_token, expires_at}
    """
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {"grant_type": "client_credentials"}
    resp = requests.post(SPOTIFY_TOKEN_URL, auth=auth, data=data, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    return {
        "access_token": payload["access_token"],
        "expires_at": int(time.time()) + int(payload.get("expires_in", 3600)) - 30,
    }


def spotify_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def safe_get_token() -> str:
    client_id = st.secrets.get("SPOTIFY_CLIENT_ID", "")
    client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        st.error("Spotify Client ID/Secret이 설정되지 않았어요. `.streamlit/secrets.toml`를 확인해줘!")
        st.stop()

    tok = st.session_state.get("spotify_token")
    if not tok or time.time() >= tok["expires_at"]:
        tok = get_access_token(client_id, client_secret)
        st.session_state["spotify_token"] = tok
    return tok["access_token"]


# -----------------------
# API calls
# -----------------------
def try_recommendations(token: str, mood_key: str, limit: int = 10, market: str = "KR"):
    """
    Tries /v1/recommendations first (may be restricted in some apps).
    If fails, caller should fallback to search.
    """
    mood = MOODS[mood_key]
    params = {
        "limit": limit,
        "market": market,
        "seed_genres": ",".join(mood["seed_genres"][:3]),  # 최대 5개 seed 중 일부만 사용
    }
    params.update(mood["targets"])

    url = f"{SPOTIFY_API_BASE}/recommendations"
    r = requests.get(url, headers=spotify_headers(token), params=params, timeout=15)
    if r.status_code == 200:
        return r.json().get("tracks", [])
    return None  # 실패 시 None


def fallback_search_tracks(token: str, mood_key: str, limit: int = 10, market: str = "KR"):
    mood = MOODS[mood_key]

    # 검색어 구성: mood search_terms + 장르들 일부
    q_terms = mood["search_terms"][:3]
    g_terms = mood["seed_genres"][:2]
    query = " ".join([*q_terms, *[f"genre:{g}" for g in g_terms]])

    url = f"{SPOTIFY_API_BASE}/search"
    params = {"q": query, "type": "track", "limit": limit, "market": market}
    r = requests.get(url, headers=spotify_headers(token), params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("tracks", {}).get("items", [])


def simplify_track(t: dict) -> dict:
    album = t.get("album", {}) or {}
    images = album.get("images", []) or []
    image_url = images[0]["url"] if images else None

    artists = ", ".join([a.get("name", "") for a in t.get("artists", [])])
    return {
        "name": t.get("name"),
        "artists": artists,
        "album": album.get("name"),
        "image_url": image_url,
        "preview_url": t.get("preview_url"),
        "external_url": (t.get("external_urls", {}) or {}).get("spotify"),
        "popularity": t.get("popularity"),
    }


# -----------------------
# UI
# -----------------------
st.title("🎧 오늘의 기분 기반 음악 추천")
st.caption("Spotify Web API (Client Credentials)로 기분에 맞는 곡을 추천합니다.")

with st.sidebar:
    st.header("🔑 Spotify API 설정")
    st.write("로컬은 `.streamlit/secrets.toml`에 넣고, 배포는 Streamlit Cloud의 Secrets에 넣어줘.")
    st.divider()

    mood_key = st.selectbox("오늘의 기분을 선택해줘", list(MOODS.keys()))
    market = st.selectbox("Market", ["KR", "US", "JP", "GB"], index=0)
    limit = st.slider("추천 곡 개수", 5, 20, 10)

    do = st.button("🎶 추천 받기", use_container_width=True)

if do:
    token = safe_get_token()

    with st.spinner("Spotify에서 곡을 고르는 중..."):
        tracks = try_recommendations(token, mood_key, limit=limit, market=market)

        used = "recommendations"
        if tracks is None:
            # /recommendations 제한/실패 시 Search로 폴백
            tracks = fallback_search_tracks(token, mood_key, limit=limit, market=market)
            used = "search"

    mood = MOODS[mood_key]
    st.subheader(f"✨ {mood_key} 추천 결과")
    st.info(f"이유: {mood['reason']}")
    st.caption(f"사용한 방식: {used} (recommendations 실패 시 search로 자동 전환)")

    if not tracks:
        st.warning("추천 결과가 비어 있어요. 다른 기분/마켓으로 다시 시도해봐!")
        st.stop()

    simple = [simplify_track(t) for t in tracks]

    # 카드 형태로 표시
    for i, tr in enumerate(simple, start=1):
        with st.container(border=True):
            cols = st.columns([1, 3])
            with cols[0]:
                if tr["image_url"]:
                    st.image(tr["image_url"], use_container_width=True)
            with cols[1]:
                st.markdown(f"### {i}. {tr['name']}")
                st.write(f"**아티스트:** {tr['artists']}")
                st.write(f"**앨범:** {tr['album']}")
                if tr["popularity"] is not None:
                    st.write(f"**인기도:** {tr['popularity']}/100")
                if tr["external_url"]:
                    st.link_button("Spotify에서 열기", tr["external_url"])
                if tr["preview_url"]:
                    st.audio(tr["preview_url"])

else:
    st.write("왼쪽에서 기분을 고르고 **추천 받기**를 눌러줘 🙂")
