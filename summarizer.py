"""
Dynamic Conversational Summarizer for AR AI 1.5.
Takes extended message history (50-100 messages) and generates a structured server recap.
"""

from typing import List, Dict, Any
import re

SUMMARY_TRIGGERS = [
    r'\bsummar(y|ize|ise)\b',
    r'\bwhat happened\b',
    r'\bcatch me up\b',
    r'\btldr\b',
    r'\brecap\b',
    r'\bwhats been going on\b',
    r'\bwhat did i miss\b'
]

def is_summary_request(text: str) -> bool:
    if not text:
        return False
    t_lower = text.lower()
    return any(re.search(p, t_lower) for p in SUMMARY_TRIGGERS)


def generate_chat_summary(history: List[Dict[str, str]]) -> str:
    """Generate a coherent, multi-turn summary of the previous chat history."""
    if not history or len(history) < 2:
        return "not much happened recently bro chat was pretty quiet ngl 💀"

    # Collect conversational turns
    user_msgs = [m["content"] for m in history if m.get("role") in ("user", "human") and len(m.get("content", "")) > 3]

    if not user_msgs:
        return "chat was mostly quick messages nothing major went down"

    # Identify recurring topics
    topics = []
    text_blob = " ".join(user_msgs).lower()

    if any(k in text_blob for k in ["smp", "minecraft", "mc", "nether", "base", "diamond"]):
        topics.append("the minecraft smp and base grinding")
    if any(k in text_blob for k in ["brawl stars", "brawler", "knockout", "hypercharge"]):
        topics.append("brawl stars meta and grinding trophies")
    if any(k in text_blob for k in ["rivals", "roblox", "loadout", "blade ball"]):
        topics.append("roblox rivals loadouts and 1v1s")
    if any(k in text_blob for k in ["acorn", "spelling", "typo"]):
        topics.append("clowning acorn for his spelling typos 😭")
    if any(k in text_blob for k in ["math", "algebra", "hw", "homework", "science"]):
        topics.append("helping out with homework and math problems")

    # Sample key snippets
    recent_highlights = user_msgs[-6:]

    lines = ["heres the recap of what went down in chat 🗣️:"]
    if topics:
        lines.append(f"- main topics were {', '.join(topics)}".replace(",", ""))
    
    # Extract 2-3 specific conversational points
    if len(recent_highlights) >= 2:
        lines.append(f"- people were discussing: \"{recent_highlights[0]}\" and \"{recent_highlights[-1]}\"".replace('"', ''))
    
    lines.append("- overall chat was active and everyone was locked in 🔥")
    return "\n".join(lines).lower().replace(",", "").replace(".", "")


if __name__ == "__main__":
    test_hist = [
        {"role": "user", "content": "yo acorn get on the smp"},
        {"role": "assistant", "content": "bet lets build the nether highway"},
        {"role": "user", "content": "acorn spelled diamond with three ms again 💀"},
        {"role": "assistant", "content": "classic acorn spelling moment 😭"},
        {"role": "user", "content": "can someone give me a summary of what happened"}
    ]
    print(generate_chat_summary(test_hist))
