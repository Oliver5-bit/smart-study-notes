"""Smart Study Notes Generator. Run: python -m streamlit run app.py"""
import csv
import io
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version

import streamlit as st

MODEL = "sshleifer/distilbart-cnn-12-6"
MAX_TOKENS = 900
EXAMPLES = {
    "Artificial Intelligence": (
        "Artificial intelligence is a branch of computer science that enables machines "
        "to perform tasks that normally require human intelligence. These tasks include "
        "learning from data, recognizing speech and images, understanding language, and "
        "making decisions. AI is used in healthcare, education, transportation, and "
        "business. Although it offers many benefits, it also creates concerns about "
        "privacy, bias, job displacement, and the responsible use of technology."
    ),
    "Water Cycle": (
        "The water cycle describes the continuous movement of water between the Earth's "
        "surface and the atmosphere. Heat from the Sun causes water in oceans, rivers, "
        "and lakes to evaporate. The water vapor rises, cools, and condenses into clouds. "
        "When droplets become heavy, they fall as precipitation. Water then collects "
        "in rivers, lakes, and groundwater, and the cycle begins again."
    ),
    "Physical Exercise": (
        "Regular physical activity is important for maintaining good health. Exercise "
        "strengthens the heart, improves blood circulation, and helps control body "
        "weight. It can also reduce stress, improve sleep, and lower the risk of "
        "diseases such as diabetes and hypertension. Experts recommend combining "
        "aerobic activities, strength training, and flexibility exercises with a "
        "balanced diet and adequate rest."
    ),
}
STOP = set("a an and are as at be been being by for from has have had in into is it "
           "its of on or that the their them there these they this to was were which "
           "with would will can could should also such than then when where who what "
           "how why about between through during while each other more most".split())


def count_words(text):
    return len(re.findall(r"\b\w+(?:['’-]\w+)*\b", text))


def reduction(original, summary):
    if original <= 0:
        raise ValueError("Original word count must be positive.")
    return round((original - summary) / original * 100, 2)


def validate(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter a paragraph first.")
    if count_words(text) < 20:
        raise ValueError("Enter at least 20 words for a useful summary.")
    if len(text) > 12000:
        raise ValueError("Input is too large. Use one paragraph under 12,000 characters.")


def key_points(text, limit=3):
    sentences = list(dict.fromkeys(
        s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()
    ))
    if limit <= 0:
        return []

    def terms(sentence):
        return [w for w in re.findall(r"\b[a-z]{3,}\b", sentence.lower()) if w not in STOP]

    frequency = Counter(terms(text))
    scores = []
    for i, sentence in enumerate(sentences):
        words = terms(sentence)
        score = sum(frequency[w] for w in words) / max(1, len(words))
        scores.append((score, i))
    selected = sorted(scores, key=lambda item: (-item[0], item[1]))[:limit]
    return [sentences[i] for _, i in sorted(selected, key=lambda item: item[1])]


@st.cache_resource(show_spinner=False)
def load_model():
    from transformers import pipeline
    model = pipeline("summarization", model=MODEL, device=-1, framework="pt")
    return model, threading.Lock()


def generate(text, model, length="Short", points=3):
    validate(text)
    tokens = model.tokenizer.encode(text, add_special_tokens=True, truncation=False)
    capacity = min(MAX_TOKENS, getattr(model.model.config, "max_position_embeddings", 1024))
    if len(tokens) > capacity:
        raise ValueError(f"Input has {len(tokens)} model tokens; maximum is {capacity}. "
                         "Please split it into smaller paragraphs. Nothing was truncated.")
    fractions = {"Short": 0.35, "Medium": 0.50, "Long": 0.65}
    if length not in fractions:
        raise ValueError("Unknown summary length.")
    maximum = min(160, max(12, int(len(tokens) * fractions[length])))
    minimum = min(20, max(5, maximum // 3))
    result = model(text, max_length=maximum, min_length=minimum,
                   do_sample=False, num_beams=4, truncation=False)
    if not result or not isinstance(result[0], dict):
        raise RuntimeError("The model returned an invalid response.")
    summary = result[0].get("summary_text", "").strip()
    if not summary:
        raise RuntimeError("The model returned an empty summary.")
    original_count, summary_count = count_words(text), count_words(summary)
    return {
        "original": text.strip(), "summary": summary,
        "key_points": key_points(text, points), "original_words": original_count,
        "summary_words": summary_count, "reduction_percent": reduction(original_count, summary_count),
        "model": MODEL, "model_revision": getattr(model.model.config, "_commit_hash", None),
        "length": length, "created_utc": datetime.now(timezone.utc).isoformat(),
        "transformers_version": version("transformers"),
    }


def markdown(notes):
    points = "\n".join(f"- {point}" for point in notes["key_points"])
    return (
        f"# Smart Study Notes\n\n## Summary\n\n{notes['summary']}\n\n"
        f"## Key Points (extracted sentences)\n\n{points}\n\n"
        f"## Statistics\n\nOriginal words: {notes['original_words']}\n\n"
        f"Summary words: {notes['summary_words']}\n\n"
        f"Reduction: {notes['reduction_percent']:.2f}%\n\n"
        f"Model: {notes['model']}\n\nGenerated UTC: {notes['created_utc']}\n\n"
        f"## Original\n\n{notes['original']}\n"
    )


def csv_report(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
    writer.writeheader()
    for row in rows:
        safe = {key: ("'" + val if isinstance(val, str) and val.lstrip().startswith(
            ("=", "+", "-", "@")) else val) for key, val in row.items()}
        writer.writerow(safe)
    return stream.getvalue()


def change_example():
    st.session_state.paragraph = EXAMPLES[st.session_state.example]


def clear_editor():
    st.session_state.paragraph = ""
    st.session_state.pop("current", None)


def render_notes(notes, download_key):
    st.subheader("Summary")
    st.write(notes["summary"])
    st.subheader("Key points")
    st.caption("Extracted from your original text using sentence scoring; not AI-generated bullets.")
    for point in notes["key_points"]:
        st.write("• " + point)
    a, b, c = st.columns(3)
    a.metric("Original words", notes["original_words"])
    b.metric("Summary words", notes["summary_words"])
    c.metric("Reduction", f"{notes['reduction_percent']:.2f}%")
    if notes["reduction_percent"] <= 0:
        st.warning("This output is not shorter than the input. Try Short or a longer paragraph.")
    st.caption("AI can omit details or introduce errors. Compare the summary with the original.")
    st.download_button("Download notes", markdown(notes), "study-notes.md",
                       "text/markdown", key=download_key)
    with st.expander("Original text and provenance"):
        st.write(notes["original"])
        st.write("Model:", notes["model"])
        st.write("Generated UTC:", notes["created_utc"])


def main():
    st.set_page_config(page_title="Smart Study Notes", page_icon="📚", layout="wide")
    st.session_state.setdefault("paragraph", "")
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("test_rows", [])
    st.title("📚 Smart Study Notes Generator")
    st.caption("Turn an English paragraph into a short AI summary and revision points.")
    with st.sidebar:
        st.header("Settings")
        length = st.selectbox("Summary length", ["Short", "Medium", "Long"])
        points = st.slider("Maximum key points", 1, 6, 3)
        st.selectbox("Example paragraph", list(EXAMPLES), key="example")
        st.button("Load example", on_click=change_example)
        st.button("Clear input and result", on_click=clear_editor)
        st.divider()
        st.caption("No API key. The first run downloads the model and may take several minutes.")
        st.caption("Text is processed on the app server, not on your device. "
                   "This app does not intentionally save it to a database; session data is temporary. "
                   "Avoid confidential material on public deployments.")
    editor, testing, history = st.tabs(["Generate notes", "Project tests", "Session history"])
    with editor:
        text = st.text_area("Your paragraph", key="paragraph", height=250, max_chars=12000)
        st.caption(f"{count_words(text)} words • At least 20 words • Up to 900 model tokens")
        if st.button("Generate study notes", type="primary"):
            st.session_state.pop("current", None)
            try:
                validate(text)
                with st.spinner("Loading the model and generating your summary…"):
                    model, lock = load_model()
                    with lock:
                        notes = generate(text, model, length, points)
                st.session_state.current = notes
                st.session_state.history.insert(0, notes)
                st.session_state.history = st.session_state.history[:10]
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("AI generation failed. Check the model download connection, dependencies, "
                         "and server memory. No substitute summary has been generated.")
        if "current" in st.session_state:
            render_notes(st.session_state.current, "current_download")
    with testing:
        st.subheader("Three-paragraph project evaluation")
        st.write("Runs the actual AI model on all three examples with Short summaries and three key points. "
                 "Results remain available until this session ends. Failed cases are marked explicitly.")
        if st.button("Run three project tests"):
            rows = []
            try:
                with st.spinner("Loading AI model…"):
                    model, lock = load_model()
                progress = st.progress(0)
                for index, (topic, paragraph) in enumerate(EXAMPLES.items()):
                    row = {"topic": topic, "status": "", "original": paragraph, "summary": "",
                           "key_points": "", "original_words": count_words(paragraph),
                           "summary_words": "", "reduction_percent": "", "model": MODEL,
                           "generated_utc": "", "model_revision": "", "transformers_version": ""}
                    try:
                        with lock:
                            result = generate(paragraph, model, "Short", 3)
                        row.update({key: result[key] for key in (
                            "summary", "summary_words", "reduction_percent", "model_revision",
                            "transformers_version")})
                        row.update(status="Generated — review quality manually",
                                   key_points="\n".join(result["key_points"]),
                                   generated_utc=result["created_utc"])
                    except Exception:
                        row["status"] = "FAILED — no model output recorded"
                    rows.append(row)
                    progress.progress((index + 1) / len(EXAMPLES))
                st.session_state.test_rows = rows
            except Exception:
                st.session_state.test_rows = []
                st.error("Tests could not start: the AI model did not load. Check the server setup.")
        if st.session_state.test_rows:
            st.dataframe(st.session_state.test_rows, use_container_width=True)
            observation = st.text_area("Your observation on relevance and coherence", key="observation",
                placeholder="After reading the summaries, describe preserved main ideas, omissions, "
                            "unsupported claims, grammar, and sentence flow.")
            export_rows = [dict(row, observation=observation) for row in st.session_state.test_rows]
            st.download_button("Download test outputs and observation", csv_report(export_rows),
                               "project-test-results.csv", "text/csv")
    with history:
        st.caption("Latest ten summaries in this browser session. Not permanent storage.")
        for index, notes in enumerate(st.session_state.history):
            with st.expander(f"{index + 1}. {notes['created_utc']} — {notes['original_words']} words"):
                render_notes(notes, f"history_download_{index}")


if __name__ == "__main__":
    main()
