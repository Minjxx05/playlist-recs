import streamlit as st
from ytmusicapi import YTMusic

st.set_page_config(page_title="🎧 기분 기반 YouTube Music 추천", page_icon="🎧", layout="wide")

# 로그인 없이도 검색 가능 (비공식 라이브러리)
ytmusic = YTMusic()

MOODS = {
    "행복🙂": {
        "queries": ["happy upbeat", "feel good", "party pop", "신나는 팝", "기분좋은 노래"],
        "reason": "기분 좋을 땐 리듬감 있고 밝은 곡이 더 잘 어울려요!",
    },
    "평온😌": {
        "queries": ["chill", "calm acoustic", "lofi", "잔잔한", "편안한 노래"],
        "reason": "차분한 날엔 잔잔하고 따뜻한 사운드가 좋아요.",
    },
    "우울😢": {
        "queries": ["sad songs", "melancholy", "korean ballad", "감성 발라드", "위로 노래"],
        "reason": "마음이 가라앉을 땐 감정을 다독이는 곡이 도움이 돼요.",
    },
    "분노😡": {
        "queries": ["angry", "rage rock", "intense hip hop", "강렬한", "빡센 노래"],
        "reason": "화가 난 날엔 강한 에너지의 곡으로 스트레스를 풀어보자!",
    },
    "피곤😴": {
        "queries": ["sleep", "ambient", "relaxing piano", "수면", "힐링 음악"],
        "reason": "피곤한 날엔 자극이 적고 편안한 곡이 좋아요.",
    },
}

def pick_thumbnail(thumbnails: list[dict]) -> str | None:
    if not thumbnails:
        return None
    # 보통 여러 사이즈가 오니 가장 큰 것 선택
    return sorted(thumbnails, key=lambda x: x.get("width", 0))[-1].get("url")

def search_songs(query: str, limit: int = 10):
    # filter="songs" 는 곡 위주 결과
    # ytmusicapi search 문서 참고 (resultType/thumbnails 등) :contentReference[oaicite:2]{index=2}
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
        songs.append({
            "title": title,
            "artists": artists,
            "album": album,
            "duration": duration,
            "thumb": thumb,
            "url": url,
        })
    return songs

st.title("🎧 오늘의 기분 기반 음악 추천 (YouTube Music)")
st.caption("※ YouTube Music은 공식 Web API가 없어 비공식 라이브러리(ytmusicapi)로 검색 기반 추천을 구현합니다.")

with st.sidebar:
    st.header("설정")
    mood_key = st.selectbox("오늘의 기분을 선택해줘", list(MOODS.keys()))
    limit = st.slider("추천 곡 개수", 5, 20, 10)
    st.divider()
    go = st.button("🎶 추천 받기", use_container_width=True)

if go:
    mood = MOODS[mood_key]
    st.subheader(f"✨ {mood_key} 추천")
    st.info(f"이유: {mood['reason']}")

    # 여러 쿼리를 돌려서 결과를 모으고, 중복 제거
    with st.spinner("YouTube Music에서 곡을 찾는 중..."):
        combined = []
        seen = set()
        per_query = max(3, limit // max(1, len(mood["queries"]) // 2))  # 대충 분배

        for q in mood["queries"]:
            for s in search_songs(q, limit=per_query):
                key = (s["title"], s["artists"])
                if key in seen:
                    continue
                seen.add(key)
                combined.append(s)
                if len(combined) >= limit:
                    break
            if len(combined) >= limit:
                break

    if not combined:
        st.warning("검색 결과가 비어 있어요. 다른 기분으로 시도해보거나, 쿼리(키워드)를 바꿔보자!")
        st.stop()

    for i, s in enumerate(combined, start=1):
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

else:
    st.write("왼쪽에서 기분을 고르고 **추천 받기**를 눌러줘 🙂")
