import json
import re
from urllib.parse import parse_qs, urlparse

import google.generativeai as genai
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi


VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_video_id(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("Please enter a YouTube URL or video ID.")

    if VIDEO_ID_PATTERN.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)
    if not parsed.netloc:
        raise ValueError("Invalid YouTube URL or video ID.")

    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.strip("/")

    if host == "youtu.be" and path:
        video_id = path.split("/")[0]
        if VIDEO_ID_PATTERN.fullmatch(video_id):
            return video_id

    is_youtube_domain = host == "youtube.com" or host.endswith(".youtube.com")
    if is_youtube_domain:
        if path == "watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if VIDEO_ID_PATTERN.fullmatch(video_id):
                return video_id

        for prefix in ("embed/", "shorts/", "live/"):
            if path.startswith(prefix):
                video_id = path[len(prefix) :].split("/")[0]
                if VIDEO_ID_PATTERN.fullmatch(video_id):
                    return video_id

    raise ValueError("Could not find a valid YouTube video ID.")


def fetch_transcript(video_id: str) -> list[dict]:
    transcript_api = YouTubeTranscriptApi()
    transcript = transcript_api.fetch(video_id)
    if not transcript:
        raise ValueError("Transcript is empty for this video.")
    return transcript


def _to_mmss(seconds: float) -> str:
    total = max(int(seconds), 0)
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def _transcript_field(item, field: str, default=""):
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def build_transcript_text(transcript: list[dict], limit: int = 200) -> str:
    lines = []
    for item in transcript[:limit]:
        text = str(_transcript_field(item, "text", "")).replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"[{_to_mmss(float(_transcript_field(item, 'start', 0)))}] {text}")
    return "\n".join(lines)


def parse_json_response(response_text: str) -> dict:
    cleaned = (response_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\\s*", "", cleaned)
        cleaned = re.sub(r"\\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise ValueError("Gemini response did not contain valid JSON.")


def extract_quotes_with_gemini(transcript: list[dict], api_key: str) -> list[dict]:
    transcript_text = build_transcript_text(transcript, limit=300)
    if not transcript_text:
        raise ValueError("Transcript text is empty after preprocessing.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
You are extracting memorable quotes from a university lecture transcript.
Pick the 5 best quotes ranked by insight and impact.

Return only valid JSON in this format:
{{
  "quotes": [
    {{
      "quote": "exact quote text",
      "context": "where/when in the lecture this appears",
      "importance": "why this quote matters",
      "timestamp": "MM:SS or HH:MM:SS"
    }}
  ]
}}

Rules:
- Exactly 5 quotes
- Keep quotes faithful to transcript wording
- Avoid duplicates or near-duplicates
- Keep importance concise (1 sentence)

Transcript:
{transcript_text}
"""

    response = model.generate_content(prompt)
    parsed = parse_json_response(getattr(response, "text", ""))
    quotes = parsed.get("quotes") if isinstance(parsed, dict) else None

    if not isinstance(quotes, list) or not quotes:
        raise ValueError("Gemini returned an invalid quote list.")

    normalized_quotes = []
    for quote in quotes[:5]:
        if not isinstance(quote, dict):
            continue
        quote_text = str(quote.get("quote", "")).strip()
        context = str(quote.get("context", "")).strip()
        importance = str(quote.get("importance", "")).strip()
        timestamp = str(quote.get("timestamp", "")).strip()
        if not quote_text:
            continue
        normalized_quotes.append(
            {
                "quote": quote_text,
                "context": context or "Not provided",
                "importance": importance or "Not provided",
                "timestamp": timestamp or "Not provided",
            }
        )

    if not normalized_quotes:
        raise ValueError("No valid quotes were returned by Gemini.")

    return normalized_quotes


st.set_page_config(page_title="YouTube Class Quote Extractor", page_icon="🎓", layout="wide")

st.title("🎓 YouTube Class Quote Extractor")
st.write(
    "Extract the best lecture quotes from Stanford/MIT YouTube classes using "
    "`youtube-transcript-api` + Google Gemini (free tier)."
)

with st.sidebar:
    st.header("Configuration")
    gemini_api_key = st.text_input("Gemini API Key", type="password")
    st.caption("Get a free key at https://aistudio.google.com/app/apikeys")

st.subheader("1) Enter a YouTube URL or Video ID")
video_input = st.text_input(
    "YouTube URL or ID",
    placeholder="https://www.youtube.com/watch?v=... or dQw4w9WgXcQ",
)

if st.button("Extract Top 5 Quotes", type="primary"):
    if not gemini_api_key:
        st.error("Please add your Gemini API key in the sidebar.")
    elif not video_input.strip():
        st.error("Please provide a YouTube URL or video ID.")
    else:
        try:
            with st.spinner("Parsing video input..."):
                video_id = extract_video_id(video_input)

            st.info(f"Video ID detected: `{video_id}`")

            with st.spinner("Fetching transcript from YouTube..."):
                transcript = fetch_transcript(video_id)

            st.success(f"Transcript loaded ({len(transcript)} segments).")

            with st.spinner("Extracting high-quality quotes using Gemini..."):
                quotes = extract_quotes_with_gemini(transcript, gemini_api_key)

            result = {
                "video_id": video_id,
                "quote_count": len(quotes),
                "quotes": quotes,
            }
            st.session_state["result"] = result
            st.session_state["transcript_preview"] = build_transcript_text(transcript, limit=80)

        except Exception as exc:
            st.error(f"Processing failed: {exc}")

if "result" in st.session_state:
    result = st.session_state["result"]
    st.subheader("2) Best Quotes")

    for index, item in enumerate(result["quotes"], start=1):
        with st.container(border=True):
            st.markdown(f"**Quote #{index}**")
            st.markdown(f"> **\"{item['quote']}\"**")
            st.write(f"**Context:** {item['context']}")
            st.write(f"**Why it matters:** {item['importance']}")
            st.caption(f"Timestamp: {item['timestamp']}")

    st.download_button(
        "Download quotes as JSON",
        data=json.dumps(result, indent=2),
        file_name=f"{result['video_id']}_quotes.json",
        mime="application/json",
    )

    show_preview = st.toggle("Show transcript preview")
    if show_preview:
        st.text_area(
            "Transcript preview",
            value=st.session_state.get("transcript_preview", ""),
            height=300,
            disabled=True,
        )

st.divider()
st.caption(
    "Tip: Streamlit is excellent for fast prototyping and free hosting on Streamlit Cloud; "
    "Railway/Vercel can be better for custom backend/frontend split and advanced scaling."
)
