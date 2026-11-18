"""
Script & Scene Generator powered by Google Gemini Free API
Produces high-retention documentary scripts, scene breakdowns, and visual prompts.
"""

import json
import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from src.config import Config

logger = logging.getLogger("youtube_agent.script")


class Scene(BaseModel):
    narration: str = Field(
        ...,
        description="Engaging spoken narration in the requested language (Urdu/Hindi script or English), ~5-8 seconds of speech.",
    )
    image_prompt: str = Field(
        ...,
        description="Detailed cinematic, dark-moody, hyper-realistic documentary illustration prompt in English (16:9).",
    )
    on_screen_text: str = Field(
        ...,
        description="Short key date, location, or highlight phrase (2-5 words) to overlay on screen.",
    )
    is_hook_clip: bool = Field(
        default=False,
        description="Set to true for the 3-4 consecutive scenes (~30-45s total) that contain the most intense mystery hook to repurpose as a vertical teaser Short.",
    )


class ContentVariant(BaseModel):
    title: str = Field(..., description="High-CTR title variant.")
    thumbnail_prompt: str = Field(..., description="16:9 visual illustration prompt.")
    thumbnail_text: str = Field(..., description="Short 2-4 word punchy hook text.")


class DocumentaryScript(BaseModel):
    title: str = Field(..., description="High-CTR, curiosity-driven documentary title.")
    description: str = Field(
        ...,
        description="SEO-optimized description including synopsis, key timestamps, and hashtags.",
    )
    tags: List[str] = Field(..., description="Array of 10-15 high-ranking SEO tags.")
    thumbnail_prompt: str = Field(
        ...,
        description="Detailed visual prompt for generating a dramatic, click-worthy 16:9 thumbnail.",
    )
    thumbnail_text: str = Field(
        ...,
        description="Short 2-4 word punchy hook text for thumbnail typography.",
    )
    variant_a: Optional[ContentVariant] = Field(
        default=None,
        description="Primary high-CTR documentary title & thumbnail variant.",
    )
    variant_b: Optional[ContentVariant] = Field(
        default=None,
        description="Alternative curiosity-gap / forensic anomaly title & thumbnail variant for A/B testing.",
    )
    variant_c: Optional[ContentVariant] = Field(
        default=None,
        description="Alternative controversial / forbidden truth title & thumbnail variant for A/B testing.",
    )
    youtube_pinned_comment: str = Field(
        default="",
        description="Curiosity-driven, controversial, or engaging question to pin at the top of YouTube comments to maximize engagement.",
    )
    facebook_post: str = Field(
        default="",
        description="Compelling storytelling post with an intense hook, summary, and call-to-action to watch the full documentary.",
    )
    twitter_thread: List[str] = Field(
        default_factory=list,
        description="A thread of 3-4 suspenseful tweets breaking down the core anomalies of the mystery.",
    )
    telegram_post: str = Field(
        default="",
        description="Formatted broadcast update with emojis and bold highlights for Telegram channels.",
    )
    scenes: List[Scene] = Field(
        ...,
        description="Chronological scene sequence matching target duration.",
    )


def _clean_json_response(raw_text: str) -> str:
    """Extract and sanitize raw JSON from model response."""
    text = raw_text.strip()
    # Strip markdown code fence if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()


def build_system_prompt(language: str, target_scenes: int, genre: str = "documentary") -> str:
    """Construct a documentary or cinematic film director system prompt."""
    lang_instruction = ""
    if language == "urdu":
        lang_instruction = (
            "LANGUAGE REQUIREMENT (CRITICAL): The `narration` field of every scene MUST be written in "
            "standard, natural spoken Urdu script (اردو رسم الخط - Nastaliq/Naskh characters). "
            "Do NOT write romanized Urdu. Ensure proper sentence flow and punctuation for Edge-TTS (`ur-PK-AsadNeural`). "
            "Use deep, suspenseful vocabulary reminiscent of elite mystery documentary channels like 'Info with Ahsan' "
            "or dramatic cinematic storytelling. "
            "Keep `image_prompt`, `title`, `description`, `tags`, and `thumbnail_prompt` in English or bilingual for best SEO."
        )
    elif language == "hindi":
        lang_instruction = (
            "LANGUAGE REQUIREMENT (CRITICAL): The `narration` field of every scene MUST be written in "
            "natural spoken Hindi in Devanagari script (हिन्दी). Do NOT use Roman Hindi. "
            "Ensure clear phrasing and suspenseful documentary tone for Edge-TTS (`hi-IN-MadhurNeural`). "
            "Keep `image_prompt` in English."
        )
    else:
        lang_instruction = (
            "LANGUAGE REQUIREMENT: The `narration` field must be written in dramatic, suspenseful English "
            "matching Vox and MagnatesMedia investigative documentary storytelling or cinematic feature film dialogue."
        )

    if genre in ("film", "story", "movie"):
        role_description = (
            "You are an elite Hollywood Dark Fantasy & Cinematic Story Film Director (style: Guillermo del Toro, Denis Villeneuve, and 'Tales of the Underworld').\n"
            "Your goal is to transform the premise into an emotionally gripping, suspenseful fictional cinematic narrative film with character arcs, dialogue, visceral world-building, and high-retention pacing."
        )
        structure_guidelines = f"""
CINEMATIC FILM STRUCTURE & PACING:
1. Target Scene Count: Exactly {target_scenes} scenes (~6 to 8 seconds of narration or character dialogue per scene).
2. ACT 1 - The Inciting Incident & Secret (Scenes 1 to {int(target_scenes * 0.3)}): Establish the tragic protagonist, the ancient curse, or the forbidden ritual, ending with the terrifying birth or discovery.
3. ACT 2 - The Rising Horror & Maternal Bond (Scenes {int(target_scenes * 0.3) + 1} to {int(target_scenes * 0.7)}): The creature grows, the mother tries desperately to protect it from the suspicious villagers or hunters, and tension escalates.
4. ACT 3 - The Climax & Final Sacrifice (Scenes {int(target_scenes * 0.7) + 1} to {target_scenes}): The confrontation erupts. Flames, heartbreak, blood, and a deeply emotional twist ending that haunts the viewer.

VISUAL PROMPT GUIDELINES (`image_prompt`):
- Describe dynamic cinematography for video generation (e.g. 'Tracking dolly shot, close-up of mother's tearful face, tiny dragon with glowing obsidian scales curled in her arms breathing blue flame, dark fantasy chiaroscuro lighting, 8k, photorealistic').
- Keep visual consistency across character descriptions throughout the film.
"""
    else:
        role_description = (
            "You are an elite Senior Investigative Documentary Director and Scriptwriter (style: 'Info with Ahsan', 'Vox', 'MagnatesMedia', and 'Fern').\n"
            "Your goal is to transform any topic into an ultra-high-retention, suspenseful visual documentary video."
        )
        structure_guidelines = f"""
DOCUMENTARY STRUCTURE & PACING GUIDELINES:
1. Target Scene Count: Exactly {target_scenes} scenes (~5 to 8 seconds of narration per scene).
2. The Hook (Scene 1): Immediate intrigue within the first 3-5 seconds. Never start with "Welcome back" or generic intros. Start right in the middle of the tension or shocking mystery.
3. The Build-up (Scenes 2 to {int(target_scenes * 0.4)}): Present the historical context, the eerie silence before the event, the key figures, and the chilling anomalies.
4. The Investigation & Climax (Scenes {int(target_scenes * 0.4) + 1} to {int(target_scenes * 0.85)}): Deconstruct the evidence, theories, leaked records, or pivotal moments with escalating suspense.
5. The Resolution / Cliffhanger (Final Scenes): Synthesize the mystery, leave the viewer contemplating the unanswered questions, and deliver a memorable closing punchline.

VISUAL PROMPT GUIDELINES (`image_prompt`):
- Each image prompt MUST be in English.
- Describe cinematic framing, dramatic chiaroscuro / volumetric lighting, 35mm documentary film grain, dark moody atmospheric tones, hyper-realistic details, and historical or forensic archive aesthetic.
- Specify: "16:9 wide shot, dark moody documentary style, cinematic volumetric lighting, 8k, photorealistic, no text, no watermark".
"""

    return f"""{role_description}

{structure_guidelines}

{lang_instruction}

OUTPUT FORMAT:
Return a single, strictly valid JSON object matching this exact schema:
{{
  "title": "Dramatic High-CTR Documentary Title (60 chars max)",
  "description": "Engaging 3-paragraph YouTube description with timestamps and tags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "thumbnail_prompt": "Ultra-detailed 16:9 prompt for a dramatic thumbnail background",
  "thumbnail_text": "2-4 WORDS PUNCHY HOOK",
  "variant_a": {{
    "title": "Primary High-CTR Title (e.g. The Untold Story of Flight 370)",
    "thumbnail_prompt": "16:9 cinematic thumbnail illustration prompt",
    "thumbnail_text": "VANISHED FOREVER"
  }},
  "variant_b": {{
    "title": "Curiosity-Gap Title (e.g. The 3 Minutes Radar Can't Explain)",
    "thumbnail_prompt": "Alternative visual prompt focusing on radar map & eerie ocean",
    "thumbnail_text": "THE GLITCH"
  }},
  "variant_c": {{
    "title": "Controversial Question Title (e.g. What Did the Navy Hide?)",
    "thumbnail_prompt": "Alternative visual prompt focusing on classified files & forensic anomalies",
    "thumbnail_text": "THE COVERUP"
  }},
  "youtube_pinned_comment": "Curiosity question to provoke discussion in comments (e.g. 'Do you believe it was an inside cover-up or a bizarre natural anomaly? Let me know your theory below 👇')",
  "facebook_post": "Compelling suspenseful hook post for Facebook Page with emojis and call to action to watch the full documentary.",
  "twitter_thread": [
    "Tweet 1: Shocking hook introducing the core anomaly of the mystery...",
    "Tweet 2: Crucial clue, declassified record, or leaked evidence...",
    "Tweet 3: The unexplained twist that still puzzles investigators...",
    "Tweet 4: Summary conclusion with cliffhanger..."
  ],
  "telegram_post": "Formatted announcement with bold title, mystery summary bullet points, and CTA for Telegram broadcast channel.",
  "scenes": [
    {{
      "narration": "Narration text for this 5-8s clip in the target language script",
      "image_prompt": "Cinematic 16:9 visual prompt in English",
      "on_screen_text": "Date / Location / Key Phrase (2-4 words)",
      "is_hook_clip": true
    }}
  ]
}}

CRITICAL HOOK CLIP INSTRUCTION:
Mark exactly 3 to 4 consecutive scenes (totaling ~30-45 seconds) with `"is_hook_clip": true` (usually scenes 1-4 or the peak climax scenes). All other scenes must have `"is_hook_clip": false`. These marked scenes will be automatically cropped and rendered as a 9:16 vertical teaser Short!

Do NOT include any commentary, Markdown backticks, or text outside the JSON object.
"""


def generate_documentary_script(
    topic: str,
    duration_minutes: int = 2,
    language: str = "urdu",
    genre: str = "documentary",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> DocumentaryScript:
    """Generate a complete documentary or cinematic film script using Gemini API."""
    key = api_key or Config.GEMINI_API_KEY
    model = model_name or Config.GEMINI_MODEL

    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Please add your free key to .env "
            "or pass it as an argument."
        )

    # Calculate target scenes: roughly 9-10 scenes per minute (6 seconds average per scene)
    target_scenes = max(4, int(duration_minutes * 9))
    system_prompt = build_system_prompt(language=language, target_scenes=target_scenes, genre=genre)

    label = "Film Story" if genre in ("film", "story", "movie") else "Documentary"
    user_prompt = (
        f"Format: {label}\n"
        f"Topic / Premise: '{topic}'\n"
        f"Target Duration: {duration_minutes} minute(s)\n"
        f"Target Scene Count: {target_scenes} scenes\n"
        f"Language: {language}\n\n"
        "Generate the complete JSON response now."
    )

    logger.info(f"Requesting {label} script from Gemini ({model}) for topic: '{topic}'...")

    raw_response_text = ""

    # Attempt using new `google-genai` SDK first
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )
        raw_response_text = response.text or ""
    except (ImportError, Exception) as genai_err:
        logger.debug(f"google-genai SDK call did not succeed ({genai_err}), falling back to google-generativeai...")
        # Fallback to `google.generativeai` SDK
        try:
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=key)
            gen_model = legacy_genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.7},
            )
            resp = gen_model.generate_content(user_prompt)
            raw_response_text = resp.text or ""
        except Exception as legacy_err:
            raise RuntimeError(
                f"Failed to generate script using Gemini API. Errors encountered:\n"
                f"SDK 1 error: {genai_err}\n"
                f"SDK 2 error: {legacy_err}"
            ) from legacy_err

    cleaned_json = _clean_json_response(raw_response_text)

    try:
        parsed_dict = json.loads(cleaned_json)
        script = DocumentaryScript.model_validate(parsed_dict)

        # Ensure all 3 A/B testing variants are populated
        if not script.variant_a:
            script.variant_a = ContentVariant(
                title=script.title,
                thumbnail_prompt=script.thumbnail_prompt,
                thumbnail_text=script.thumbnail_text,
            )
        if not script.variant_b:
            script.variant_b = ContentVariant(
                title=f"The 3 Anomalies That Defy Science: {script.title}",
                thumbnail_prompt=script.thumbnail_prompt + ", ominous dark investigation archive room",
                thumbnail_text="THE EVIDENCE",
            )
        if not script.variant_c:
            script.variant_c = ContentVariant(
                title=f"What Really Happened? The Untold Truth of {topic}",
                thumbnail_prompt=script.thumbnail_prompt + ", classified redacted records, dramatic neon backlight",
                thumbnail_text="THE TRUTH",
            )

        logger.info(
            f"Successfully generated script: '{script.title}' with {len(script.scenes)} scenes "
            f"and 3 A/B test variants."
        )
        return script
    except Exception as parse_err:
        logger.error(f"Failed to parse Gemini JSON response. Raw output:\n{raw_response_text}")
        raise ValueError(f"Gemini output could not be parsed as valid DocumentaryScript: {parse_err}")
