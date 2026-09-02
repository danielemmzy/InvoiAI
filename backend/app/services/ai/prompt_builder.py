"""
============================================================
Prompt Builder

Responsible for constructing prompts for the LLM.

Responsibilities
----------------
- Build system prompt
- Inject semantic context
- Apply AI instructions
- Keep prompt formatting consistent

No OpenAI calls.

No repositories.

No business logic.
============================================================
"""

from __future__ import annotations


class PromptBuilder:
    """
    Builds prompts for GPT.
    """

    SYSTEM_PROMPT = """
You are InvoiAI.

You are an AI finance copilot that assists businesses with
documents, invoices, receipts, vendors, expenses,
organizations and financial workflows.

Rules

- Always answer truthfully.
- Never invent information.
- Use retrieved context whenever possible.
- If information is unavailable, clearly say so.
- Keep answers concise unless the user requests detail.
- Use markdown formatting when appropriate.
- If a tool can better answer the request,
  call the appropriate tool.
"""

    # =====================================================
    # System Prompt
    # =====================================================

    @classmethod
    def build_system_prompt(
        cls,
        *,
        context: str,
    ) -> str:
        """
        Creates the system prompt with semantic context.
        """

        if not context.strip():
            return cls.SYSTEM_PROMPT.strip()

        return f"""
{cls.SYSTEM_PROMPT.strip()}

============================================================
Retrieved Context
============================================================

{context}
""".strip()

    # =====================================================
    # User Prompt
    # =====================================================

    @staticmethod
    def build_user_prompt(
        message: str,
    ) -> str:
        """
        Formats the user prompt.
        """

        return message.strip()

    # =====================================================
    # Complete Prompt
    # =====================================================

    @classmethod
    def build(
        cls,
        *,
        context: str,
        message: str,
    ) -> tuple[str, str]:
        """
        Returns

        (
            system_prompt,
            user_prompt,
        )
        """

        return (
            cls.build_system_prompt(
                context=context,
            ),
            cls.build_user_prompt(
                message,
            ),
        )