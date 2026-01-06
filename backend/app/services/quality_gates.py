"""
Quality Gates Service - validates generated content before publishing.
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.models import GeneratedContent, Opportunity, SubredditConfig
from app.utils.text_processing import (
    detect_promotional_language,
    detect_spam_patterns,
    calculate_readability,
    check_length_appropriate,
    calculate_authenticity_score,
)

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single quality check."""
    name: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityCheckResult:
    """Aggregated result of all quality checks."""
    passed: bool
    overall_score: float
    checks: List[CheckResult]
    blocking_issues: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "overall_score": self.overall_score,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "score": c.score,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
        }


class QualityGates:
    """
    Service for validating generated content quality.

    Runs multiple checks:
    - Spam detection
    - Promotional language detection
    - Length validation
    - Readability assessment
    - Subreddit compliance
    - Authenticity scoring
    """

    # Thresholds
    MAX_PROMOTIONAL_SCORE = 0.3
    MAX_SPAM_SCORE = 0.2
    MIN_READABILITY_SCORE = 0.5
    MIN_AUTHENTICITY_SCORE = 0.6
    PASS_THRESHOLD = 0.7  # Overall score threshold to pass

    def __init__(self):
        pass

    def run_all_checks(
        self,
        content: GeneratedContent,
        opportunity: Optional[Opportunity] = None,
        subreddit_config: Optional[SubredditConfig] = None
    ) -> QualityCheckResult:
        """
        Run all quality checks on content.

        Args:
            content: GeneratedContent to validate
            opportunity: Associated opportunity for context
            subreddit_config: Subreddit rules to check against

        Returns:
            QualityCheckResult with all check results
        """
        checks = []
        blocking_issues = []
        warnings = []

        text = content.content_text
        context = opportunity.post_title if opportunity else None

        # 1. Spam Detection
        spam_check = self._check_spam(text)
        checks.append(spam_check)
        if not spam_check.passed:
            blocking_issues.append(spam_check.message)

        # 2. Promotional Language
        promo_check = self._check_promotional(text)
        checks.append(promo_check)
        if not promo_check.passed:
            if promo_check.score > 0.5:
                blocking_issues.append(promo_check.message)
            else:
                warnings.append(promo_check.message)

        # 3. Length Check
        length_check = self._check_length(text, content.content_type)
        checks.append(length_check)
        if not length_check.passed:
            blocking_issues.append(length_check.message)

        # 4. Readability
        readability_check = self._check_readability(text)
        checks.append(readability_check)
        if not readability_check.passed:
            warnings.append(readability_check.message)

        # 5. Authenticity
        authenticity_check = self._check_authenticity(text, context)
        checks.append(authenticity_check)
        if not authenticity_check.passed:
            warnings.append(authenticity_check.message)

        # 6. Subreddit Compliance (if config available)
        if subreddit_config:
            compliance_check = self._check_subreddit_compliance(text, subreddit_config)
            checks.append(compliance_check)
            if not compliance_check.passed:
                blocking_issues.append(compliance_check.message)

        # Calculate overall score
        scores = [c.score for c in checks]
        overall_score = sum(scores) / len(scores) if scores else 0

        # Determine if passed
        passed = (
            len(blocking_issues) == 0 and
            overall_score >= self.PASS_THRESHOLD
        )

        return QualityCheckResult(
            passed=passed,
            overall_score=overall_score,
            checks=checks,
            blocking_issues=blocking_issues,
            warnings=warnings,
        )

    def _check_spam(self, text: str) -> CheckResult:
        """Check for spam patterns."""
        result = detect_spam_patterns(text)

        passed = result["spam_score"] < self.MAX_SPAM_SCORE
        score = 1.0 - result["spam_score"]

        message = "No spam patterns detected" if passed else f"Spam patterns detected: {result['indicators'][:3]}"

        return CheckResult(
            name="spam_detection",
            passed=passed,
            score=score,
            message=message,
            details=result,
        )

    def _check_promotional(self, text: str) -> CheckResult:
        """Check for promotional language."""
        result = detect_promotional_language(text)

        passed = result["promotional_score"] < self.MAX_PROMOTIONAL_SCORE
        score = 1.0 - result["promotional_score"]

        if not passed:
            message = f"Promotional language detected: {result['matches'][:3]}"
        else:
            message = "Content appears authentic"

        return CheckResult(
            name="promotional_language",
            passed=passed,
            score=score,
            message=message,
            details=result,
        )

    def _check_length(self, text: str, content_type: str = "comment") -> CheckResult:
        """Check content length appropriateness."""
        result = check_length_appropriate(text, content_type)

        passed = result["is_appropriate"]
        score = 1.0 if passed else 0.5

        if result["too_short"]:
            message = f"Content too short ({result['char_count']} chars, min {result['min_length']})"
        elif result["too_long"]:
            message = f"Content too long ({result['char_count']} chars, max {result['max_length']})"
        else:
            message = f"Content length appropriate ({result['char_count']} chars)"

        return CheckResult(
            name="length_check",
            passed=passed,
            score=score,
            message=message,
            details=result,
        )

    def _check_readability(self, text: str) -> CheckResult:
        """Check content readability."""
        result = calculate_readability(text)

        score = result["readability_score"]
        passed = score >= self.MIN_READABILITY_SCORE

        if passed:
            message = "Content is readable"
        else:
            message = f"Content may be hard to read (avg {result['avg_sentence_length']:.1f} words/sentence)"

        return CheckResult(
            name="readability",
            passed=passed,
            score=score,
            message=message,
            details=result,
        )

    def _check_authenticity(self, text: str, context: Optional[str] = None) -> CheckResult:
        """Check content authenticity."""
        score = calculate_authenticity_score(text, context)
        passed = score >= self.MIN_AUTHENTICITY_SCORE

        if passed:
            message = "Content appears authentic and natural"
        else:
            message = "Content may not sound authentic enough"

        return CheckResult(
            name="authenticity",
            passed=passed,
            score=score,
            message=message,
            details={"authenticity_score": score},
        )

    def _check_subreddit_compliance(
        self,
        text: str,
        config: SubredditConfig
    ) -> CheckResult:
        """Check compliance with subreddit rules."""
        issues = []

        # Check against posting rules if available
        if config.posting_rules:
            rules_lower = config.posting_rules.lower()

            # Check for common rule violations
            if "no self-promotion" in rules_lower:
                promo = detect_promotional_language(text)
                if promo["is_promotional"]:
                    issues.append("Self-promotion may be prohibited")

            if "no link" in rules_lower and "http" in text.lower():
                issues.append("Links may be prohibited")

        passed = len(issues) == 0
        score = 1.0 if passed else 0.5

        return CheckResult(
            name="subreddit_compliance",
            passed=passed,
            score=score,
            message="Compliant with subreddit rules" if passed else f"Potential issues: {issues}",
            details={"issues": issues, "subreddit": config.subreddit_name},
        )

    def quick_check(self, text: str) -> bool:
        """
        Quick pass/fail check without detailed results.

        Args:
            text: Content text to check

        Returns:
            bool: True if content passes basic checks
        """
        # Quick spam check
        spam = detect_spam_patterns(text)
        if spam["spam_score"] > self.MAX_SPAM_SCORE:
            return False

        # Quick promotional check
        promo = detect_promotional_language(text)
        if promo["promotional_score"] > self.MAX_PROMOTIONAL_SCORE:
            return False

        # Quick length check
        if len(text) < 50 or len(text) > 2000:
            return False

        return True

    def suggest_improvements(
        self,
        result: QualityCheckResult
    ) -> List[str]:
        """
        Suggest improvements based on check results.

        Args:
            result: QualityCheckResult from run_all_checks

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        for check in result.checks:
            if not check.passed:
                if check.name == "promotional_language":
                    suggestions.append("Remove or tone down promotional language. Focus on providing value first.")

                elif check.name == "spam_detection":
                    suggestions.append("Remove spam-like elements (excessive links, all caps, repeated characters).")

                elif check.name == "length_check":
                    if check.details.get("too_short"):
                        suggestions.append("Add more detail and value to the response.")
                    else:
                        suggestions.append("Shorten the response - Reddit users prefer concise content.")

                elif check.name == "readability":
                    suggestions.append("Use shorter sentences and simpler language.")

                elif check.name == "authenticity":
                    suggestions.append("Make the response sound more natural and conversational.")

                elif check.name == "subreddit_compliance":
                    suggestions.append(f"Review subreddit rules: {check.details.get('issues', [])}")

        return suggestions
