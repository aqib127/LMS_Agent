"""
Format command/LLM output for Streamlit markdown and Telegram.
Fixes the "wall of text" issue by ensuring bullets render as proper lists.
"""
import re


# Emojis that typically start a list item on a new line
ITEM_EMOJIS = ["📅", "⏰", "📢", "📄", "📝", "🎓", "💰", "🤝",
               "📊", "📚", "📉", "✅", "⚠️", "❌", "🔴", "📥", "🎥"]


def clean_for_streamlit(text: str) -> str:
    """Convert '•' bullets to markdown list items, split emojis onto new lines."""
    if not text:
        return ""

    # Unicode bullet → markdown bullet
    text = text.replace("• ", "\n- ")

    # Ensure each emoji that starts a new item is on its own line
    for emoji in ITEM_EMOJIS:
        text = re.sub(rf"\s*{re.escape(emoji)}", f"\n{emoji}", text)

    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading newlines
    return text.strip()


def clean_for_telegram(text: str) -> str:
    return text
