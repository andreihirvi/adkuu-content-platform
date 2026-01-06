"""
Content Generator Service - generates Reddit content using LLMs.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from openai import OpenAI
from anthropic import Anthropic

from app.core.config import settings
from app.models import Opportunity, Project, GeneratedContent, ContentStatus, ContentStyle

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Service for generating Reddit content using LLMs.

    Supports OpenAI (primary) and Anthropic (fallback).
    Generates contextually appropriate, brand-aligned content.
    """

    STYLES = {
        ContentStyle.HELPFUL_EXPERT.value: {
            "description": "Professional, knowledgeable, and genuinely helpful",
            "tone": "informative yet approachable",
            "example": "Based on my experience..."
        },
        ContentStyle.CASUAL.value: {
            "description": "Friendly, conversational, like talking to a peer",
            "tone": "relaxed and natural",
            "example": "Hey! I've dealt with something similar..."
        },
        ContentStyle.TECHNICAL.value: {
            "description": "Detailed, precise, for technical audiences",
            "tone": "thorough and accurate",
            "example": "The technical solution involves..."
        },
        ContentStyle.STORYTELLING.value: {
            "description": "Personal narrative that relates to the topic",
            "tone": "engaging and relatable",
            "example": "This reminds me of when..."
        }
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
        Generate content for an opportunity.

        Args:
            opportunity: The opportunity to respond to
            project: The project context
            style: Content style to use

        Returns:
            GeneratedContent object
        """
        # Build prompts
        system_prompt = self._build_system_prompt(project, opportunity.subreddit, style)
        user_prompt = self._build_user_prompt(opportunity, project, style)

        # Try OpenAI first, fall back to Anthropic
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
                "generated_at": datetime.utcnow().isoformat(),
            }
        )

        return generated_content

    async def _generate_openai(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> tuple[str, Dict[str, Any]]:
        """Generate content using OpenAI."""
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
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }

        return content, metadata

    async def _generate_anthropic(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> tuple[str, Dict[str, Any]]:
        """Generate content using Anthropic Claude."""
        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=settings.DEFAULT_LLM_MAX_TOKENS,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.content[0].text
        metadata = {
            "model": "claude-3-haiku",
            "provider": "anthropic",
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return content, metadata

    # Map of ISO 639-1 codes to language names for prompts
    LANGUAGE_NAMES = {
        "en": "English",
        "et": "Estonian",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
        "uk": "Ukrainian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "ar": "Arabic",
        "hi": "Hindi",
        "sv": "Swedish",
        "no": "Norwegian",
        "da": "Danish",
        "fi": "Finnish",
        "lv": "Latvian",
        "lt": "Lithuanian",
    }

    def _get_language_name(self, code: str) -> str:
        """Get full language name from ISO code."""
        if not code:
            return "English"
        return self.LANGUAGE_NAMES.get(code.lower(), code)

    def _build_system_prompt(
        self,
        project: Project,
        subreddit: str,
        style: str
    ) -> str:
        """Build system prompt for content generation."""
        style_info = self.STYLES.get(style, self.STYLES[ContentStyle.HELPFUL_EXPERT.value])

        # Determine language instruction
        language_name = self._get_language_name(project.language) if project.language else "English"
        language_instruction = ""
        if project.language and project.language.lower() != "en":
            language_instruction = f"""
LANGUAGE REQUIREMENT:
You MUST write the entire comment in {language_name}. Do not use English unless it's a commonly used term in {language_name} Reddit communities.
"""

        prompt = f"""You are a helpful Reddit user writing a comment on r/{subreddit}.

CRITICAL RULES:
1. Write naturally like a real Reddit user - NO corporate speak
2. NEVER mention you're an AI or that you're promoting anything
3. Provide GENUINE VALUE first - the comment should be helpful even without any product mention
4. If mentioning a product/service, it must feel organic and relevant
5. Match the subreddit's culture and tone
6. Keep it concise - Reddit users prefer shorter, value-dense comments
7. NO promotional links unless absolutely natural
8. NO excessive punctuation or emoji
9. Be specific and actionable, not vague
{language_instruction}
STYLE: {style_info['description']}
TONE: {style_info['tone']}

"""

        if project.brand_voice:
            prompt += f"BRAND VOICE GUIDELINES:\n{project.brand_voice}\n\n"

        if project.product_context:
            prompt += f"PRODUCT/SERVICE CONTEXT (use naturally only if relevant):\n{project.product_context}\n\n"

        output_format = "Write ONLY the Reddit comment. No meta-commentary, no \"Here's a comment:\", just the actual comment text."
        if project.language and project.language.lower() != "en":
            output_format += f" Remember: write in {language_name}."

        prompt += f"""OUTPUT FORMAT:
{output_format}"""

        return prompt

    def _build_user_prompt(
        self,
        opportunity: Opportunity,
        project: Project,
        style: str
    ) -> str:
        """Build user prompt with opportunity context."""
        prompt = f"""POST TITLE: {opportunity.post_title}

SUBREDDIT: r/{opportunity.subreddit}

"""

        if opportunity.post_content:
            # Truncate if too long
            content = opportunity.post_content[:2000]
            prompt += f"POST CONTENT:\n{content}\n\n"

        prompt += f"""POST STATS: {opportunity.post_score} upvotes, {opportunity.post_num_comments} comments

Write a helpful, authentic Reddit comment responding to this post. Focus on providing value.
"""

        # Add style-specific guidance
        style_info = self.STYLES.get(style, self.STYLES[ContentStyle.HELPFUL_EXPERT.value])
        prompt += f"\nStyle guidance: {style_info['description']}"

        return prompt

    async def regenerate_content(
        self,
        content: GeneratedContent,
        opportunity: Opportunity,
        project: Project,
        feedback: Optional[str] = None,
        new_style: Optional[str] = None
    ) -> GeneratedContent:
        """
        Regenerate content with optional feedback.

        Args:
            content: Previous content to improve upon
            opportunity: Original opportunity
            project: Project context
            feedback: Optional feedback for improvement
            new_style: Optional different style

        Returns:
            New GeneratedContent object
        """
        style = new_style or content.style or ContentStyle.HELPFUL_EXPERT.value

        # Build prompts with feedback context
        system_prompt = self._build_system_prompt(project, opportunity.subreddit, style)

        user_prompt = self._build_user_prompt(opportunity, project, style)

        if feedback:
            user_prompt += f"\n\nPREVIOUS ATTEMPT (needs improvement):\n{content.content_text}\n"
            user_prompt += f"\nFEEDBACK TO ADDRESS:\n{feedback}\n"
            user_prompt += "\nPlease generate an improved version addressing the feedback."

        # Generate new content
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

        # Create new version
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
        """
        Generate multiple content variants.

        Args:
            opportunity: The opportunity
            project: Project context
            styles: Specific styles to use (or auto-select)
            count: Number of variants

        Returns:
            List of GeneratedContent objects
        """
        if styles:
            selected_styles = styles[:count]
        else:
            # Default style selection
            selected_styles = [
                ContentStyle.HELPFUL_EXPERT.value,
                ContentStyle.CASUAL.value,
                ContentStyle.TECHNICAL.value,
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
