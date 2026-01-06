"""
Text processing utilities for content analysis and generation.
"""
import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Promotional patterns to detect
PROMOTIONAL_PATTERNS = [
    r'\bcheck out\b',
    r'\bvisit\s+(our|my)\b',
    r'\bclick\s+(here|the\s+link)\b',
    r'\buse\s+(my|our|this)\s+code\b',
    r'\bdiscount\s+code\b',
    r'\bpromo\s+code\b',
    r'\baffiliate\b',
    r'\bsponsored\b',
    r'\b(buy|purchase)\s+now\b',
    r'\bfree\s+trial\b',
    r'\bsign\s+up\b',
    r'\bsubscribe\b.*\bchannel\b',
    r'\bfollow\s+(me|us)\b',
    r'\blink\s+in\s+(bio|description)\b',
]

# Spam indicators
SPAM_INDICATORS = [
    r'(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?',  # URLs
    r'\$\d+',  # Price mentions
    r'\d+%\s*off',  # Discount percentages
    r'!!!+',  # Excessive exclamation marks
    r'FREE\s*[A-Z]+',  # All caps FREE
    r'(?:BUY|SALE|DISCOUNT|OFFER|LIMITED)',  # Sales language (caps)
]


def detect_promotional_language(text: str) -> Dict[str, Any]:
    """
    Detect promotional language in text.

    Args:
        text: Text to analyze

    Returns:
        Dict with detection results
    """
    text_lower = text.lower()
    matches = []

    for pattern in PROMOTIONAL_PATTERNS:
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        if found:
            matches.extend(found)

    promotional_score = len(matches) / max(len(text.split()), 1)

    return {
        "is_promotional": len(matches) > 0,
        "promotional_score": min(promotional_score * 10, 1.0),
        "matches": matches[:10],  # Limit to first 10
        "match_count": len(matches),
    }


def detect_spam_patterns(text: str) -> Dict[str, Any]:
    """
    Detect spam patterns in text.

    Args:
        text: Text to analyze

    Returns:
        Dict with spam detection results
    """
    indicators = []

    for pattern in SPAM_INDICATORS:
        found = re.findall(pattern, text, re.IGNORECASE)
        if found:
            indicators.extend(found)

    # Check for excessive caps
    words = text.split()
    caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
    caps_ratio = caps_words / max(len(words), 1)

    # Check for repeated characters
    repeated_chars = bool(re.search(r'(.)\1{4,}', text))

    spam_score = (
        (len(indicators) * 0.2) +
        (caps_ratio * 0.5) +
        (0.3 if repeated_chars else 0)
    )

    return {
        "is_spam": spam_score > 0.3,
        "spam_score": min(spam_score, 1.0),
        "indicators": indicators[:10],
        "caps_ratio": caps_ratio,
        "has_repeated_chars": repeated_chars,
    }


def calculate_readability(text: str) -> Dict[str, Any]:
    """
    Calculate readability metrics for text.

    Args:
        text: Text to analyze

    Returns:
        Dict with readability metrics
    """
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Split into words
    words = text.split()

    if not words or not sentences:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "avg_sentence_length": 0,
            "readability_score": 0,
        }

    # Calculate metrics
    word_count = len(words)
    sentence_count = len(sentences)
    avg_sentence_length = word_count / sentence_count

    # Simple readability score (higher = easier to read)
    # Optimal: 10-20 words per sentence
    if avg_sentence_length < 10:
        readability_score = 0.8
    elif avg_sentence_length <= 20:
        readability_score = 1.0
    elif avg_sentence_length <= 30:
        readability_score = 0.7
    else:
        readability_score = 0.5

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": avg_sentence_length,
        "readability_score": readability_score,
    }


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract keywords from text.

    Args:
        text: Text to analyze
        top_n: Number of keywords to return

    Returns:
        List of keywords
    """
    # Common stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
        'she', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why',
        'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then',
    }

    # Extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    words = [w for w in words if w not in stop_words]

    # Count frequencies
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    return [word for word, _ in sorted_words[:top_n]]


def check_length_appropriate(
    text: str,
    content_type: str = "comment",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check if text length is appropriate for the content type.

    Args:
        text: Text to check
        content_type: Type of content (comment, post, reply)
        min_length: Minimum length override
        max_length: Maximum length override

    Returns:
        Dict with length check results
    """
    # Default lengths by type
    defaults = {
        "comment": {"min": 50, "max": 2000},
        "post": {"min": 100, "max": 10000},
        "reply": {"min": 20, "max": 1000},
    }

    type_defaults = defaults.get(content_type, defaults["comment"])

    min_len = min_length or type_defaults["min"]
    max_len = max_length or type_defaults["max"]

    word_count = len(text.split())
    char_count = len(text)

    is_appropriate = min_len <= char_count <= max_len

    return {
        "is_appropriate": is_appropriate,
        "char_count": char_count,
        "word_count": word_count,
        "min_length": min_len,
        "max_length": max_len,
        "too_short": char_count < min_len,
        "too_long": char_count > max_len,
    }


def calculate_authenticity_score(text: str, context: Optional[str] = None) -> float:
    """
    Calculate an authenticity score for generated content.

    Higher scores indicate more natural, authentic-sounding content.

    Args:
        text: Generated text to analyze
        context: Optional context (original post) for relevance

    Returns:
        float: Authenticity score (0-1)
    """
    score = 1.0

    # Penalize promotional language
    promo = detect_promotional_language(text)
    score -= promo["promotional_score"] * 0.3

    # Penalize spam patterns
    spam = detect_spam_patterns(text)
    score -= spam["spam_score"] * 0.4

    # Consider readability
    readability = calculate_readability(text)
    score *= readability["readability_score"]

    # Penalize very short or very long responses
    length = check_length_appropriate(text)
    if length["too_short"]:
        score -= 0.2
    if length["too_long"]:
        score -= 0.1

    # Bonus for natural elements
    # Has questions
    if '?' in text:
        score += 0.05

    # Has personal pronouns (seems more human)
    personal_pronouns = re.findall(r'\b(I|my|me|we|our)\b', text, re.IGNORECASE)
    if personal_pronouns:
        score += min(len(personal_pronouns) * 0.02, 0.1)

    return max(0.0, min(1.0, score))


def sanitize_for_reddit(text: str) -> str:
    """
    Sanitize text for posting to Reddit.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text
    """
    # Remove any tracking/affiliate links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\?[^)]*(?:ref|affiliate|utm)[^)]*\)', r'\1', text)

    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove excessive spaces
    text = re.sub(r' {2,}', ' ', text)

    # Trim
    text = text.strip()

    return text
