import streamlit as st

st.set_page_config(page_title="오늘의 플리! 🎧✨", page_icon="🎧", layout="wide")

# --- 안전하게 import (없으면 안내 후 종료) ---
try:
    from ytmusicapi import YTMusic
except ModuleNotFoundError:
    st.error("앗! `ytmusicapi`가 없어서 실행이 안 돼요 🥲\n\n`requirements.txt`에 `ytmusicapi>=1.11.5`를 추가해줘!")
    st.stop()

ytmusic = YTMusic()


# -----------------------
# 옵션 데이터
# -----------------------
MOODS = {
    "행복🙂": {"terms": ["happy", "upbeat", "feel good", "신나는", "기분좋은"], "msg": "오늘 텐션 업! 같이 신나게 가자아 🎉"},
    "평온😌": {"terms": ["chill", "calm", "relax", "잔잔한", "편안한"], "msg": "차분하게 스르르— 편안한 플리로 가볼까? ☁️"},
    "우울😢": {"terms": ["sad", "melancholy", "emotional", "감성", "위로"], "msg": "마음 토닥토닥… 위로가 되는 노래로 골라봤어 🫶"},
    "분노😡": {"terms": ["angry", "rage", "intense", "강렬한", "빡센"], "msg": "에너지 빡! 시원하게 풀어보자 🔥"},
    "피곤😴": {"terms": ["sleep", "ambient", "relaxing", "힐링", "수면"], "msg": "오늘은 쉬는 게 최고… 포근한 플리로 가자 🛌"},
}

SITUATIONS = {
    "선택 안 함": [],
    "드라이브 🚗": ["drive", "driving", "road trip", "드라이브", "차에서 듣기"],
    "공부/집중 📚": ["study", "focus", "집중", "공부할 때", "lofi"],
    "운동 🏋️": ["workout", "gym", "running", "운동", "헬스"],
    "출퇴근 🚇": ["commute", "출퇴근", "이동할 때"],
    "파티/모임 🎉": ["party", "dance", "파티", "신나는"],
    "힐링/휴식 🛋️": ["healing", "relax", "휴식", "힐링"],
}

# ✅ 장르를 "확실하게" 잡기 위한 강한 키워드 + 기본 국가(차트 보강용)
GENRES = {
    "선택 안 함": {
        "force_terms": [],
        "playlist_terms": [],
        "chart_country": None,
        "label": "장르 안 고름 😌",
    },
    "K-pop 🇰🇷": {
        "force_terms": ["kpop", "k-pop", "케이팝", "가요", "아이돌"],
        "playlist_terms": ["K-pop", "케이팝", "Kpop Hits", "K-pop playlist", "K-pop mix"],
        "chart_country": "KR",
        "label": "K-pop 💖",
    },
    "Pop 🌎": {
        "force_terms": ["pop", "pop hits", "top hits", "radio hits"],
        "playlist_terms": ["Pop Hits", "Today's Top Hits", "Pop playlist", "Top pop"],
        "chart_country": "US",
        "label": "Pop ✨",
    },
    "J-pop 🇯🇵": {
        "force_terms": ["jpop", "j-pop", "J-Pop", "일본 노래", "Japanese pop"],
        "playlist_terms": ["J-Pop", "Jpop Hits", "J-pop playlist", "Japanese pop"],
        "chart_country": "JP",
        "label": "J-pop 🍡",
    },
    "Classic 🎻": {
        "force_terms": ["classical", "classic", "orchestra", "piano", "클래식", "피아노"],
        "playlist_terms": ["Classical", "Classical playlist", "Piano", "Relaxing classical"],
        "chart_country": None,  # 클래식은 차트보다는 플레이리스트/검색이 더 낫다
        "label": "Classic 🎼",
    },
}


# -----------------------
# 유틸 함수
# -----------------------
def pick_thumbnail(thumbnails):
    if not thumbnails:
        return None
    return sorted(thumbnails, key=lambda x: x.get("width", 0))[-1].get("url")


def norm_key(title, artists):
    return (title or "").strip().lower(), (artists or "").strip().lower()


def song_from_search(r, query=""):
    vid = r.get("videoId")
    if not vid:
        return None
    title = r.get("title", "Unknown")
    artists = ", ".join([a.get("name", "") for a in (r.get("artists") or [])]) or "Unknown"
    album = (r.get("album") or {}).get("name")
    duration = r.get("duration")
    thumb = pick_thumbnail(r.get("thumbnails") or [])
    url = f"https://music.youtube.com/watch?v={vid}"
    return {
        "title": title,
        "artists": artists,
        "album": album,
        "duration": duration,
        "thumb": thumb,
        "url": url,
        "from": query,
    }


def song_from_track(t, query=""):
    vid = t.get("videoId")
    if not vid:
        return None
    title = t.get("title", "Unknown")
    artists = ", ".join([a.get("name", "") for a in (t.get("artists") or [])]) or "Unknown"
    album = (t.get("album") or {}).get("name")
    duration = t.get("duration")
    thumb = pick_thumbnail(t.get("thumbnails") or [])
    url = f"https://music.youtube.com/watch?v={vid}"
    return {
        "title": title,
        "artists": artists,
        "album": album,
        "duration": duration,
        "thumb": thumb,
        "url": url,
        "from": query,
    }


def search_playlists(query, limit=5):
    return ytmusic.search(query, filter="playlists", limit=limit) or []


def get_playlist_tracks(browse_id, limit=200):
    pl = ytmusic.get_playlist(browse_id, limit=limit) or {}
    return pl.get("tracks", []) or []


def search_songs(query, limit=20):
    results = ytmusic.search(query, filter="songs", limit=limit) or []
    out = []
    for r in results:
        s = song_from_search(r, query=query)
        if s:
            out.append(s)
    return out


def get_chart_songs(country, limit=60):
    if not country:
        return []
    try:
        charts = ytmusic.get_charts(country=country) or {}
        items = (charts.get("songs") or {}).get("items", []) or []
        out = []
        for t in items[:limit]:
            s = song_from_track(t, query=f"{country} chart")
            if s:
                out.append(s)
        return out
    except Exception:
        return []


def build_playlist_queries(mood_key, situation_key, genre_key):
    mood_terms = MOODS[mood_key]["terms"]
    sit_terms = SITUATIONS[situation_key]
    g = GENRES[genre_key]

    # 장르를 "강제"하기 위해 장르 키워드를 꼭 포함
    force = g["force_terms"]
    pl_terms = g["playlist_terms"]

    queries = []
    # 장르 플레이리스트 키워드 중심
    if pl_terms:
        if sit_terms:
            queries.append(" ".join(pl_terms[:2] + sit_terms[:3] + ["playlist"]))
        queries.append(" ".join(pl_terms[:2] + ["playlist"]))
    # 장르 강제 + 기분/상황 섞기
    if force:
        if sit_terms:
            queries.append(" ".join(force[:3] + sit_terms[:2] + mood_terms[:2] + ["playlist"]))
        queries.append(" ".join(force[:3] + mood_terms[:2] + ["playlist"]))
    # 장르 미선택이면 기분/상황 중심
    if not force and sit_terms:
        queries.append(" ".join(mood_terms[:2] + sit_terms[:3] + ["playlist"]))
    if not force:
        queries.append(" ".join(mood_terms[:3] + ["playlist"]))

    # 중복 제거
    seen = set()
    out = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def recommend(mood_key, situation_key, genre_key, limit):
    """
    추천 순서:
    1) (장르 강제) 플레이리스트에서 추출
    2) (가능하면) 해당 국가 차트에서 보강
    3) 마지막으로 곡 검색으로 채우기
    """
    g = GENRES[genre_key]
    combined = []
    seen = set()

    # 1) Playlist-first (장르 확실)
    pl_queries = build_playlist_queries(mood_key, situation_key, genre_key)

    for q in pl_queries:
        pls = search_playlists(q, limit=4)
        for pl in pls:
            pid = pl.get("browseId")
            if not pid:
                continue
            tracks = get_playlist_tracks(pid, limit=250)
            for t in tracks:
                s = song_from_track(t, query=f"playlist: {q}")
                if not s:
                    continue
                key = norm_key(s["title"], s["artists"])
                if key in seen:
                    continue
                seen.add(key)
                combined.append(s)
                if len(combined) >= limit:
                    return combined, pl_queries

    # 2) Charts boost (장르가 K-pop/Pop/J-pop이면 국가 차트로 보강)
    chart_songs = get_chart_songs(g["chart_country"], limit=120)
    for s in chart_songs:
        key = norm_key(s["title"], s["artists"])
        if key in seen:
            continue
        seen.add(key)
        combined.append(s)
        if len(combined) >= limit:
            return combined, pl_queries

    # 3) Song search fallback (장르 키워드 강제 포함)
    mood_terms = MOODS[mood_key]["terms"]
    sit_terms = SITUATIONS[situation_key]
    force = g["force_terms"]

    # 장르 선택이면 force를 무조건 쿼리에 포함
    if force:
        fallback_queries = [
            " ".join(force[:3] + sit_terms[:2] + mood_terms[:2]),
            " ".join(force[:3] + mood_terms[:2] + ["playlist"]),
            " ".join(force[:3] + sit_terms[:3] + ["playlist"]),
        ]
    else:
        fallback_queries = [
            " ".join(mood_terms[:2] + sit_terms[:3] + ["playlist"]),
            " ".join(mood_terms[:3]),
        ]

    # 중복 제거
    fq_seen = set()
    fallback_queries = [q for q in fallback_queries if not (q in fq_seen or fq_seen.add(q))]

    for q in fallback_queries:
        for s in search_songs(q, limit=limit * 2):
            key = norm_key(s["title"], s["artists"])
            if key in seen:
                continue
            seen.add(key)
            combined.append(s)
            if len(combined) >= limit:
                return combined, pl_queries + fallback_queries

    return combined, pl_queries + fallback_queries


# -----------------------
# UI (귀엽게!)
# -----------------------
st.markdown("# 오늘의 플리! 🎧✨")
st.write("기분이랑 상황만 골라주면, 딱 어울리는 노래로 골라줄게요 💗")

with st.sidebar:
    st.markdown("## 🎛️ 오늘의 선택")
    mood_key = st.selectbox("오늘 기분은 어때? 🙂", list(MOODS.keys()))
    situation_key = st.selectbox("지금 뭐 하는 중이야? 🌿", list(SITUATIONS.keys()), index=1)
    genre_key = st.selectbox("원하는 장르가 있으면 골라줘! (선택) 🎼", list(GENRES.keys()), index=0)
    limit = st.slider("몇 곡 골라줄까? 🎶", 5, 20, 10)
    go = st.button("💖 플리 뽑기!", use_container_width=True)

if go:
    st.markdown("## 🧸 오늘의 추천!")
    st.success(f"{MOODS[mood_key]['msg']}")

    chips = f"**{mood_key}** · **{situation_key}** · **{GENRES[genre_key]['label']}**"
    st.markdown(f"🫧 {chips}")

    with st.spinner("노래 고르는 중… 잠깐만 기다려줘! 🎀"):
        songs, used_queries = recommend(mood_key, situation_key, genre_key, limit)

    if not songs:
        st.warning("앗… 이번엔 곡을 못 찾았어 🥲 옵션을 살짝 바꿔서 다시 해볼래?")
        st.stop()

    # 결과 출력
    for i, s in enumerate(songs[:limit], start=1):
        with st.container(border=True):
            cols = st.columns([1, 3])
            with cols[0]:
                if s["thumb"]:
                    st.image(s["thumb"], use_container_width=True)
                else:
                    st.write("🎵")
            with cols[1]:
                st.markdown(f"### {i}. {s['title']} 🎶")
                st.write(f"👤 **아티스트:** {s['artists']}")
                if s["album"]:
                    st.write(f"💿 **앨범:** {s['album']}")
                if s["duration"]:
                    st.write(f"⏱️ **길이:** {s['duration']}")
                st.link_button("▶️ YouTube Music에서 듣기", s["url"])
else:
    st.info("왼쪽에서 골라주면 바로 플리 만들어줄게요 💫")
