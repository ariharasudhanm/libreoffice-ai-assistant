# LibreOffice AI Assistant Extension
# Copyright (c) 2026 Local MVP — MIT License
# See LICENSE file for details.

"""Prompt templates for the AI Assistant actions."""

REWRITE_TEMPLATE = (
    "Rewrite the following text. Preserve meaning. Do not add new facts. "
    "Keep formatting neutral. Tone: {tone}. "
    "Output ONLY the rewritten text — no explanations, no preamble, "
    "no commentary.\n\nText:\n{selection}"
)

SUMMARIZE_TEMPLATE = (
    "Summarize the following text to 30-40% of its original length. "
    "Preserve key points. Do not add new facts. "
    "Output ONLY the summary — no explanations, no preamble, "
    "no commentary.\n\nText:\n{selection}"
)

GRAMMAR_TEMPLATE = (
    "Fix all grammar, spelling, and punctuation errors in the following "
    "text. Preserve the original meaning and style. Do not rewrite or "
    "rephrase — only correct errors. "
    "Output ONLY the corrected text — no explanations, no preamble, "
    "no commentary.\n\nText:\n{selection}"
)

TRANSLATE_TEMPLATE = (
    "Translate the following text to {language}. "
    "Preserve the original meaning, tone, and formatting. "
    "Output ONLY the translation — no explanations, no preamble, "
    "no commentary.\n\nText:\n{selection}"
)

CONTINUE_TEMPLATE = (
    "Continue writing the following text. Match the same style, tone, "
    "and topic. Write approximately the same length as the original. "
    "Output ONLY the continuation — no explanations, no preamble, "
    "no commentary. Start exactly where the text leaves off.\n\n"
    "Text:\n{selection}"
)

SIMPLIFY_TEMPLATE = (
    "Simplify the following text to make it easier to understand. "
    "Use plain, clear language. Keep all key information but remove "
    "jargon, complex sentence structures, and unnecessary words. "
    "Output ONLY the simplified text — no explanations, no preamble, "
    "no commentary.\n\nText:\n{selection}"
)

CUSTOM_TEMPLATE = (
    "{instructions}\n\nText:\n{selection}"
)

# When custom instructions are appended to a standard action
EXTRA_INSTRUCTIONS = (
    "\n\nAdditional instructions: {instructions}"
)


def build_prompt(action, tone, selection, custom_instructions=""):
    """Build a prompt for the specified action.

    Args:
        action: 'rewrite', 'summarize', 'grammar', 'translate',
                'continue', 'simplify', or 'custom'
        tone: Tone for rewriting (e.g. 'Formal', 'Concise')
        selection: The selected text to process
        custom_instructions: Optional extra instructions from the user.
                            For translate, this is the target language.
    """
    action = (action or "").strip().lower()
    tone = (tone or "Formal").strip()
    selection = (selection or "").strip()
    custom_instructions = (custom_instructions or "").strip()

    if action == "custom":
        if not custom_instructions:
            custom_instructions = "Process the following text as instructed."
        return CUSTOM_TEMPLATE.format(
            instructions=custom_instructions,
            selection=selection,
        )

    if action == "grammar":
        prompt = GRAMMAR_TEMPLATE.format(selection=selection)
        if custom_instructions:
            prompt += EXTRA_INSTRUCTIONS.format(instructions=custom_instructions)
        return prompt

    if action == "translate":
        language = custom_instructions if custom_instructions else "English"
        prompt = TRANSLATE_TEMPLATE.format(language=language, selection=selection)
        return prompt

    if action == "continue":
        prompt = CONTINUE_TEMPLATE.format(selection=selection)
        if custom_instructions:
            prompt += EXTRA_INSTRUCTIONS.format(instructions=custom_instructions)
        return prompt

    if action == "simplify":
        prompt = SIMPLIFY_TEMPLATE.format(selection=selection)
        if custom_instructions:
            prompt += EXTRA_INSTRUCTIONS.format(instructions=custom_instructions)
        return prompt

    if action == "summarize":
        prompt = SUMMARIZE_TEMPLATE.format(selection=selection)
    else:
        prompt = REWRITE_TEMPLATE.format(tone=tone, selection=selection)

    # Append custom instructions if provided
    if custom_instructions:
        prompt += EXTRA_INSTRUCTIONS.format(instructions=custom_instructions)

    return prompt
