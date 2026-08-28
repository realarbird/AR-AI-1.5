#!/usr/bin/env python3
"""
Process Discord chat logs for MLX LoRA fine-tuning on Google Gemma 4 E4B-it.
Parses all JSON and JSONL Discord chat logs in the workspace, cleans noise
(URLs, mentions, emojis), filters out bots and short messages, pairs consecutive messages,
adds identity knowledge for AR AI, and creates 90/10 train/valid splits.
"""

import os
import glob
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Set, Any

def build_cleaners():
    url_regex = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
    mention_regex = re.compile(
        r'<@!?&?\d+>|<#\d+>|@everyone|@here|@AR Bird|@Make it a Quote|@Femboy Bot|@[\w.-]+',
        re.IGNORECASE
    )
    emoji_regex = re.compile(r'<a?:\w+:\d+>|:[a-zA-Z0-9_+-]+:')
    bot_cmd_regex = re.compile(r'^[!/;\$\.\?][a-zA-Z0-9]+')
    
    known_bots = {
        'femboy bot', 'make it a quote', 'carl-bot', 'dyno', 'mee6',
        'ticket tool', 'rythm', 'groovy', 'probot', 'tupperbox', 'bot'
    }

    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = url_regex.sub('', text)
        text = mention_regex.sub('', text)
        text = emoji_regex.sub('', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n', text)
        return text.strip()

    def is_bot_message(author: str, content: str, is_bot_flag: bool = False) -> bool:
        if is_bot_flag:
            return True
        auth_lower = (author or "").lower()
        if any(bot in auth_lower for bot in known_bots):
            return True
        if bot_cmd_regex.match((content or "").strip()):
            return True
        return False

    return clean_text, is_bot_message

def parse_json_export(file_path: str) -> List[Dict[str, Any]]:
    """Parse messages from a Discord Chat Exporter JSON file, with truncation recovery."""
    messages = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            channel_name = data.get('channel', {}).get('name', Path(file_path).stem)
            for m in data.get('messages', []):
                m['_channel_name'] = channel_name
                messages.append(m)
    except Exception:
        # Attempt repair for incomplete / truncated exports
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            last_obj_end = content.rfind('},\n    {')
            if last_obj_end != -1:
                valid_content = content[:last_obj_end+1] + '\n  ]\n}'
                data = json.loads(valid_content)
                channel_name = data.get('channel', {}).get('name', Path(file_path).stem)
                for m in data.get('messages', []):
                    m['_channel_name'] = channel_name
                    messages.append(m)
        except Exception as err:
            print(f"  Warning: Failed to parse {file_path}: {err}")
    return messages

def parse_jsonl_export(file_path: str) -> List[Dict[str, Any]]:
    """Parse messages from a JSONL export."""
    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                m = json.loads(line_str)
                m['_channel_name'] = m.get('channel', 'default')
                messages.append(m)
            except json.JSONDecodeError:
                continue
    return messages

def get_identity_pairs():
    """Generate identity and server context pairs for AR AI."""
    pairs = [
        # Name & identity
        ("What is your name?", "I am AR AI, the chatbot for Acorn's Dictatorship."),
        ("Who are you?", "I am AR AI, an AI assistant created by AR Bird for Acorn's Dictatorship."),
        ("What does AR AI stand for?", "AR AI is the Discord bot created by AR Bird for the Acorn's Dictatorship server."),
        ("Introduce yourself.", "Hey! I'm AR AI, created by AR Bird for Acorn's Dictatorship."),
        
        # Creator / Author
        ("Who created you?", "I was created by AR Bird (also known as AR Holiday, Ayanangelato, or Ayan)."),
        ("Who made you?", "AR Bird made me! He is also known as AR Holiday, Ayanangelato, and Ayan."),
        ("Who is your creator?", "My creator is AR Bird."),
        ("Who is AR Bird?", "AR Bird is my creator and the developer behind AR AI."),
        ("Who is AR Holiday?", "AR Holiday is another name for AR Bird, my creator."),
        ("Who is Ayanangelato?", "Ayanangelato is another alias for AR Bird, the creator of AR AI."),
        ("Who is Ayan?", "Ayan is AR Bird, the creator and author of AR AI."),
        ("Who owns AR AI?", "AR AI was built and is maintained by AR Bird."),
        
        # Server
        ("What server is this?", "This is Acorn's Dictatorship."),
        ("What is this Discord server called?", "This Discord server is called Acorn's Dictatorship."),
        ("Where are we?", "We are in the Acorn's Dictatorship server."),
        ("Tell me about this server.", "This is Acorn's Dictatorship, a Discord community."),
        ("Who runs Acorn's Dictatorship?", "Acorn's Dictatorship is the Discord server founded and run by Acorn and the community."),
    ]
    # Multiply identity pairs so the model strongly absorbs core knowledge during fine-tuning
    return pairs * 30

def process_all_data(output_dir: str = "data", train_split: float = 0.9):
    print("Collecting all Discord chat log files in directory...")
    clean_text, is_bot_message = build_cleaners()
    
    # 1. Collect from all JSON files
    json_files = [f for f in sorted(glob.glob("*.json")) if not f.startswith("adapter")]
    # 2. Collect from all JSONL files
    jsonl_files = [f for f in sorted(glob.glob("*.jsonl")) if not f.startswith("data/")]

    all_raw_messages = []
    seen_ids: Set[str] = set()

    # Ingest JSONL files first
    for jf in jsonl_files:
        print(f"Reading JSONL file: {jf}")
        msgs = parse_jsonl_export(jf)
        for m in msgs:
            msg_id = str(m.get('id', ''))
            if msg_id and msg_id in seen_ids:
                continue
            if msg_id:
                seen_ids.add(msg_id)
            
            author_val = m.get('author', '')
            if isinstance(author_val, dict):
                author_name = author_val.get('nickname') or author_val.get('name') or ''
                is_bot = author_val.get('isBot', False)
            else:
                author_name = str(author_val)
                is_bot = False

            all_raw_messages.append({
                'id': msg_id,
                'author': author_name,
                'is_bot': is_bot,
                'content': m.get('content', ''),
                'channel': m.get('_channel_name', 'default'),
                'timestamp': m.get('timestamp', '')
            })

    # Ingest JSON files
    for jf in json_files:
        print(f"Reading JSON file: {jf}")
        msgs = parse_json_export(jf)
        new_count = 0
        for m in msgs:
            msg_id = str(m.get('id', ''))
            if msg_id and msg_id in seen_ids:
                continue
            if msg_id:
                seen_ids.add(msg_id)
            new_count += 1
            
            author_val = m.get('author', {})
            if isinstance(author_val, dict):
                author_name = author_val.get('nickname') or author_val.get('name') or ''
                is_bot = author_val.get('isBot', False)
            else:
                author_name = str(author_val)
                is_bot = False

            all_raw_messages.append({
                'id': msg_id,
                'author': author_name,
                'is_bot': is_bot,
                'content': m.get('content', ''),
                'channel': m.get('_channel_name', 'default'),
                'timestamp': m.get('timestamp', '')
            })
        print(f"  Added {new_count:,} new unique messages from {jf}")

    print(f"\nTotal unique messages collected across all files: {len(all_raw_messages):,}")

    # Group messages by channel and sort by timestamp
    by_channel: Dict[str, List[Dict[str, Any]]] = {}
    for m in all_raw_messages:
        ch = m['channel']
        by_channel.setdefault(ch, []).append(m)

    pairs = []
    skipped_bots = 0
    skipped_short = 0

    for ch, channel_msgs in by_channel.items():
        # Sort chronologically by timestamp if present
        channel_msgs.sort(key=lambda x: x.get('timestamp') or '')
        
        prev_cleaned = None
        for m in channel_msgs:
            author = m['author']
            content = m['content']
            is_bot = m['is_bot']
            
            if is_bot_message(author, content, is_bot):
                skipped_bots += 1
                continue
                
            cleaned = clean_text(content)
            if len(cleaned) < 3:
                skipped_short += 1
                continue
                
            if prev_cleaned is not None:
                pairs.append({'prompt': prev_cleaned, 'completion': cleaned})
            prev_cleaned = cleaned

    print(f"Skipped bot messages: {skipped_bots:,}")
    print(f"Skipped short/empty messages: {skipped_short:,}")
    print(f"Total consecutive chat pairs generated: {len(pairs):,}")

    # Add identity and context pairs
    identity_pairs = get_identity_pairs()
    print(f"Adding {len(identity_pairs)} identity and context QA pairs.")
    for prompt, completion in identity_pairs:
        pairs.append({'prompt': prompt, 'completion': completion})

    # Shuffle dataset
    random.seed(42)
    random.shuffle(pairs)

    total_pairs = len(pairs)
    train_count = int(total_pairs * train_split)
    train_pairs = pairs[:train_count]
    valid_pairs = pairs[train_count:]

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    train_file = out_path / "train.jsonl"
    valid_file = out_path / "valid.jsonl"

    print(f"Writing {len(train_pairs):,} training pairs to {train_file}...")
    with open(train_file, 'w', encoding='utf-8') as f:
        for p in train_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')

    print(f"Writing {len(valid_pairs):,} validation pairs to {valid_file}...")
    with open(valid_file, 'w', encoding='utf-8') as f:
        for p in valid_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')

    print("Data processing complete!")
    print(f"  Train set: {train_file} ({len(train_pairs):,} samples)")
    print(f"  Validation set: {valid_file} ({len(valid_pairs):,} samples)")

if __name__ == "__main__":
    process_all_data()
