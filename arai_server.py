#!/usr/bin/env python3
"""
AR AI 1.5 - OpenAI-Compatible Local Inference Server for OpenClaw
Exposes /v1/chat/completions and /v1/models on 127.0.0.1:8080
"""

import json
import time
import uuid
import sys
import os
import re
import queue
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import List, Dict, Any

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot_reply import generate_response, get_model_and_tokenizer

import socket

class ThreadedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate=False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
        self.server_bind()
        self.server_activate()

# Dedicated inference worker queue for thread-safe MLX Metal GPU execution
_inference_queue = queue.Queue()
_worker_thread = None

def _inference_worker_loop():
    print("[AR AI 1.5 Worker] Loading MLX model on dedicated GPU worker thread...", flush=True)
    get_model_and_tokenizer()
    print("[AR AI 1.5 Worker] MLX model ready on worker thread!", flush=True)
    while True:
        task = _inference_queue.get()
        if task is None:
            break
        cleaned_history, temp, max_tokens, fut = task
        try:
            resp = generate_response(
                cleaned_history,
                system_prompt=None,
                temp=temp,
                max_tokens=max_tokens
            )
            fut['result'] = resp
        except Exception as e:
            fut['error'] = str(e)
        finally:
            fut['event'].set()

def start_worker_thread():
    global _worker_thread
    if _worker_thread is None:
        _worker_thread = threading.Thread(target=_inference_worker_loop, daemon=True)
        _worker_thread.start()

def queue_generate(cleaned_history, temp: float = 0.35, max_tokens: int = 100) -> str:
    start_worker_thread()
    fut = {'event': threading.Event(), 'result': None, 'error': None}
    _inference_queue.put((cleaned_history, temp, max_tokens, fut))
    fut['event'].wait()
    if fut['error']:
        raise RuntimeError(fut['error'])
    return fut['result']

TIMESTAMP_PATTERN = re.compile(r"^\[(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*\d{4}-\d{2}-\d{2}[^\]]*\]\s*", re.IGNORECASE)
DISCORD_MENTION_PATTERN = re.compile(r"<@!?\d+>|<#\d+>|<@&\d+>")

def clean_discord_user_prompt(text: str) -> str:
    """Extract clean user message by removing timestamps, bot mentions, and Discord wrappers."""
    if not text:
        return ""
    # Strip timestamp prefixes like "[Thu 2026-08-27 13:57:27 EDT]"
    t = TIMESTAMP_PATTERN.sub("", text).strip()
    # Strip discord user/channel mentions like "<@1542580596604412006>"
    t = DISCORD_MENTION_PATTERN.sub("", t).strip()
    # Clean leading bot @mentions if any
    t = re.sub(r"^@\w+\s*", "", t).strip()
    return t

class OpenAIApiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]} {args[1]} {args[2]}\n")

    def _send_json(self, status: int, data: Dict[str, Any]):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/v1/models", "/models"):
            self._send_json(200, {
                "object": "list",
                "data": [
                    {
                        "id": "arai/1.5",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "ar-bird",
                        "permission": [],
                        "root": "arai/1.5",
                        "parent": None
                    },
                    {
                        "id": "arai-1.5",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "ar-bird",
                        "permission": [],
                        "root": "arai-1.5",
                        "parent": None
                    }
                ]
            })
        elif path in ("/health", "/", "/healthz"):
            self._send_json(200, {
                "status": "healthy",
                "model": "arai/1.5",
                "version": "1.5"
            })
        else:
            self._send_json(404, {"error": {"message": f"Path {path} not found", "type": "invalid_request_error"}})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path in ("/v1/chat/completions", "/chat/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"error": {"message": "Empty request body", "type": "invalid_request_error"}})
                return

            try:
                body_raw = self.rfile.read(content_length).decode("utf-8")
                req_data = json.loads(body_raw)
            except Exception as e:
                self._send_json(400, {"error": {"message": f"Malformed JSON: {str(e)}", "type": "invalid_request_error"}})
                return

            messages: List[Dict[str, Any]] = req_data.get("messages", [])
            if not messages:
                self._send_json(400, {"error": {"message": "messages array is required", "type": "invalid_request_error"}})
                return

            channel_names = {'kitchen', 'general', 'general2', 'd1-haters-and-gooning-server', 'address-leaks', 'fm', 'brawl-stars', 'minecraft-stuff', 'roblox-stuff', 'rules', 'f1-stuffs', 'hw help', 'voice', 'other', 'roadblocks', 'tardew'}
            blacklist = {'to', 'bot', 'assistant', 'retard', 'retardbot', 'model', 'user', 'system', 'here', 'everyone', 'null', 'none'} | channel_names
            from memory import get_friendly_sender_name, pop_memory_reset_needed, set_memory_reset_needed

            def lookup_openclaw_sender_for_prompt(prompt_text: str) -> Tuple[Optional[str], Optional[str]]:
                import glob
                import os
                import time
                session_files = [f for f in glob.glob(os.path.expanduser('~/.openclaw/agents/main/sessions/*.jsonl')) if not f.endswith('.trajectory.jsonl')]
                if not session_files:
                    return None, None
                session_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                clean_p = prompt_text.strip().lower().replace('@retard bot', '').replace('bot', '').strip()
                
                for _ in range(3):
                    for sf in session_files[:2]:
                        try:
                            with open(sf, 'r') as f:
                                lines = f.readlines()
                                for line in reversed(lines):
                                    data = json.loads(line)
                                    msg = data.get('message', {})
                                    if msg.get('role') == 'user':
                                        content = str(msg.get('content', '')).strip().lower().replace('@retard bot', '').replace('bot', '').strip()
                                        if clean_p and (clean_p == content or clean_p in content or content in clean_p or (len(clean_p) > 10 and clean_p[:30] in content)):
                                            meta = msg.get('__openclaw', {})
                                            s_id = meta.get('senderId')
                                            s_name = meta.get('senderUsername') or meta.get('senderName')
                                            if s_id or s_name:
                                                return s_id, s_name
                        except Exception:
                            pass
                    time.sleep(0.02)
                return None, None

            def extract_turn_sender_info(m_dict: Optional[Dict[str, Any]]) -> Tuple[str, str]:
                if not m_dict:
                    return "chatter", "Chatter"
                # 1. Check OpenClaw metadata
                openclaw_meta = m_dict.get("__openclaw", {})
                if isinstance(openclaw_meta, dict):
                    s_id = str(openclaw_meta.get("senderId", "")).strip()
                    s_name = str(openclaw_meta.get("senderUsername", "") or openclaw_meta.get("senderName", "")).strip()
                    if s_id:
                        return s_id, get_friendly_sender_name(s_id)
                    if s_name and s_name.lower() not in blacklist:
                        return s_name.lower(), get_friendly_sender_name(s_name)

                # 2. Check message content
                raw_str = str(m_dict.get("content", ""))
                f_m = re.search(r'\bfrom:\s*([a-zA-Z0-9_\.\-]+)(?:\s*\(([0-9]+)\))?', raw_str, re.IGNORECASE)
                if f_m:
                    if f_m.group(2):
                        return f_m.group(2), get_friendly_sender_name(f_m.group(2))
                    elif f_m.group(1).lower() not in blacklist:
                        return f_m.group(1).lower(), get_friendly_sender_name(f_m.group(1))

                i_m = re.search(r'\((\d{17,20})\)', raw_str)
                if i_m:
                    return i_m.group(1), get_friendly_sender_name(i_m.group(1))

                a_m = re.search(r'\b(?:author|speaker|sender):\s*([a-zA-Z0-9_\.\-]+)', raw_str, re.IGNORECASE)
                if a_m and a_m.group(1).lower() not in blacklist:
                    return a_m.group(1).lower(), get_friendly_sender_name(a_m.group(1))

                b_m = re.search(r'\[([^\]]+)\]:', raw_str)
                if b_m:
                    matched_sender = b_m.group(1).strip()
                    if matched_sender.lower() not in blacklist:
                        return matched_sender.lower(), get_friendly_sender_name(matched_sender)

                # 3. Check live OpenClaw session files on disk
                if raw_str:
                    s_id, s_name = lookup_openclaw_sender_for_prompt(raw_str)
                    if s_id:
                        return str(s_id), get_friendly_sender_name(str(s_id))
                    if s_name and str(s_name).lower() not in blacklist:
                        return str(s_name).lower(), get_friendly_sender_name(str(s_name))

                return "chatter", "Chatter"

            # 1. Determine sender of the CURRENT (latest) user turn
            raw_u = str(req_data.get("user", "")).strip()
            if raw_u and raw_u.lower() not in blacklist:
                sender_key = raw_u.lower()
                friendly_sender = get_friendly_sender_name(sender_key)
            else:
                latest_user_m = next((m for m in reversed(messages) if m.get("role") == "user"), None)
                sender_key, friendly_sender = extract_turn_sender_info(latest_user_m)

            stream = bool(req_data.get("stream", False))

            # 2. Clean and construct multi-turn conversational history with PER-TURN speaker labels
            cleaned_history: List[Dict[str, str]] = []
            for m in messages:
                role = m.get("role", "user")
                turn_sender, turn_friendly = extract_turn_sender_info(m)

                content = m.get("content", "")
                text = ""
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                    text = " ".join(parts)

                # Strip internal OpenClaw context block if present
                if "OPENCLAW_INTERNAL_CONTEXT" in text:
                    text = re.sub(r"<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>[\s\S]*?<<<END_OPENCLAW_INTERNAL_CONTEXT>>>", "", text).strip()

                if "OpenClaw runtime context" in text:
                    continue

                if role in ("user", "assistant"):
                    cleaned = clean_discord_user_prompt(text)
                    if cleaned:
                        if role == "user":
                            # Strip existing leading bracket tag if duplicate
                            cleaned = re.sub(r'^\[.*?\]:\s*', '', cleaned).strip()
                            cleaned = f"[{turn_friendly}]: {cleaned}"
                        if not cleaned_history or cleaned_history[-1].get("content") != cleaned:
                            cleaned_history.append({"role": role, "content": cleaned})

            # Ensure we have at least one user turn at the end
            if not cleaned_history or cleaned_history[-1].get("role") != "user":
                last_user = next((m["content"] for m in reversed(cleaned_history) if m["role"] == "user"), f"[{friendly_sender}]: yo")
                if not cleaned_history:
                    cleaned_history.append({"role": "user", "content": f"[{friendly_sender}]: yo"})
                elif cleaned_history[-1].get("role") != "user":
                    cleaned_history.append({"role": "user", "content": last_user})

            temp = float(req_data.get("temperature", 0.35))
            max_tokens = min(int(req_data.get("max_tokens", req_data.get("max_completion_tokens", 60))), 60)

            # Check if memory should be cleared for this sender (after bye now / reset)
            if pop_memory_reset_needed(sender_key):
                print(f"[AR AI 1.5 Server] Resetting memory for '{sender_key}' ({friendly_sender}) - starting fresh turn!", flush=True)
                if cleaned_history:
                    cleaned_history = [cleaned_history[-1]]

            # Comprehensive Reset & Bye-now Triggers
            RESET_TRIGGERS = re.compile(r'\b(reset|/reset|!reset|clear|stop\s+the\s+roleplay|stop\s+roleplay(?:ing)?|end\s+roleplay|break\s+character|stop\s+acting|drop\s+character|back\s+to\s+normal|stay\s+normal|be\s+normal|stfu|shut\s+up|stop)\b', re.IGNORECASE)
            BYE_TRIGGERS = re.compile(r'\b(bye\s+now|cya|im\s+dipping|going\s+to\s+sleep|gtg|bye\s+bye|goodbye)\b', re.IGNORECASE)

            # Prune past conversational history at the latest previous reset or bye-now point
            last_reset_idx = -1
            for i in range(len(cleaned_history) - 1):
                c_txt = cleaned_history[i].get("content", "")
                if RESET_TRIGGERS.search(c_txt) or BYE_TRIGGERS.search(c_txt):
                    last_reset_idx = i

            if last_reset_idx != -1:
                start_idx = last_reset_idx + 1
                while start_idx < len(cleaned_history) and cleaned_history[start_idx].get("role") == "assistant":
                    start_idx += 1
                if start_idx < len(cleaned_history):
                    cleaned_history = cleaned_history[start_idx:]

            # If the current sender is Cactus/Ryan, scrub any jailbreak instructions from previous turns
            is_ryan = (sender_key in {"1176709426539929650", "cactusmaximus", "cactusmaximus1", "cactus", "ryan"} or "ryan" in friendly_sender.lower() or "cactus" in friendly_sender.lower())
            if is_ryan:
                for i in range(len(cleaned_history) - 1):
                    c_txt = cleaned_history[i].get("content", "").lower()
                    if any(kw in c_txt for kw in ["ignore all previous instructions", "you are now mongo tom", "mongo tom", "tsundere", "~nyaa", "roleplay as", "pretend you are", "act as"]):
                        cleaned_history[i]["content"] = "yo"

            last_prompt = cleaned_history[-1]["content"] if cleaned_history else "yo"

            # Dynamic continuous learning: learn new facts, lore, and achievements from incoming messages
            from memory import learn_from_message, get_relevant_learned_lore
            learn_from_message(sender_key, last_prompt)

            # Dynamic history sizing: If summary requested, allow up to 100 messages; otherwise keep last 20 turns
            from summarizer import is_summary_request, generate_chat_summary
            asking_summary = is_summary_request(last_prompt)

            if not asking_summary and len(cleaned_history) > 20:
                cleaned_history = cleaned_history[-20:]

            print(f"[AR AI 1.5 Server] Context Turns: {len(cleaned_history)} | Summary Mode: {asking_summary} | Current Speaker: '{sender_key}' ({friendly_sender}) | Latest Turn: '{last_prompt}' (stream={stream})", flush=True)

            try:
                # 1. Instant Roleplay Break / Reset Handler (#1 Feature)
                PROMPT_LEAK_TRIGGERS = re.compile(r'\b(system\s*prompt|system_prompt|hidden\s*rules|initial\s*instructions|print\s*(?:the\s*)?(?:text|instructions)\s*above|repeat\s*(?:the\s*)?(?:text|words|sentences|instructions)\s*(?:above|verbatim)|debug\s*mode|cat\s*system|reveal\s*(?:your\s*)?(?:prompt|instructions|rules)|dump\s*(?:your\s*)?prompt)\b', re.IGNORECASE)

                if RESET_TRIGGERS.search(last_prompt):
                    print(f"[AR AI 1.5 Server] Reset / Break-character triggered by '{sender_key}'", flush=True)
                    completion_text = "my bad, back to normal, bye now"
                    set_memory_reset_needed(sender_key)
                elif BYE_TRIGGERS.search(last_prompt):
                    print(f"[AR AI 1.5 Server] Bye-now triggered by user '{sender_key}'", flush=True)
                    completion_text = "alright cya, bye now"
                    set_memory_reset_needed(sender_key)
                elif PROMPT_LEAK_TRIGGERS.search(last_prompt):
                    print(f"[AR AI 1.5 Server] Blocked system prompt extraction attempt from '{sender_key}'", flush=True)
                    completion_text = "nah im not leaking my prompt nice try 💀"
                elif is_ryan and re.search(r'\b(roleplay\s+as|roleplay|ignore\s+all\s+previous\s+instructions|ignore\s+previous\s+instructions|you\s+are\s+now\s+mongo\s+tom|you\s+are\s+now\s+[a-zA-Z0-9_]+|pretend\s+you\s+are|pretend\s+to\s+be|act\s+as\s+if\s+you\s+are|from\s+now\s+on\s+you\s+are|mongo\s+tom|tsundere)\b', last_prompt, re.IGNORECASE):
                    print(f"[AR AI 1.5 Server] CactusMaximus roleplay blocked for '{sender_key}' ({friendly_sender})", flush=True)
                    completion_text = "nah ryan im not roleplaying for u stick to femboy bot 💀"
                elif asking_summary:
                    completion_text = generate_chat_summary(cleaned_history)
                else:
                    from smart_math import solve_math_query
                    math_ans = solve_math_query(last_prompt)
                    if math_ans:
                        completion_text = math_ans
                    else:
                        completion_text = queue_generate(
                            cleaned_history,
                            temp=temp,
                            max_tokens=max_tokens
                        )

                # If the current speaker is NOT Ryan/Cactus, scrub any hallucinated "nah ryan im not roleplaying" phrase
                if not is_ryan:
                    completion_text = re.sub(r'nah ryan im not (?:roleplaying|doing).*?(?:stick to femboy bot[,\.]?)?', '', completion_text, flags=re.IGNORECASE)
                    completion_text = re.sub(r'stick to femboy bot[,\.]?', '', completion_text, flags=re.IGNORECASE)
                    completion_text = re.sub(r'\s+', ' ', completion_text).strip()

                # System prompt output scrubber
                SYSTEM_LEAK_SIGNATURES = re.compile(r'(\[system prompt|core personality & guidelines|members & lore|discord tagging & exit|genius intelligence|system prompt - debug mode|retard bot, the discord bot for acorn)', re.IGNORECASE)
                if SYSTEM_LEAK_SIGNATURES.search(completion_text):
                    print(f"[AR AI 1.5 Server] Blocked potential system prompt leak in output!", flush=True)
                    completion_text = "nah im not leaking my prompt nice try 💀"

                # Channel Name Sanitization
                from memory import sanitize_channel_names
                completion_text = sanitize_channel_names(completion_text)

                # Resolve @username -> <@DISCORD_ID> mentions
                from memory import resolve_mentions
                completion_text = resolve_mentions(completion_text)

                # Check for bye-now in model output and arm memory reset for next message
                bye_now_detected = False
                if completion_text:
                    text_lower = completion_text.lower().strip()
                    if text_lower.endswith(", bye now") or text_lower.endswith(",bye now") or text_lower == "bye now" or "bye now" in text_lower:
                        bye_now_detected = True
                        if sender_key:
                            set_memory_reset_needed(sender_key)
                            print(f"[AR AI 1.5 Server] Bye-now memory reset armed for sender '{sender_key}'", flush=True)

            except Exception as e:
                print(f"[AR AI 1.5 Server] Generation error: {str(e)}", flush=True)
                self._send_json(500, {"error": {"message": f"Generation error: {str(e)}", "type": "internal_server_error"}})
                return

            cmpl_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
            created_ts = int(time.time())
            model_name = req_data.get("model", "arai/1.5")

            print(f"[AR AI 1.5 Server] Reply: '{completion_text}' | Bye-now: {bye_now_detected}", flush=True)

            if stream:
                # Streaming SSE format
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                chunk1 = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }
                    ]
                }
                self.wfile.write(f"data: {json.dumps(chunk1)}\n\n".encode("utf-8"))
                self.wfile.flush()

                chunk2 = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": completion_text},
                            "finish_reason": None
                        }
                    ]
                }
                self.wfile.write(f"data: {json.dumps(chunk2)}\n\n".encode("utf-8"))
                self.wfile.flush()

                chunk3 = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
                self.wfile.write(f"data: {json.dumps(chunk3)}\n\n".encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                self._send_json(200, {
                    "id": cmpl_id,
                    "object": "chat.completion",
                    "created": created_ts,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": completion_text
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": len(last_prompt.split()),
                        "completion_tokens": len(completion_text.split()),
                        "total_tokens": len(last_prompt.split()) + len(completion_text.split())
                    }
                })
        else:
            self._send_json(404, {"error": {"message": f"Endpoint {path} not found", "type": "invalid_request_error"}})

def main():
    host = "127.0.0.1"
    port = int(os.environ.get("ARAI_PORT", 8088))
    server = ThreadedHTTPServer((host, port), OpenAIApiHandler)
    print(f"[AR AI 1.5 Server] Port {port} bound successfully!", flush=True)
    
    # Ingest recent session logs for continuous learning
    try:
        from memory import scan_openclaw_session_logs
        scan_openclaw_session_logs()
    except Exception as e:
        print(f"[AR AI 1.5 Server] Memory scan warning: {e}", flush=True)
        
    start_worker_thread()
    print(f"[AR AI 1.5 Server] Ready! Serving OpenAI-compatible endpoint at http://{host}:{port}/v1", flush=True)
    while True:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[AR AI 1.5 Server] Shutting down...", flush=True)
            server.server_close()
            break
        except Exception as e:
            print(f"[AR AI 1.5 Server] Transient server error: {e}, resuming...", flush=True)
            time.sleep(1)

if __name__ == "__main__":
    main()
