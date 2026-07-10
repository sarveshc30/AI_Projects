from src.sentiment import SentimentAnalyzer


def test_empty_comments_default_neutral():
    result = SentimentAnalyzer().compute_project_sentiment([])
    assert result["score"] == 50
    assert result["data_gap"] is not None


def test_none_and_blank_comments_treated_as_absent():
    result = SentimentAnalyzer().compute_project_sentiment([None, "", None])
    assert result["score"] == 50
    assert result["comment_count"] == 0


def test_positive_comments_score_high_calm():
    result = SentimentAnalyzer().compute_project_sentiment(
        ["Great progress, everything on track and the team is thrilled!"]
    )
    assert result["score"] > 50
    assert result["data_gap"] is None


def test_negative_comments_score_low_calm():
    result = SentimentAnalyzer().compute_project_sentiment(
        ["This is a disaster, we are severely delayed and blocked on everything."]
    )
    assert result["score"] < 50


def test_score_bounded_0_100():
    analyzer = SentimentAnalyzer()
    for texts in ([""], ["terrible awful horrible"] * 5, ["wonderful amazing great"] * 5):
        result = analyzer.compute_project_sentiment(texts)
        assert 0 <= result["score"] <= 100
