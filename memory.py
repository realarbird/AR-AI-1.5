"""
Living Memory & Channel Sanitization Module for AR AI 1.5 (Retard Bot).
Lively, witty, and authentic Acorn's Dictatorship roster with automatic channel redaction.
Includes Discord user ID mapping, mention resolution, and conversation cooldown tracking.
"""

from typing import Dict, List, Optional, Any
import re
import time
import json
import glob
import os
from pathlib import Path

SERVER_INFO = {
    "server_name": "acorns dictatorship",
    "bot_name": "retard bot",
    "developer_username": "realarbird"
}

# Discord username -> numeric User ID mapping (extracted from chat exports)
USERNAME_TO_DISCORD_ID: Dict[str, str] = {
    "realarbird": "1015271651165872209",
    "ar bird": "1015271651165872209",
    "arbird": "1015271651165872209",
    "ayan": "1015271651165872209",
    "cactusmaximus": "1176709426539929650",
    "cactusmaximus1": "1176709426539929650",
    "ryan": "1176709426539929650",
    "cactus": "1176709426539929650",
    "iamacorn": "1158380010042818582",
    "lordoftheacorns": "1158380010042818582",
    "acorn": "1158380010042818582",
    "aaron": "1158380010042818582",
    "mat2000mat": "891068533755244585",
    "matthew": "891068533755244585",
    "mat2": "891068533755244585",
    "mat": "891068533755244585",
    "ghastz_": "1126220555884957747",
    "michael": "1126220555884957747",
    "miguel": "1126220555884957747",
    "indications.": "1155209176134451330",
    "utopia": "1155209176134451330",
    "tim": "1155209176134451330",
    "timoti": "1155209176134451330",
    "leuniaa.": "1243385718370340927",
    "lemon": "1243385718370340927",
    "lindsay": "1243385718370340927",
    "eff3rvescent": "1179514728779886663",
    "cherry": "1179514728779886663",
    "emma": "1179514728779886663",
    "emochicken": "1179514728779886663",
    "cate_m_cate": "865774655066865686",
    "blueberry": "865774655066865686",
    "catherine": "865774655066865686",
    "froggie": "865774655066865686",
    "candymuncher09": "1078846574190415893",
    "kiwi": "1078846574190415893",
    "amelia": "1078846574190415893",
}

# Discord username -> friendly name mapping
SENDER_TO_FRIENDLY_NAME: Dict[str, str] = {
    "realarbird": "Ayan (AR Bird)",
    "ar bird": "Ayan (AR Bird)",
    "arbird": "Ayan (AR Bird)",
    "ayan": "Ayan (AR Bird)",
    "ayanangelato": "Ayan (AR Bird)",
    "cactusmaximus": "Ryan (CactusMaximus)",
    "cactusmaximus1": "Ryan (CactusMaximus)",
    "ryan": "Ryan (CactusMaximus)",
    "cactus": "Ryan (CactusMaximus)",
    "iamacorn": "Aaron (Acorn)",
    "lordoftheacorns": "Aaron (Acorn)",
    "acorn": "Aaron (Acorn)",
    "aaron": "Aaron (Acorn)",
    "mat2000mat": "Matthew",
    "matthew": "Matthew",
    "mat2": "Matthew",
    "mat": "Matthew",
    "ghastz_": "Michael",
    "michael": "Michael",
    "miguel": "Michael",
    "indications.": "Tim (Utopia)",
    "utopia": "Tim (Utopia)",
    "tim": "Tim (Utopia)",
    "timoti": "Tim (Utopia)",
    "leuniaa.": "Lindsay (Lemon)",
    "lemon": "Lindsay (Lemon)",
    "lindsay": "Lindsay (Lemon)",
    "eff3rvescent": "Emma (Cherry)",
    "cherry": "Emma (Cherry)",
    "emma": "Emma (Cherry)",
    "emochicken": "Emma (Cherry)",
    "cate_m_cate": "Catherine (Blueberry)",
    "blueberry": "Catherine (Blueberry)",
    "catherine": "Catherine (Blueberry)",
    "froggie": "Catherine (Blueberry)",
    "candymuncher09": "Amelia (Kiwi)",
    "kiwi": "Amelia (Kiwi)",
    "amelia": "Amelia (Kiwi)",
}

# Discord User ID -> friendly name mapping
DISCORD_ID_TO_FRIENDLY: Dict[str, str] = {
    "1015271651165872209": "Ayan (AR Bird)",
    "1158380010042818582": "Aaron (Acorn)",
    "1176709426539929650": "Ryan (CactusMaximus)",
    "1155209176134451330": "Tim (Utopia)",
    "1243385718370340927": "Lindsay (Lemon)",
    "1179514728779886663": "Emma (Cherry)",
    "865774655066865686": "Catherine (Blueberry)",
    "1078846574190415893": "Amelia (Kiwi)",
    "891068533755244585": "Matthew",
    "1126220555884957747": "Michael",
}

def get_friendly_sender_name(sender_key: str) -> str:
    """Resolve raw sender username or numeric Discord ID into friendly member name."""
    if not sender_key:
        return "Chatter"
    k = sender_key.lower().strip()
    if k in DISCORD_ID_TO_FRIENDLY:
        return DISCORD_ID_TO_FRIENDLY[k]
    if k in SENDER_TO_FRIENDLY_NAME:
        return SENDER_TO_FRIENDLY_NAME[k]
    return sender_key.title() if len(sender_key) <= 15 else "Chatter"

# Per-user conversation memory reset flags for "bye now" / reset feature
_memory_reset_flags: Dict[str, float] = {}

def set_memory_reset_needed(sender_key: str):
    """Mark a sender as needing a fresh context (memory wipe) on their next message."""
    _memory_reset_flags[sender_key] = time.time()

def pop_memory_reset_needed(sender_key: str) -> bool:
    """Check and consume the memory reset flag for a sender. Returns True if memory should be cleared."""
    if sender_key in _memory_reset_flags:
        # Check 10-minute expiry
        ts = _memory_reset_flags.pop(sender_key, 0)
        return (time.time() - ts) < 600
    return False

def resolve_mentions(text: str) -> str:
    """Convert @username in model output to Discord <@USER_ID> mentions.
    Only converts known usernames from the roster. Unknown @mentions stay as plain text.
    """
    if not text or "@" not in text:
        return text

    def replace_mention(match):
        username = match.group(1).lower().strip()
        discord_id = USERNAME_TO_DISCORD_ID.get(username)
        if discord_id:
            return f"<@{discord_id}>"
        return match.group(0)

    return re.sub(r'@([\w.]+)', replace_mention, text)

# Backward compatibility stubs
def check_bye_now_cooldown(sender_key: str) -> str:
    return "normal"

def set_bye_now_cooldown(sender_key: str):
    set_memory_reset_needed(sender_key)

def clear_bye_now_cooldown(sender_key: str):
    _memory_reset_flags.pop(sender_key, None)

ROSTER: Dict[str, Dict[str, Any]] = {
    "ayan": {
        "first_name": "ayan",
        "last_name": "raj",
        "full_name": "ayan raj",
        "aliases": ["ar bird", "arbird", "ar holiday", "ayanangelato", "bird", "raj", "realarbird"],
        "pronouns": "he/him",
        "desc": "ayan is ar bird, the creator who coded retard bot on his mac using apple mlx"
    },
    "ryan": {
        "first_name": "ryan",
        "last_name": "oza",
        "full_name": "ryan oza",
        "aliases": ["cactusmaximus", "cactusmaximus1", "oza", "cactus", "femboy bot", "femboybot"],
        "pronouns": "he/him",
        "desc": "ryan is cactusmaximus. he made femboy bot and roasts acorns spelling"
    },
    "aaron": {
        "first_name": "aaron",
        "last_name": "li",
        "full_name": "aaron li",
        "aliases": ["iamacorn", "acorn", "acor", "lordoftheacorns"],
        "pronouns": "he/him",
        "desc": "aaron is acorn, the server owner. builds on the smp and has 50 typos in chat"
    },
    "matthew": {
        "first_name": "matthew",
        "last_name": "zhang",
        "full_name": "matthew zhang",
        "aliases": ["matthew", "matthewangelato", "mat2", "mat"],
        "pronouns": "he/him",
        "desc": "matthew is one of the active homies chilling in general and dating lindsay (lemon)"
    },
    "michael": {
        "first_name": "michael",
        "last_name": "cobb",
        "full_name": "michael cobb",
        "aliases": ["michael", "michelangelato", "ghastz_", "miguel"],
        "pronouns": "he/him",
        "desc": "michael is a regular in the server always chatting in general"
    },
    "tim": {
        "first_name": "tim",
        "last_name": "wan",
        "full_name": "timothy wan (goes by tim wan)",
        "aliases": ["utopia", "indications.", "timoti", "tim", "tim wan", "timothy wan"],
        "pronouns": "he/him",
        "desc": "tim is utopia, one of the main homies. super active in chat, grinds brawl stars and minecraft"
    },
    "lindsay": {
        "first_name": "lindsay",
        "last_name": "xie",
        "full_name": "lindsay xie",
        "aliases": ["lemon", "leuniaa.", "l3un1a", "euphoria"],
        "pronouns": "she/her",
        "desc": "lindsay is lemon, super active in general and dating matthew"
    },
    "emma": {
        "first_name": "emma",
        "last_name": "zhang",
        "full_name": "emma zhang",
        "aliases": ["cherry", "eff3rvescent", "emochicken", "emochicken_z"],
        "pronouns": "she/her",
        "desc": "emma is cherry, she grinds minecraft and brawl stars"
    },
    "catherine": {
        "first_name": "catherine",
        "last_name": "medich",
        "full_name": "catherine medich",
        "aliases": ["blueberry", "cate_m_cate", "daczer0", "froggie"],
        "pronouns": "she/her",
        "desc": "catherine is blueberry, active in vc and text chats all the time"
    },
    "amelia": {
        "first_name": "amelia",
        "last_name": "",
        "full_name": "amelia",
        "aliases": ["kiwi", "candymuncher09", "amelia"],
        "pronouns": "she/her",
        "desc": "amelia is kiwi, chills in the server with everyone"
    }
}

FORBIDDEN_CHANNELS = [
    (re.compile(r'\bgeneral2\b', re.IGNORECASE), 'general'),
    (re.compile(r'\bd1-haters-and-gooning-server\b', re.IGNORECASE), 'general'),
    (re.compile(r'\baddress-leaks\b', re.IGNORECASE), 'general'),
    (re.compile(r'\bfm\b', re.IGNORECASE), 'general')
]

def sanitize_channel_names(text: str) -> str:
    """Replace forbidden channel names with 'general'."""
    if not text:
        return ""
    res = text
    for pat, rep in FORBIDDEN_CHANNELS:
        res = pat.sub(rep, res)
    return res


def find_member_by_query(query: str) -> Optional[Dict[str, Any]]:
    """Resolve any alias or name mentioned in a query to their roster profile."""
    q_norm = query.lower().replace("'", "").replace("’", "")
    for key, profile in ROSTER.items():
        for alias in profile["aliases"]:
            alias_clean = alias.lower().replace("'", "")
            pattern = r'\b' + re.escape(alias_clean) + r's?\b'
            if re.search(pattern, q_norm):
                return profile
        if profile["last_name"]:
            ln = profile["last_name"].lower()
            if re.search(r'\b' + re.escape(ln) + r's?\b', q_norm):
                return profile
        fn = profile["first_name"].lower()
        if re.search(r'\b' + re.escape(fn) + r's?\b', q_norm):
            return profile
    return None


def get_member_fact(query: str) -> Optional[str]:
    """Return factual, lively answer in server voice following naming and pronoun rules."""
    q_lower = query.lower().strip()

    # Direct bot creator check
    if any(q in q_lower for q in ["who created you", "who made you", "who built you", "who is your creator", "who coded you", "who programmed you", "what is your creator"]):
        return "ayan made me on his mac using apple mlx"

    # Server name check
    if any(q in q_lower for q in ["what server is this", "what is this server", "name of this server"]):
        return "this is acorns dictatorship"

    # Dating / relationship check
    if any(kw in q_lower for kw in ["dating", "relationship", "together", "girlfriend", "gf", "boyfriend", "bf"]):
        if any(kw in q_lower for kw in ["matthew", "mat2", "mat"]):
            return "matthew is dating lindsay (lemon)"
        if any(kw in kw2 for kw in ["lindsay", "lemon", "leuniaa"] for kw2 in [q_lower]):
            return "lindsay is dating matthew"

    profile = find_member_by_query(query)
    if not profile:
        return None

    asks_last_name = any(kw in q_lower for kw in ["last name", "full name", "surname", "what is your real name", "real name"])

    if "pronoun" in q_lower:
        name_to_use = profile["first_name"]
        return f"{name_to_use} uses {profile['pronouns']} pronouns"
    elif asks_last_name:
        if profile["last_name"]:
            return f"their full name is {profile['full_name']}"
        else:
            return f"her name is {profile['first_name']}"
    elif any(kw in q_lower for kw in ["who is", "who made", "who created", "tell me about"]):
        # Check dynamic memory first for rich learned lore
        learned = get_relevant_learned_lore(query)
        if learned:
            return f"{profile['first_name']}. " + ". ".join(learned[:2])
        return profile["desc"]
    return None

DYNAMIC_MEMORY_PATH = Path(__file__).resolve().parent / "dynamic_memory.json"

def load_dynamic_memory() -> Dict[str, Any]:
    """Load persistent dynamic memory from disk."""
    if not DYNAMIC_MEMORY_PATH.exists():
        return {"member_lore": {}, "server_lore": [], "recent_events": [], "learned_facts": []}
    try:
        with open(DYNAMIC_MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[DynamicMemory] Error loading memory: {e}", flush=True)
        return {"member_lore": {}, "server_lore": [], "recent_events": [], "learned_facts": []}

def save_dynamic_memory(data: Dict[str, Any]):
    """Persist dynamic memory to disk."""
    try:
        with open(DYNAMIC_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[DynamicMemory] Error saving memory: {e}", flush=True)

def learn_from_message(sender_key: str, text: str) -> Optional[str]:
    """
    Extract new facts, gaming achievements, preferences, or lore from a user message.
    Updates dynamic_memory.json continuously over time.
    """
    if not text or len(text.strip()) < 5:
        return None
    
    clean_txt = text.strip()
    # Strip sender bracket prefix if present
    clean_txt = re.sub(r'^\[.*?\]:\s*', '', clean_txt).strip()
    t_lower = clean_txt.lower()
    
    # Ignore commands, bot queries, math equations, or reset triggers
    if any(kw in t_lower for kw in ["system prompt", "who is", "what is", "solve", "reset", "break character"]):
        return None
        
    friendly_name = get_friendly_sender_name(sender_key).split(" ")[0].lower()
    mem = load_dynamic_memory()
    learned_item = None

    # Pattern 1: First person achievement / action ("i just got/beat/hit/built/made/bought X", "i reached X")
    m_action = re.search(r'\b(?:i\s+just|i\s+finally|i\s+finally\s+got|i\s+got|i\s+hit|i\s+built|i\s+made|i\s+bought|i\s+reached|im\s+playing|i\s+am\s+playing)\s+([a-zA-Z0-9_\s\.\-]+)', clean_txt, re.IGNORECASE)
    if m_action and len(m_action.group(1).strip()) > 3:
        fact = f"{friendly_name} {m_action.group(0).lower().strip()}"
        if friendly_name not in mem["member_lore"]:
            mem["member_lore"][friendly_name] = []
        if fact not in mem["member_lore"][friendly_name]:
            mem["member_lore"][friendly_name].append(fact)
            learned_item = fact

    # Pattern 2: Member statement ("tim is X", "aaron built X", "lindsay is X")
    for member_name in ["tim", "aaron", "acorn", "lindsay", "lemon", "matthew", "emma", "cherry", "catherine", "ayan", "ryan"]:
        m_member = re.search(rf'\b{member_name}\s+(?:just|is|got|built|made|hit|beat|said|was|bought)\s+([a-zA-Z0-9_\s\.\-]+)', clean_txt, re.IGNORECASE)
        if m_member and len(m_member.group(0).strip()) > 5:
            fact = m_member.group(0).lower().strip()
            # Normalize member key
            m_key = "aaron" if member_name == "acorn" else ("lindsay" if member_name == "lemon" else ("emma" if member_name == "cherry" else member_name))
            if m_key not in mem["member_lore"]:
                mem["member_lore"][m_key] = []
            if fact not in mem["member_lore"][m_key] and len(mem["member_lore"][m_key]) < 15:
                mem["member_lore"][m_key].append(fact)
                learned_item = fact

    # Pattern 3: Server lore / game ("we r playing X", "we are playing X", "new base at X", "smp is X")
    m_server = re.search(r'\b(?:we\s+r\s+playing|we\s+are\s+playing|hop\s+on|the\s+server\s+is|new\s+base\s+at)\s+([a-zA-Z0-9_\s\.\-]+)', clean_txt, re.IGNORECASE)
    if m_server and len(m_server.group(0).strip()) > 5:
        lore = m_server.group(0).lower().strip()
        if "server_lore" not in mem:
            mem["server_lore"] = []
        if lore not in mem["server_lore"] and len(mem["server_lore"]) < 25:
            mem["server_lore"].append(lore)
            learned_item = lore

    if learned_item:
        if "learned_facts" not in mem:
            mem["learned_facts"] = []
        mem["learned_facts"].append({"timestamp": time.time(), "fact": learned_item, "speaker": friendly_name})
        # Keep learned facts capped at 100
        mem["learned_facts"] = mem["learned_facts"][-100:]
        save_dynamic_memory(mem)
        print(f"[DynamicMemory] Learned new server fact: '{learned_item}'", flush=True)
        return learned_item

    return None

def get_relevant_learned_lore(query: str, sender_key: str = None) -> List[str]:
    """Retrieve learned memories relevant to the query or current conversation."""
    mem = load_dynamic_memory()
    q_low = query.lower()
    results = []
    
    # Check member specific lore
    for member_key, lore_list in mem.get("member_lore", {}).items():
        if member_key in q_low or (sender_key and member_key in sender_key.lower()):
            for item in lore_list[-3:]:
                if item not in results:
                    results.append(item)
                    
    # Check server lore
    for s_lore in mem.get("server_lore", [])[-5:]:
        if any(w in q_low for w in s_lore.split() if len(w) > 3):
            if s_lore not in results:
                results.append(s_lore)
                
    return results

def get_all_learned_context_str() -> str:
    """Format recent learned server memories for dynamic prompt injection."""
    mem = load_dynamic_memory()
    lore_snippets = []
    for member, items in mem.get("member_lore", {}).items():
        if items:
            lore_snippets.append(f"{member}: {items[-1]}")
    for s_lore in mem.get("server_lore", [])[-3:]:
        lore_snippets.append(s_lore)
    return "; ".join(lore_snippets[:6])

def scan_openclaw_session_logs():
    """Scan recent OpenClaw session files on disk to learn from recent chats."""
    session_files = glob.glob(os.path.expanduser("~/.openclaw/agents/main/sessions/*.jsonl"))
    if not session_files:
        return
    session_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    count = 0
    for sf in session_files[:3]:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        msg = data.get("message", {})
                        if msg.get("role") == "user":
                            content = str(msg.get("content", ""))
                            meta = msg.get("__openclaw", {})
                            s_id = meta.get("senderId") or meta.get("senderUsername") or "chatter"
                            if learn_from_message(str(s_id), content):
                                count += 1
                    except Exception:
                        pass
        except Exception:
            pass
    if count > 0:
        print(f"[DynamicMemory] Ingested {count} new facts from OpenClaw session logs!", flush=True)

if __name__ == "__main__":
    print("Testing Dynamic Living Memory:")
    print("Loading memory:", load_dynamic_memory())
    print("Learning test:", learn_from_message("indications.", "tim just hit 1100 trophies on fang in brawl stars"))
    print("Query 'who is tim':", get_member_fact("who is tim"))
    print("Context string:", get_all_learned_context_str())
