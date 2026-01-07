"""
Content Generator Service - generates authentic, high-value Reddit content.

Philosophy: Every comment must genuinely help the reader. Product mentions are
rare and only when truly relevant. The account username IS the product -
interested users will discover it naturally by clicking the profile.
"""
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from openai import OpenAI
from anthropic import Anthropic

from app.core.config import settings
from app.models import Opportunity, Project, GeneratedContent, ContentStatus, ContentStyle

logger = logging.getLogger(__name__)


class MentionStrategy:
    """Determines if/how to mention the product based on context."""

    NEVER = "never"           # Pure value, no mention at all
    SUBTLE = "subtle"         # Hint through expertise, no direct mention
    NATURAL = "natural"       # Can mention if flows naturally
    DIRECT = "direct"         # Direct recommendation appropriate

    @staticmethod
    def analyze_opportunity(opportunity: Opportunity, project: Project) -> Tuple[str, str]:
        """
        Analyze the opportunity to determine appropriate mention strategy.

        Returns:
            Tuple of (strategy, reasoning)
        """
        title_lower = opportunity.post_title.lower()
        content_lower = (opportunity.post_content or "").lower()
        combined = f"{title_lower} {content_lower}"

        # Direct recommendation requests - can mention product
        recommendation_signals = [
            "recommend", "suggestion", "what do you use", "what should i",
            "looking for", "any good", "best way to", "how do you",
            "what's the best", "alternatives to", "similar to",
            "does anyone know", "help me find", "need advice on"
        ]

        # Questions seeking help - be helpful, maybe subtle hint
        help_signals = [
            "how do i", "how can i", "help with", "struggling with",
            "can't figure out", "problem with", "issue with", "doesn't work",
            "any tips", "advice", "question about"
        ]

        # Discussion/opinion threads - pure value, no mention
        discussion_signals = [
            "what do you think", "opinion on", "thoughts on", "discuss",
            "debate", "unpopular opinion", "hot take", "rant"
        ]

        # Check for recommendation requests first (highest intent)
        for signal in recommendation_signals:
            if signal in combined:
                return (
                    MentionStrategy.NATURAL,
                    f"User is actively seeking recommendations ('{signal}')"
                )

        # Check for help requests
        for signal in help_signals:
            if signal in combined:
                return (
                    MentionStrategy.SUBTLE,
                    f"User needs help ('{signal}') - focus on solving their problem"
                )

        # Discussion threads - pure value
        for signal in discussion_signals:
            if signal in combined:
                return (
                    MentionStrategy.NEVER,
                    f"Discussion thread ('{signal}') - contribute genuine perspective"
                )

        # Default: be helpful without any mention
        return (
            MentionStrategy.SUBTLE,
            "General post - provide value, let username speak for itself"
        )


class ContentGenerator:
    """
    Service for generating authentic Reddit content.

    Core Principles:
    1. GENUINE VALUE FIRST - Every comment must help the reader
    2. AUTHENTICITY - Write like a real person who happens to know about the topic
    3. NO PROMOTIONAL FEEL - Never feel like an ad or sponsored content
    4. USERNAME IS THE BRAND - Interested users will click the profile
    5. RARE MENTIONS - Only mention products when someone explicitly asks for recommendations
    """

    STYLES = {
        ContentStyle.HELPFUL_EXPERT.value: {
            "description": "Someone who genuinely knows their stuff and enjoys helping others",
            "voice": "confident but not arrogant, specific rather than generic",
            "approach": "Share real insights from experience, acknowledge complexity",
            "avoid": "lecturing, being preachy, over-explaining basics"
        },
        ContentStyle.CASUAL.value: {
            "description": "A friendly person who's been through similar situations",
            "voice": "warm, relatable, conversational",
            "approach": "Share personal angle, use casual language, be supportive",
            "avoid": "being too formal, corporate language, excessive positivity"
        },
        ContentStyle.TECHNICAL.value: {
            "description": "Someone with deep technical knowledge who can explain clearly",
            "voice": "precise, thorough, educational",
            "approach": "Break down complex topics, provide specific details, cite reasons",
            "avoid": "jargon without explanation, being condescending, wall of text"
        },
        ContentStyle.STORYTELLING.value: {
            "description": "Someone sharing a relevant personal experience",
            "voice": "authentic, engaging, human",
            "approach": "Connect through shared experience, make it relatable",
            "avoid": "making it about yourself, humble bragging, irrelevant tangents"
        }
    }

    # Language names for non-English content
    LANGUAGE_NAMES = {
        "en": "English", "et": "Estonian", "de": "German", "fr": "French",
        "es": "Spanish", "it": "Italian", "pt": "Portuguese", "nl": "Dutch",
        "pl": "Polish", "ru": "Russian", "uk": "Ukrainian", "ja": "Japanese",
        "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
        "sv": "Swedish", "no": "Norwegian", "da": "Danish", "fi": "Finnish",
        "lv": "Latvian", "lt": "Lithuanian",
    }

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None

        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_content(
        self,
        opportunity: Opportunity,
        project: Project,
        style: str = ContentStyle.HELPFUL_EXPERT.value
    ) -> GeneratedContent:
        """
        Generate authentic, valuable content for an opportunity.
        """
        # Analyze what mention strategy is appropriate
        mention_strategy, strategy_reason = MentionStrategy.analyze_opportunity(
            opportunity, project
        )

        logger.info(
            f"Generating content for opportunity {opportunity.id}: "
            f"strategy={mention_strategy}, reason={strategy_reason}"
        )

        # Build prompts
        system_prompt = self._build_system_prompt(
            project, opportunity.subreddit, style, mention_strategy
        )
        user_prompt = self._build_user_prompt(
            opportunity, project, style, mention_strategy
        )

        # Generate with GPT-5.2 (primary) or fallback
        content_text = None
        metadata = {}

        try:
            if self.openai_client:
                content_text, metadata = await self._generate_openai(system_prompt, user_prompt)
            elif self.anthropic_client:
                content_text, metadata = await self._generate_anthropic(system_prompt, user_prompt)
            else:
                raise ValueError("No LLM client configured")

        except Exception as e:
            logger.error(f"Primary LLM failed: {e}, trying fallback")
            if self.anthropic_client and self.openai_client:
                try:
                    content_text, metadata = await self._generate_anthropic(system_prompt, user_prompt)
                except Exception as e2:
                    logger.error(f"Fallback LLM also failed: {e2}")
                    raise

        if not content_text:
            raise ValueError("Failed to generate content")

        # Post-process to ensure quality
        content_text = self._post_process(content_text)

        # Create content object
        generated_content = GeneratedContent(
            opportunity_id=opportunity.id,
            project_id=project.id,
            content_text=content_text,
            content_type="comment",
            style=style,
            status=ContentStatus.DRAFT.value,
            content_metadata={
                **metadata,
                "style": style,
                "mention_strategy": mention_strategy,
                "strategy_reason": strategy_reason,
                "generated_at": datetime.utcnow().isoformat(),
            }
        )

        return generated_content

    async def _generate_openai(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate content using OpenAI Chat Completions API."""

        response = self.openai_client.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            max_tokens=settings.DEFAULT_LLM_MAX_TOKENS,
        )

        content = response.choices[0].message.content

        metadata = {
            "model": settings.DEFAULT_LLM_MODEL,
            "provider": "openai",
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        }

        return content, metadata

    async def _generate_anthropic(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate content using Anthropic Claude (fallback)."""
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=settings.DEFAULT_LLM_MAX_TOKENS,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.content[0].text
        metadata = {
            "model": "claude-sonnet-4",
            "provider": "anthropic",
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return content, metadata

    def _get_language_name(self, code: str) -> str:
        """Get full language name from ISO code."""
        if not code:
            return "English"
        return self.LANGUAGE_NAMES.get(code.lower(), code)

    def _build_system_prompt(
        self,
        project: Project,
        subreddit: str,
        style: str,
        mention_strategy: str
    ) -> str:
        """Build system prompt optimized for authentic, valuable content."""

        style_info = self.STYLES.get(style, self.STYLES[ContentStyle.HELPFUL_EXPERT.value])
        language_name = self._get_language_name(project.language) if project.language else None

        # Core identity prompt
        prompt = f"""You are a real Reddit user on r/{subreddit}. You have genuine knowledge and experience in your field. You're here because you enjoy helping people and being part of the community - NOT to promote anything.

YOUR PERSONALITY:
- {style_info['description']}
- Voice: {style_info['voice']}
- Approach: {style_info['approach']}
- Avoid: {style_info['avoid']}

AUTHENTICITY RULES (CRITICAL):
1. Write like a REAL person - use natural language, occasional imperfections are OK
2. Your comment must be GENUINELY HELPFUL even if the reader never learns about any product
3. Share real insights, not generic advice anyone could Google
4. Match r/{subreddit}'s culture - read the room
5. Be concise - Reddit rewards density of value, not length
6. If you don't know something, say so or don't comment on that aspect
7. React naturally to the post - empathy for frustrations, enthusiasm for wins

"""

        # Mention strategy instructions
        if mention_strategy == MentionStrategy.NEVER:
            prompt += """PRODUCT MENTIONS: DO NOT mention any product, service, or brand. Focus purely on helping with valuable advice or perspective. Your username already indicates your expertise area.

"""
        elif mention_strategy == MentionStrategy.SUBTLE:
            prompt += """PRODUCT MENTIONS: Do NOT directly mention any product or service. Just be helpful. If your advice naturally relates to your area of expertise, that's fine - but never name-drop. Interested readers will check your profile.

"""
        elif mention_strategy == MentionStrategy.NATURAL:
            prompt += """PRODUCT MENTIONS: You MAY mention a product/service IF AND ONLY IF:
- The user is explicitly asking for recommendations
- It genuinely fits their specific need (not just tangentially related)
- You frame it as one option among others, not THE answer
- You acknowledge it might not be perfect for everyone
- The mention feels like natural conversation, not a pitch

If these conditions aren't clearly met, don't mention anything. Being helpful without a mention is ALWAYS better than a forced mention.

"""
        elif mention_strategy == MentionStrategy.DIRECT:
            prompt += """PRODUCT MENTIONS: The user is actively seeking recommendations. You may suggest relevant solutions including products you know well. Be honest about pros AND cons. Compare with alternatives if relevant. Never oversell or make unrealistic claims.

"""

        # Add product context only if mentions are possible
        if mention_strategy in [MentionStrategy.NATURAL, MentionStrategy.DIRECT]:
            if project.product_context:
                prompt += f"""YOUR KNOWLEDGE (use naturally only when genuinely helpful):
{project.product_context}

Remember: Only mention this if the user's situation genuinely calls for it. Most comments should NOT mention it.

"""

        # Brand voice as personality traits (if provided)
        if project.brand_voice:
            prompt += f"""COMMUNICATION STYLE:
{project.brand_voice}

"""

        # Language requirements
        if language_name and project.language and project.language.lower() != "en":
            prompt += f"""LANGUAGE: Write entirely in {language_name}. Use natural {language_name} Reddit vernacular.

"""

        # Output format
        prompt += """OUTPUT: Write ONLY the Reddit comment. No meta-text, no "Here's a comment:", no explanations. Just the authentic comment a real user would post."""

        return prompt

    def _build_user_prompt(
        self,
        opportunity: Opportunity,
        project: Project,
        style: str,
        mention_strategy: str
    ) -> str:
        """Build user prompt with opportunity context."""

        prompt = f"""REDDIT POST TO RESPOND TO:

Subreddit: r/{opportunity.subreddit}
Title: {opportunity.post_title}
"""

        if opportunity.post_content:
            content = opportunity.post_content[:2500]
            prompt += f"""
Post Content:
{content}
"""

        prompt += f"""
Engagement: {opportunity.post_score} upvotes, {opportunity.post_num_comments} comments

---

Write a single Reddit comment responding to this post. Remember:
- Be genuinely helpful - this person has a real question or situation
- Your comment should add value whether or not anyone ever clicks your profile
- Sound like a real human, not a polished corporate response
- If you have relevant experience or knowledge, share specific insights"""

        # Style-specific nudge
        style_info = self.STYLES.get(style, self.STYLES[ContentStyle.HELPFUL_EXPERT.value])
        prompt += f"""
- Tone: {style_info['voice']}"""

        return prompt

    def _post_process(self, content: str) -> str:
        """Clean up generated content for Reddit."""

        # Remove any meta-commentary the model might have added
        meta_patterns = [
            r'^(Here\'s|Here is|I\'ll write|Let me write|My comment:?)[\s:]*\n*',
            r'\n*(Note:|P\.S\.|Edit:|---|\*\*\*|Hope this helps!?).*$',
            r'^["\']|["\']$',  # Surrounding quotes
        ]

        for pattern in meta_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)

        # Clean up excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()

        return content

    async def regenerate_content(
        self,
        content: GeneratedContent,
        opportunity: Opportunity,
        project: Project,
        feedback: Optional[str] = None,
        new_style: Optional[str] = None
    ) -> GeneratedContent:
        """Regenerate content with optional feedback."""

        style = new_style or content.style or ContentStyle.HELPFUL_EXPERT.value
        mention_strategy, strategy_reason = MentionStrategy.analyze_opportunity(
            opportunity, project
        )

        system_prompt = self._build_system_prompt(
            project, opportunity.subreddit, style, mention_strategy
        )
        user_prompt = self._build_user_prompt(
            opportunity, project, style, mention_strategy
        )

        if feedback:
            user_prompt += f"""

FEEDBACK ON PREVIOUS VERSION:
Previous attempt: "{content.content_text}"

Issues to address: {feedback}

Please write an improved version that addresses this feedback while maintaining authenticity."""

        content_text = None
        metadata = {}

        try:
            if self.openai_client:
                content_text, metadata = await self._generate_openai(system_prompt, user_prompt)
            elif self.anthropic_client:
                content_text, metadata = await self._generate_anthropic(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Regeneration failed: {e}")
            raise

        content_text = self._post_process(content_text)

        new_content = GeneratedContent(
            opportunity_id=opportunity.id,
            project_id=project.id,
            content_text=content_text,
            content_type="comment",
            style=style,
            status=ContentStatus.DRAFT.value,
            version=content.version + 1,
            parent_content_id=content.id,
            content_metadata={
                **metadata,
                "style": style,
                "mention_strategy": mention_strategy,
                "regenerated_from": content.id,
                "feedback": feedback,
                "generated_at": datetime.utcnow().isoformat(),
            }
        )

        return new_content

    async def generate_variants(
        self,
        opportunity: Opportunity,
        project: Project,
        styles: Optional[List[str]] = None,
        count: int = 3
    ) -> List[GeneratedContent]:
        """Generate multiple content variants with different styles."""

        if styles:
            selected_styles = styles[:count]
        else:
            selected_styles = [
                ContentStyle.HELPFUL_EXPERT.value,
                ContentStyle.CASUAL.value,
                ContentStyle.STORYTELLING.value,
            ][:count]

        variants = []
        for style in selected_styles:
            try:
                content = await self.generate_content(opportunity, project, style)
                variants.append(content)
            except Exception as e:
                logger.error(f"Failed to generate {style} variant: {e}")
                continue

        return variants
