import streamlit as st

st.set_page_config(page_title="🎧 기분/상황 기반 YouTube Music 추천", page_icon="🎧", layout="wide")

try:
    from ytmusicapi import YTMusic
except ModuleNotFoundError:
    st.error(
        "❌ 'ytmusicapi' 패키지가 설치되어 있지 않아요.\n\n"
        "✅ requirements.txt에 아래 줄을 추가해줘:\n"
        "ytmusicapi>=1.11.5"
    )
    st.stop()

ytmusic = YTMusic()

MOODS = {
    "행복🙂": {"base_terms": ["happy", "upbeat", "feel good", "신나는", "기분좋은"], "reason": "밝고 에너지 있는 곡이 잘 어울려요!"},
    "평온😌": {"base_terms": ["chill", "calm", "relax", "잔잔한", "편안한"], "reason": "잔잔하고 따뜻한 사운드가 좋아요."},
    "우울😢": {"base_terms": ["sad", "melancholy", "emotional", "감성", "위로"], "reason": "감정을 다독이는 곡이 도움이 돼요."},
    "분노😡": {"base_terms": ["angry", "rage", "intense", "강렬한", "빡센"], "reason": "강한 에너지로 스트레스를 풀어봐요!"},
    "피곤😴": {"base_terms": ["sleep", "ambient", "relaxing", "힐링", "수면"], "reason": "자극이 적고 편안한 곡이 좋아요."},
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

GENRES = {
    "선택 안 함": [],
    "K-pop": ["k-pop", "kpop", "케이팝", "아이돌", "가요"],
    "Pop": ["pop"],
    "J-pop": ["j-pop", "jpop", "일본 노래"],
    "Classic": ["classical", "classic", "클래식", "piano"],
}

def pick_thumbnail(thumbnails):
    if not thumbnails:
        return None
    return sorted(thumbnails, key=lambda x: x.get("width", 0))[-1].get("url")

def normalize_key(title, artists):
    return (title or "").strip().lower(), (artists or "").strip().lower()

def to_song_item_from_search(r, query=""):
    video_id = r.get("videoId")
    if not video_id:
        return None
    title = r.get("title", "Unknown")
    artists = ", ".join([a.get("name", "") for a in (r.get("artists") or [])]) or "Unknown"
    album = (r.get("album") or {}).get("name")
    duration = r.get("duration")
    thumb = pick_thumbnail(r.get("thumbnails") or [])
    url = f"https://music.youtube.com/watch?v={video_id}"
    return {
        "title": title, "artists": artists, "album": album, "duration": duration,
        "thumb": thumb, "url": url, "query": query
    }

def to_song_item_from_playlist_track(t, query=""):
    video_id = t.get("videoId")
    if not video_id:
        return None
    title = t.get("title", "Unknown")
    artists = ", ".join([a.get("name", "") for a in (t.get("artists") or [])]) or "Unknown"
    album = (t.get("album") or {}).get("name")
    duration = t.get("duration")
    thumb = pick_thumbnail(t.get("thumbnails") or [])
    url = f"https://music.youtube.com/watch?v={video_id}"
    return {
        "title": title, "artists": artists, "album": album, "duration": duration,
        "thumb": thumb, "url": url, "query": query
    }

def search_playlists(query: str, limit: int = 5):
    return ytmusic.search(query, filter="playlists", limit=limit) or []

def get_playlist_tracks(playlist_id: str, limit: int = 100):
    pl = ytmusic.get_playlist(playlist_id, limit=limit)
    return (pl or {}).get("tracks", []) or []

def search_songs(query: str, limit: int = 10):
    results = ytmusic.search(query, filter="songs", limit=limit) or []
    out = []
    for r in results:
        item = to_song_item_from_search(r, query=query)
        if item:
            out.append(item)
    return out

def get_kr_chart_songs(limit: int = 50):
    # KR 차트(가능하면)에서 곡을 가져옴 — K-pop 비중 높음
    try:
        charts = ytmusic.get_charts(country="KR")
        songs = (charts or {}).get("songs", {}).get("items", []) or []
        out = []
        for s in songs[:limit]:
            item = to_song_item_from_playlist_track(s, query="KR chart")
            if item:
                out.append(item)
        return out
    except Exception:
        return []

def build_kpop_playlist_queries(mood_key, situation_key):
    # K-pop은 “플레이리스트를 먼저” 찾는 게 가장 확실함
    mood_terms = MOODS[mood_key]["base_terms"]
    sit_terms = SITUATIONS[situation_key]
    # K-pop 강제 키워드: kpop/케이팝/가요를 꼭 넣음
    base = ["kpop", "케이팝", "가요", "K-pop"]

    queries = []
    if sit_terms:
        queries.append(" ".join(base + sit_terms[:3] + ["playlist"]))
    queries.append(" ".join(base + mood_terms[:2] + ["playlist"]))
    if sit_terms:
        queries.append(" ".join(base + mood_terms[:2] + sit_terms[:2] + ["playlist"]))
    # 중복 제거
    seen = set()
    out = []
    for q in queries:
        if q not in seen:
            seen.add(q); out.append(q)
    return out

def recommend_strict_kpop(mood_key, situation_key, limit):
    """K-pop은 Playlist → KR chart → songs 검색 순으로 강제."""
    combined = []
    seen = set()
    used_sources = []

    # 1) 플레이리스트에서 먼저 추출
    pl_queries = build_kpop_playlist_queries(mood_key, situation_key)
    for q in pl_queries:
        pls = search_playlists(q, limit=3)
        for pl in pls:
            pid = pl.get("browseId")
            if not pid:
                continue
            tracks = get_playlist_tracks(pid, limit=200)
            for t in tracks:
                item = to_song_item_from_playlist_track(t, query=f"playlist: {q}")
                if not item:
                    continue
                key = normalize_key(item["title"], item["artists"])
                if key in seen:
                    continue
                seen.add(key)
                combined.append(item)
                if len(combined) >= limit:
                    used_sources.append(f"Playlist({q})")
                    return combined, pl_queries, used_sources
        used_sources.append(f"Playlist({q})")

    # 2) KR 차트에서 보강
    kr = get_kr_chart_songs(limit=100)
    if kr:
        used_sources.append("KR charts")
    for item in kr:
        key = normalize_key(item["title"], item["artists"])
        if key in seen:
            continue
        seen.add(key)
        combined.append(item)
        if len(combined) >= limit:
            return combined, pl_queries, used_sources

    # 3) 최후: K-pop 키워드로 곡 검색
    fallback_terms = ["kpop", "케이팝", "가요"] + (SITUATIONS[situation_key][:2] if SITUATIONS[situation_key] else [])
    fallback_q = " ".join(fallback_terms + ["playlist"])
    used_sources.append(f"Song search({fallback_q})")
    for item in search_songs(fallback_q, limit=limit * 2):
        key = normalize_key(item["title"], item["artists"])
        if key in seen:
            continue
        seen.add(key)
        combined.append(item)
        if len(combined) >= limit:
            break

    return combined, pl_queries, used_sources

def recommend_general(mood_key, situation_key, genre_key, limit):
    """K-pop 외 장르는 기존 방식(검색) + 상황/장르 키워드 강화."""
    mood_terms = MOODS[mood_key]["base_terms"]
    sit_terms = SITUATIONS[situation_key]
    gen_terms = GENRES[genre_key]

    queries = []
    # 상황+장르를 더 강하게 반영
    if gen_terms and sit_terms:
        queries.append(" ".join(gen_terms[:2] + sit_terms[:3] + ["playlist"]))
        queries.append(" ".join(mood_terms[:2] + gen_terms[:2] + sit_terms[:2]))
    if gen_terms:
        queries.append(" ".join(gen_terms[:3] + ["playlist"]))
        queries.append(" ".join(mood_terms[:2] + gen_terms[:2]))
    if sit_terms:
        queries.append(" ".join(sit_terms[:4] + ["playlist"]))
    queries.append(" ".join(mood_terms[:3]))

    # 중복 제거
    seen_q = set()
    queries = [q for q in queries if not (q in seen_q or seen_q.add(q))]

    combined = []
    seen = set()
    for q in queries:
        for item in search_songs(q, limit=max(4, limit // max(1, len(queries)))):
            key = normalize_key(item["title"], item["artists"])
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)
            if len(combined) >= limit:
                return combined, queries, ["Song search"]

    return combined, queries, ["Song search"]

# ---------------- UI ----------------
st.title("🎧 기분 + 상황 + 장르 기반 음악 추천 (YouTube Music)")
st.caption("K-pop은 ‘플레이리스트/차트 기반’으로 강제 추천해서 K-pop이 확실히 뜨게 했어요.")

with st.sidebar:
    st.header("옵션")
    mood_key = st.selectbox("오늘의 기분", list(MOODS.keys()))
    situation_key = st.selectbox("지금 상황", list(SITUATIONS.keys()), index=1)
    genre_key = st.selectbox("원하는 장르(선택)", list(GENRES.keys()), index=0)
    limit = st.slider("추천 곡 개수", 5, 20, 10)
    go = st.button("🎶 추천 받기", use_container_width=True)

if go:
    st.subheader(f"✨ 추천: {mood_key} / {situation_key} / {genre_key}")
    st.info(f"이유: {MOODS[mood_key]['reason']}")

    with st.spinner("추천 중..."):
        if genre_key == "K-pop":
            songs, used_queries, sources = recommend_strict_kpop(mood_key, situation_key, limit)
        else:
            songs, used_queries, sources = recommend_general(mood_key, situation_key, genre_key, limit)

    if not songs:
        st.warning("추천 결과가 비어 있어요. 상황/장르를 바꿔서 다시 시도해봐!")
        st.stop()

    with st.expander("🔍 사용된 쿼리/소스 보기"):
        st.write("**소스:** " + ", ".join(sources))
        for q in used_queries:
            st.write(f"- {q}")

    for i, s in enumerate(songs[:limit], start=1):
        with st.container(border=True):
            cols = st.columns([1, 3])
            with cols[0]:
                if s["thumb"]:
                    st.image(s["thumb"], use_container_width=True)
            with cols[1]:
                st.markdown(f"### {i}. {s['title']}")
                st.write(f"**아티스트:** {s['artists']}")
                if s["album"]:
                    st.write(f"**앨범:** {s['album']}")
                if s["duration"]:
                    st.write(f"**길이:** {s['duration']}")
                st.link_button("YouTube Music에서 열기", s["url"])
                st.caption(f"출처/검색어: {s['query']}")
else:
    st.write("왼쪽에서 기분/상황을 고르고, 장르는 선택(특히 K-pop)한 뒤 **추천 받기**를 눌러줘 🙂")
