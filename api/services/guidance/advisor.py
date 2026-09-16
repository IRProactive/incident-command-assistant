"""
Turns retrieved context chunks + the incident lead's question into a
grounded answer via the Anthropic API. Provider/key/model are runtime-
configurable through services/config.py (settable from the frontend's
Settings panel) rather than fixed at container build time.

Provider "none" (the default until someone configures one) keeps this
fully offline for air-gapped use — retrieval still works and its sources
are still returned, just without a synthesized answer on top.
"""
from services import config

SYSTEM_PROMPT = (
    "You are assisting an incident lead during an active security incident. "
    "Answer only using the provided context passages — do not add information "
    "you weren't given. Each passage is labeled either [org_doc] (the "
    "organization's own incident response plan) or [reference] (an external "
    "standard, e.g. NIST SP 800-61r3). Distinguish clearly in your answer "
    "between what the org's own plan says and what the external standard "
    "recommends — these are not the same thing and shouldn't be blended "
    "together as if they were. If the context doesn't actually answer the "
    "question, say so plainly rather than guessing or padding the answer."
)


async def generate_guidance(question: str, context_chunks: list[dict]) -> str:
    if not context_chunks:
        return "No relevant passages found in the loaded documents for that question."

    provider = config.get_provider()

    if provider == "none":
        return (
            f"Found {len(context_chunks)} relevant passage(s) but no LLM provider is "
            "configured yet — see 'sources' below for what retrieval matched. "
            "Set one up from the Settings panel to generate a synthesized answer."
        )

    if provider == "anthropic":
        return await _generate_with_anthropic(question, context_chunks)

    return f"Unrecognized LLM provider '{provider}' — check the Settings panel."


async def _generate_with_anthropic(question: str, context_chunks: list[dict]) -> str:
    api_key = config.get_api_key()
    if not api_key:
        return "Anthropic is selected as the provider, but no API key is configured. Add one from the Settings panel."

    try:
        import anthropic
    except ImportError:
        return (
            "The 'anthropic' package isn't installed in this container. "
            "It should be in api/requirements.txt — rebuild the API image."
        )

    context_text = "\n\n".join(f"[{c['kind']}] {c['source']}\n{c['text']}" for c in context_chunks)
    user_message = f"Context passages:\n\n{context_text}\n\nIncident lead's question: {question}"

    client = anthropic.AsyncAnthropic(api_key=api_key)
    try:
        response = await client.messages.create(
            model=config.get_model(),
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.AuthenticationError:
        return "Anthropic rejected the configured API key — check it in the Settings panel."
    except anthropic.APIError as e:
        return f"Anthropic API error: {e}"
    except Exception as e:  # keep the guidance endpoint usable even on an unexpected client-side failure
        return f"Unexpected error calling Anthropic: {e}"

    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "\n".join(text_blocks) if text_blocks else "The model returned no text content."
