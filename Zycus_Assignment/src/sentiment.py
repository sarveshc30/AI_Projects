"""VADER-based stakeholder sentiment scoring. No LLM calls -- see SENTIMENT_SCORING_GUIDE.md."""
from __future__ import annotations

from typing import Optional

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

NEUTRAL_DEFAULT = 50


class SentimentAnalyzer:
    def __init__(self):
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon")
        self.sia = SentimentIntensityAnalyzer()

    def score_comment(self, text: str) -> float:
        return self.sia.polarity_scores(text)["compound"]

    def compute_project_sentiment(self, comments_list: list[Optional[str]]) -> dict:
        """Returns dict with 0-100 score (high = calm, low = urgent/concerning) plus detail.

        NOTE: SENTIMENT_SCORING_GUIDE.md's own sample code uses `(1 - compound) / 2 * 100`
        and calls the result "urgency" -- that formula gives a HIGH number for concerning
        comments, which is the opposite of the guide's own stated contract ("high = calm")
        and of the RAG methodology's composite ("higher sub-score = healthier", positively
        weighted). Using it as written would mean alarming stakeholder comments *raise* a
        project's composite score. This uses `(1 + compound) / 2 * 100` instead, so calm/
        positive comments (compound near +1) score near 100 and alarming ones (compound
        near -1) score near 0 -- consistent with every other signal in the composite.
        See DECISIONS.md for the full writeup.
        """
        texts = [c for c in comments_list if c and isinstance(c, str)]
        if not texts:
            return {
                "score": NEUTRAL_DEFAULT,
                "comment_count": 0,
                "avg_compound": None,
                "data_gap": "No usable stakeholder comments found; sentiment defaults to neutral (50).",
            }

        compounds = [self.score_comment(t) for t in texts]
        avg_compound = sum(compounds) / len(compounds)
        score = int((1 + avg_compound) / 2 * 100)
        score = max(0, min(100, score))
        return {
            "score": score,
            "comment_count": len(texts),
            "avg_compound": round(avg_compound, 3),
            "data_gap": None,
        }
