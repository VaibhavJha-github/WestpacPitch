from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

EMOTION_KEYWORDS = {
    "anxious": ["worried", "nervous", "anxious", "scared", "afraid", "concerned", "stress", "uncertain", "unsure"],
    "frustrated": ["frustrated", "annoyed", "angry", "ridiculous", "terrible", "worst", "unacceptable", "furious"],
    "confused": ["confused", "don't understand", "unclear", "lost", "what do you mean", "how does that work"],
    "calm": ["okay", "fine", "sure", "thanks", "good", "great", "appreciate"],
}

def analyze_sentiment(text: str) -> dict:
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.3:
        label = "Positive"
    elif compound <= -0.3:
        label = "Frustrated"
    else:
        label = "Neutral"

    text_lower = text.lower()
    emotion = "calm"
    for emo, keywords in EMOTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            emotion = emo
            break

    if emotion == "anxious":
        label = "Anxious"

    score_pct = round((compound + 1) * 50, 1)

    return {
        "label": label,
        "score": score_pct,
        "emotion": emotion,
        "compound": compound,
    }

def aggregate_sentiment(turns: list[dict]) -> dict:
    if not turns:
        return {"label": "Neutral", "score": 50.0, "emotion": "calm"}

    customer_turns = [t for t in turns if t.get("speaker") == "customer"]
    if not customer_turns:
        return {"label": "Neutral", "score": 50.0, "emotion": "calm"}

    results = [analyze_sentiment(t["text"]) for t in customer_turns]
    avg_score = sum(r["score"] for r in results) / len(results)

    last_emotions = [r["emotion"] for r in results[-3:]]
    dominant_emotion = max(set(last_emotions), key=last_emotions.count)

    if avg_score >= 65:
        label = "Positive"
    elif avg_score <= 35:
        label = "Frustrated"
    else:
        label = "Neutral"

    if dominant_emotion == "anxious":
        label = "Anxious"

    return {"label": label, "score": round(avg_score, 1), "emotion": dominant_emotion}
