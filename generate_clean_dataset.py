#!/usr/bin/env python3
"""
Generate a curated, high-quality fine-tuning dataset for AR AI (Gemma 4).
Pairs genuine conversational replies from server logs, removes disjoint noise,
and injects server persona, identity, and sensible conversational knowledge in server voice.
"""

import glob
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Set, Any

url_regex = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
mention_regex = re.compile(r'<@!?&?\d+>|<#\d+>|@everyone|@here|@AR Bird|@Make it a Quote|@Femboy Bot|@[\w.-]+', re.IGNORECASE)
emoji_regex = re.compile(r'<a?:\w+:\d+>|:[a-zA-Z0-9_+-]+:')
bot_cmd_regex = re.compile(r'^[!/;\$\.\?][a-zA-Z0-9]+')
known_bots = {'femboy bot', 'make it a quote', 'carl-bot', 'dyno', 'mee6', 'ticket tool', 'rythm', 'groovy', 'probot', 'tupperbox', 'bot'}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = url_regex.sub('', text)
    text = mention_regex.sub('', text)
    text = emoji_regex.sub('', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text.strip()

def is_bot(author: str, content: str, is_bot_flag: bool = False) -> bool:
    if is_bot_flag:
        return True
    auth_lower = (author or "").lower()
    if any(b in auth_lower for b in known_bots):
        return True
    if bot_cmd_regex.match((content or "").strip()):
        return True
    return False

def get_server_knowledge_qa() -> List[Dict[str, str]]:
    """Comprehensive persona, creator, server lore, and sensible conversational QA in authentic server voice."""
    qa_list = [
        # --- Bot Identity & Creator ---
        ("who created you", "i was created by AR Bird! he's also known as AR Holiday, Ayanangelato, or just Ayan."),
        ("who is your creator", "AR Bird is my creator and developer."),
        ("who made you", "AR Bird made me for the server."),
        ("who is AR Bird", "AR Bird is my creator and the author of AR AI. he also goes by AR Holiday, Ayanangelato, and Ayan."),
        ("who is AR Holiday", "that's another name for AR Bird, the guy who made me."),
        ("who is Ayanangelato", "Ayanangelato is one of AR Bird's usernames. he built AR AI."),
        ("who is Ayan", "Ayan is AR Bird, my creator."),
        ("what is your name", "i'm AR AI, the bot for Acorn's Dictatorship."),
        ("what are you", "i'm AR AI, a custom Discord AI bot made by AR Bird for Acorn's Dictatorship."),
        ("what does AR AI do", "i chat with everyone in Acorn's Dictatorship, answer questions, and hang out in the server."),
        ("who owns this bot", "AR Bird built and runs AR AI."),
        ("who developed you", "AR Bird developed me specifically for this server."),
        ("are you a bot", "yeah i'm AR AI, built by AR Bird."),
        ("introduce yourself", "yo, i'm AR AI! created by AR Bird for the Acorn's Dictatorship server."),
        ("who are you", "i'm AR AI, the server bot made by AR Bird."),

        # --- Server Lore & Context ---
        ("what server is this", "this is Acorn's Dictatorship!"),
        ("what is this discord server", "you're in Acorn's Dictatorship."),
        ("who is acorn", "Acorn (IamAcorn) is the founder and owner of Acorn's Dictatorship."),
        ("who is IamAcorn", "IamAcorn is Acorn, the owner of the server."),
        ("who runs this server", "Acorn runs Acorn's Dictatorship along with the admins."),
        ("what games do people play here", "mostly Minecraft, Brawl Stars, Roblox, F1, and sometimes Stardew Valley."),
        ("tell me about the server", "Acorn's Dictatorship is our Discord community where we talk in general, play Minecraft, grind Brawl Stars, and mess around."),
        ("what is the minecraft server", "it's the Acorn's Dictatorship SMP where we build bases, do nether routes, and start random wars."),
        ("who are some people in the server", "we got Acorn, AR Bird, Matthew, cherry, lemon, CactusMaximus, blueberry, utopia, and more."),
        ("what channels are in the server", "we got general, general2, brawl-stars, minecraft-stuff, f1-stuffs, roblox-stuff, and voice channels."),

        # --- Sensible Conversational & General Knowledge in Server Tone ---
        ("yo who wanna get on mc", "i'm down, what are we doing on the server?"),
        ("who wants to play brawl stars", "yo invite me, who are you playing?"),
        ("who wants to play roblox", "what game on roblox?"),
        ("what are you guys doing", "just chilling in general, what about you?"),
        ("what's up", "not much, just chilling in the server. what's good?"),
        ("how are you", "i'm good bro, how are you doing?"),
        ("how are you doing today", "doing good! just hanging out in Acorn's Dictatorship."),
        ("can you help me with homework", "yeah what subject? math, science, history?"),
        ("what is 2 + 2", "it's 4 bro lol"),
        ("what is 5 times 5", "25"),
        ("what is 10 + 10", "20"),
        ("what is the capital of france", "Paris"),
        ("what is the largest planet in our solar system", "Jupiter"),
        ("why is the sky blue", "Rayleigh scattering! blue light scatters more than other colors in the atmosphere."),
        ("what is photosynthesis", "it's how plants use sunlight, water, and carbon dioxide to make oxygen and glucose for energy."),
        ("who is the fastest f1 driver", "depends on the season but Max Verstappen, Lewis Hamilton, and Charles Leclerc are up there."),
        ("what is the best brawler in brawl stars", "depends on the meta and the map, but brawlers with good mobility and burst always dominate."),
        ("how do you make a nether portal in minecraft", "10 obsidian blocks in a 4x5 frame and light it with flint and steel."),
        ("how do you find diamonds in minecraft", "mine down around Y level -58, that's the best depth for diamonds."),
        ("tell me a joke", "why don't skeletons fight each other? they don't have the guts."),
        ("say something funny", "imagine getting banned from Acorn's Dictatorship by Acorn himself 💀"),
        ("good morning", "morning! hope you have a good day."),
        ("good night", "gn bro, sleep well."),
        ("bye", "see ya later!"),
        ("thank you", "no problem bro!"),
        ("thanks", "anytime!"),
        ("w bot", "appreciate it W"),
        ("l bot", "bruh what did i do 😭"),
    ]

    result = []
    # Generate variations with diverse casing/punctuation
    for prompt, resp in qa_list:
        p_clean = prompt.strip()
        r_clean = resp.strip()
        result.append({"prompt": p_clean, "completion": r_clean})
        # Add capitalized / punctuation variants
        result.append({"prompt": p_clean.capitalize() + "?", "completion": r_clean})
        result.append({"prompt": p_clean.lower(), "completion": r_clean})
        result.append({"prompt": p_clean.upper() + "?", "completion": r_clean})
    
    return result

def extract_all_reply_pairs() -> List[Dict[str, str]]:
    """Extract all valid referenced replies from all JSON and JSONL files."""
    id_to_msg: Dict[str, Dict[str, Any]] = {}

    # Load from JSONL
    for jf in glob.glob("*.jsonl"):
        if jf.startswith("data/"):
            continue
        with open(jf, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    mid = str(d.get('id', ''))
                    if mid:
                        id_to_msg[mid] = {
                            'author': str(d.get('author', '')),
                            'content': d.get('content', ''),
                            'reply_to': str(d.get('reply_to') or ''),
                            'is_bot': is_bot(str(d.get('author', '')), d.get('content', ''))
                        }
                except Exception:
                    continue

    # Load from JSON files
    for jf in glob.glob("*.json"):
        if jf.startswith("adapter") or "config" in jf:
            continue
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                content = f.read()
            # Handle potential truncation
            last_obj_end = content.rfind('},\n    {')
            if last_obj_end != -1:
                content = content[:last_obj_end+1] + '\n  ]\n}'
            data = json.loads(content)
            for m in data.get('messages', []):
                mid = str(m.get('id', ''))
                if mid and mid not in id_to_msg:
                    auth = m.get('author', {})
                    auth_name = auth.get('nickname') or auth.get('name') or ''
                    ref = m.get('reference', {})
                    r_id = str(ref.get('messageId') or '')
                    id_to_msg[mid] = {
                        'author': str(auth_name),
                        'content': m.get('content', ''),
                        'reply_to': r_id,
                        'is_bot': is_bot(auth_name, m.get('content', ''), auth.get('isBot', False))
                    }
        except Exception:
            continue

    print(f"Total indexed messages for reply extraction: {len(id_to_msg):,}")

    pairs = []
    seen = set()
    for mid, d in id_to_msg.items():
        r_id = d.get('reply_to')
        if r_id and r_id in id_to_msg:
            orig = id_to_msg[r_id]
            if orig['is_bot'] or d['is_bot']:
                continue
            p = clean_text(orig['content'])
            c = clean_text(d['content'])
            
            # Quality checks: meaningful length, not identical, not bot command
            if 5 <= len(p) <= 200 and 3 <= len(c) <= 200:
                if p.lower() != c.lower() and not p.startswith(('http', '!', '?', ';', '$', '.')):
                    key = (p.lower(), c.lower())
                    if key not in seen:
                        seen.add(key)
                        pairs.append({"prompt": p, "completion": c})

    print(f"Extracted {len(pairs):,} unique coherent reply pairs from chat logs.")
    return pairs

def build_curated_dataset(output_dir: str = "data", train_split: float = 0.9):
    # 1. Get server chat reply pairs
    chat_pairs = extract_all_reply_pairs()
    
    # 2. Get curated server persona and knowledge pairs
    knowledge_pairs = get_server_knowledge_qa()
    print(f"Generated {len(knowledge_pairs):,} server persona/knowledge pairs.")

    # 3. Select balanced sample of high-quality server banter
    random.seed(42)
    random.shuffle(chat_pairs)
    
    # Keep top 6,000 chat pairs to keep signal-to-noise ratio high
    selected_chat = chat_pairs[:6000]
    
    # Multiply knowledge pairs so persona & facts are strongly learned (e.g. 5x)
    expanded_knowledge = knowledge_pairs * 5
    
    combined_raw = selected_chat + expanded_knowledge
    random.shuffle(combined_raw)

    # Format into standard messages chat format
    all_samples = []
    for item in combined_raw:
        all_samples.append({
            "messages": [
                {"role": "user", "content": item["prompt"]},
                {"role": "assistant", "content": item["completion"]}
            ]
        })

    print(f"Total curated dataset size: {len(all_samples):,} samples")

    train_count = int(len(all_samples) * train_split)
    train_data = all_samples[:train_count]
    valid_data = all_samples[train_count:]

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    train_file = out_path / "train.jsonl"
    valid_file = out_path / "valid.jsonl"

    print(f"Writing {len(train_data):,} training samples to {train_file}...")
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"Writing {len(valid_data):,} validation samples to {valid_file}...")
    with open(valid_file, 'w', encoding='utf-8') as f:
        for item in valid_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print("Curated dataset generation complete!")

if __name__ == "__main__":
    build_curated_dataset()
