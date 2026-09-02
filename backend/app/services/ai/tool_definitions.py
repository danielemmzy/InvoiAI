"""
============================================================
AI Tool Definitions

These are the tools exposed to OpenAI.

This file contains ONLY schemas.

No execution.
No business logic.
No repositories.

Flow 7: "tool_registry.get_tools_for_context(ctx) -> IF
ctx.org.features.personal_mode: tools = PERSONAL_TOOLS ELSE:
tools = BUSINESS_TOOLS". Previously this file only had a flat
TOOLS list with no mode split — CORE_TOOLS below is that
original list (still available in every mode), and
BUSINESS_TOOLS / PERSONAL_TOOLS extend it per mode.
============================================================
"""

from __future__ import annotations

CORE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_document",
            "description": (
                "Retrieve a document by its UUID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document UUID.",
                    }
                },
                "required": [
                    "document_id",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_vendor",
            "description": (
                "Retrieve a vendor by UUID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor UUID.",
                    }
                },
                "required": [
                    "vendor_id",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_document",
            "description": (
                "Archive a document."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                    },
                    "archived_by": {
                        "type": "string",
                    },
                    "reason": {
                        "type": "string",
                    },
                },
                "required": [
                    "document_id",
                    "archived_by",
                ],
            },
        },
    },
]

# ============================================================
# Business Mode (Flow 7, Flow 10, Flow 14)
# ============================================================

BUSINESS_TOOLS = CORE_TOOLS + [{"type":"function","function":{"name":"get_document_workflow","description":"Get classification, route and processing status for a business document.","parameters":{"type":"object","properties":{"document_id":{"type":"string"}},"required":["document_id"]}}},
    {
        "type": "function",
        "function": {
            "name": "get_vendor_price_changes",
            "description": (
                "Get vendors whose prices increased recently, "
                "with the percentage increase and how many "
                "standard deviations above their historical "
                "average the latest invoice is. Use this for "
                "questions like 'which vendor increased prices "
                "most this month?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_similar_vendors",
            "description": (
                "Semantic search for vendors similar to a given "
                "name or description, e.g. 'find vendors similar "
                "to Amazon'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Vendor name or description to search for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_followup_email",
            "description": (
                "Draft a polite payment-reminder email for an "
                "overdue document, using the document's real "
                "vendor, amount, and due date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document UUID for the overdue invoice.",
                    },
                    "customer_id": {
                        "type": "string",
                        "description": "Optional customer identifier.",
                    },
                },
                "required": ["document_id"],
            },
        },
    },
]

# ============================================================
# Personal Mode (Flow 8)
# ============================================================

PERSONAL_TOOLS = CORE_TOOLS + [{"type":"function","function":{"name":"get_finance_snapshot","description":"Get personal accounts and latest statement freshness.","parameters":{"type":"object","properties":{},"required":[]}}},
    {
        "type": "function",
        "function": {
            "name": "record_paycheck",
            "description": (
                "Record income received (e.g. a paycheck) and "
                "regenerate the user's allocation plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Income amount.",
                    },
                    "source": {
                        "type": "string",
                        "description": (
                            "One of: salary, freelance, business, "
                            "investment, gift, refund, other."
                        ),
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_expense",
            "description": (
                "Log a personal expense. Category is "
                "auto-detected from the description if not "
                "given."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Expense amount.",
                    },
                    "description": {
                        "type": "string",
                        "description": "What the expense was for, e.g. 'fuel', 'Netflix'.",
                    },
                },
                "required": ["amount", "description"],
            },
        },
    },
]

# Backward-compatible name — some code may still import the flat
# list. Defaults to BUSINESS_TOOLS; prefer get_tools_for_mode()
# in new code.
TOOLS = BUSINESS_TOOLS


def get_tools_for_mode(personal_mode: bool) -> list[dict]:
    """
    Flow 7: "tool_registry.get_tools_for_context(ctx)". Call this
    with ctx.feature_flags.get("personal_mode", False) from the
    router/service layer.
    """
    return PERSONAL_TOOLS if personal_mode else BUSINESS_TOOLS
