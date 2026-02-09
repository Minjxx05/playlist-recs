import streamlit as st

st.set_page_config(page_title="🎧 기분/상황 기반 YouTube Music 추천", page_icon="🎧", layout="wide")

# ✅ ytmusicapi가 없을 때 앱이 죽지 않도록 처리
try:
    from ytmusicapi import YTMusic
except ModuleNotFoundError:
    st.error(
        "❌ 'ytmusicapi' 패키지가 설치되어 있지 않아요.\n\n"
        "✅ 해결 방법:\n"
        "1) 레포에 requirements.txt가 있는지 확인\n"
        "2) requirements.txt에 아래 줄 추가\n"
        "   ytmusicapi>=1.11.5\n"
        "3) Streamlit Cloud에서 재배포(자동 재빌드) 또는 'Reboot app'\n"
    )
    st.stop()

ytmusic = YTMusic()


# -----------------------
# 기분/상황/장르 옵션
# -----------------------
MOODS = {
    "행복🙂": {
        "base_terms": ["happy", "upbeat", "feel good", "신나는", "기분좋은"],
        "reason": "기분 좋을 땐 리듬감 있고 밝은 곡이 더 잘 어울려요!",
    },
    "평온😌": {
        "base_terms": ["chill", "calm", "relax", "잔잔한", "편안한"],
        "reason": "차분한 날엔 잔잔하고 따뜻한 사운드가 좋아요.",
    },
    "우울😢": {
        "base_terms": ["sad", "melancholy", "emotional", "감성", "위로"],
        "reason": "마음이 가라앉을 땐 감정을 다독이는 곡이 도움이 돼요.",
    },
    "분노😡": {
        "base_terms": ["angry", "rage", "intense", "강렬한", "빡센"],
        "reason": "화가 난 날엔 강한 에너지의 곡으로 스트레스를 풀어보자!",
    },
    "피곤😴": {
        "base_terms": ["sleep", "ambient", "relaxing", "힐링", "수면"],
        "reason": "피곤한 날엔 자극이 적고 편안한 곡이 좋아요.",
    },
}

SITUATIONS = {
    "선택 안 함": [],
    "드라이브 🚗": ["drive", "driving", "road trip", "차에서 듣기", "드라이브 플레이리스트"],
    "공부/집중 📚": ["study", "focus", "concentration", "공부할 때", "집중 음악", "lofi"],
    "운동 🏋️": ["workout", "gym", "running", "운동할 때", "헬스 음악", "high energy"],
    "출퇴근 🚇": ["commute", "subway", "on the way", "출퇴근", "이동할 때"],
    "파티/모임 🎉": ["party", "dance", "club", "파티", "신나는 노래"],
    "힐링/휴식 🛋️": ["healing", "relax", "rest", "휴식", "힐링 음악"],
}

# 장르(선택 옵션) — 필수 아님
GENRES = {
    "선택 안 함": [],
    "K-pop": ["k-pop", "kpop", "케이팝"],
    "Pop": ["pop"],
    "J-pop": ["j-pop", "jpop", "일본 노래"],
    "Classic": ["classical", "classic", "클래식", "piano"],
}


# -----------------------
# 유틸 & 검색
# -----------------------
def pick_thumbnail(thumbnails):
    if not thumbnails:
        return None
    return sorted(thumbnails, key=lambda x: x.get("width", 0))[-1].get("url")


def build_queries(mood_key: str, situation_key: str, genre_key: str):
    """기분 + 상황 + 장르를 조합해 여러 개 검색 쿼리를 만든다."""
    mood_terms = MOODS[mood_key]["base_terms"]
    situation_terms = SITUATIONS[situation_key]
    genre_terms = GENRES[genre_key]

    # 핵심 조합 (영/한 섞어서 검색 커버리지↑)
    combos = []

    # 1) 기본(기분)만
    combos.append(" ".join(mood_terms[:3]))

    # 2) 기분 + 상황
    if situation_terms:
        combos.append(" ".join(mood_terms[:2] + situation_terms[:3]))

    # 3) 기분 + 장르
    if genre_terms:
        combos.append(" ".join(mood_terms[:2] + genre_terms[:2]))

    # 4) 기분 + 상황 + 장르
    if situation_terms and genre_terms:
        combos.append(" ".join(mood_terms[:2] + situation_terms[:2] + genre_terms[:2]))

    # 5) 상황 중심(플레이리스트 느낌)
    if situation_terms:
        combos.append(" ".join(situation_terms[:4]))

    # 6) 장르 중심(장르만 골랐을 때도 먹히게)
    if genre_terms:
        combos.append(" ".join(genre_terms[:3] + ["playlist"]))

    # 중복 제거
    out, seen = [], set()
    for q in combos:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def search_songs(query: str, limit: int = 10):
    # 곡 위주로 검색
    results = ytmusic.search(query, filter="songs", limit=limit) or []
    songs = []
    for r in results:
        video_id = r.get("videoId")
        if not video_id:
            continue

        title = r.get("title", "Unknown")
        artists = ", ".join([a.get("name", "") for a in (r.get("artists") or [])]) or "Unknown"
        album = (r.get("album") or {}).get("name")
        duration = r.get("duration")
        thumb = pick_thumbnail(r.get("thumbnails") or [])
        url = f"https://music.youtube.com/watch?v={video_id}"

        songs.append(
            {
                "title": title,
                "artists": artists,
                "album": album,
                "duration": duration,
                "thumb": thumb,
                "url": url,
                "query": query,
            }
        )
    return songs


def recommend(mood_key: str, situation_key: str, genre_key: str, limit: int):
    queries = build_queries(mood_key, situation_key, genre_key)

    combined = []
    seen = set()

    # 쿼리 여러 개로 분산 검색해서 다양성 확보
    per_query = max(4, limit // max(1, len(queries)))
    for q in queries:
        for s in search_songs(q, limit=per_query):
            key = (s["title"], s["artists"])
            if key in seen:
                continue
            seen.add(key)
            combined.append(s)
            if len(combined) >= limit:
                return combined, queries

    # 결과가 부족하면 마지막으로 넓은 검색(보강)
    if len(combined) < limit:
        fallback_query = " ".join(MOODS[mood_key]["base_terms"][:2] + ["playlist"])
        for s in search_songs(fallback_query, limit=limit * 2):
            key = (s["title"], s["artists"])
            if key in seen:
                continue
            seen.add(key)
            combined.append(s)
            if len(combined) >= limit:
                break

    return combined, queries


# -----------------------
# UI
# -----------------------
st.title("🎧 기분 + 상황 기반 음악 추천 (YouTube Music)")
st.caption("기분/상황/장르 옵션을 조합해 YouTube Music에서 곡을 검색해 추천해줘요.")

with st.sidebar:
    st.header("옵션 선택")
    mood_key = st.selectbox("오늘의 기분", list(MOODS.keys()))

    # ✅ 상황 추가 (요구사항)
    situation_key = st.selectbox("지금 상황(예: 드라이브)", list(SITUATIONS.keys()), index=1)

    # ✅ 장르 추가 (선택 옵션, 필수 아님)
    genre_key = st.selectbox("원하는 장르(선택)", list(GENRES.keys()), index=0)

    limit = st.slider("추천 곡 개수", 5, 20, 10)
    st.divider()
    go = st.button("🎶 추천 받기", use_container_width=True)

if go:
    mood = MOODS[mood_key]
    st.subheader(f"✨ 추천 결과: {mood_key} / {situation_key} / {genre_key}")
    st.info(f"이유: {mood['reason']}")

    with st.spinner("YouTube Music에서 곡을 찾는 중..."):
        songs, used_queries = recommend(mood_key, situation_key, genre_key, limit)

    if not songs:
        st.warning("검색 결과가 비어 있어요. 다른 상황/장르로 바꿔서 다시 시도해봐!")
        st.stop()

    with st.expander("🔍 사용된 검색 쿼리 보기"):
        for q in used_queries:
            st.write(f"- {q}")

    for i, s in enumerate(songs, start=1):
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
                st.caption(f"검색어: {s['query']}")
else:
    st.write("왼쪽에서 **기분 + 상황(예: 드라이브)** 을 고르고, 원하면 장르도 선택한 뒤 **추천 받기**를 눌러줘 🙂")
