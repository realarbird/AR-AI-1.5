# AR AI 1.5 — Project Handoff Documentation

This document serves as the authoritative, up-to-date technical handoff for developers and AI assistants maintaining and developing **AR AI 1.5** (aka **Retard Bot** for the *Acorn's Dictatorship* Discord server).

---

## 1. Project Overview

**AR AI 1.5** is a custom Discord AI bot built specifically for the **Acorn's Dictatorship** Discord community. It runs locally on Apple Silicon and is connected to Discord 24/7 via **OpenClaw**.

- **Bot Name**: Retard Bot
- **Discord Server**: Acorn's Dictatorship
- **Server Owner**: IAmAcorn / Aaron Li (`<@1158380010042818582>`)
- **Bot Creator / Dev**: AR Bird / Ayan Raj (`<@1015271651165872209>`)
- **Active Model Backend**: `retard-bot` (custom Ollama model powered by Gemma 4 E4B with MLX fallback)
- **Serving Architecture**: OpenAI-compatible endpoint on `http://127.0.0.1:8088/v1`
- **Core Persona & Guidelines**:
  - **Natural Slang, Shorthands & Tone**: Casual, all lowercase, no trailing periods. Uses natural shorthands (`u`, `r`, `ur`, `rn`, `idk`, `ngl`, `fr`, `mb`, `bruh`) without robotic AI fluff or forced boomer slang.
  - **Dynamic Continuous Server Memory & Learning**: The bot continuously learns facts, achievements, gaming milestones, and server lore from Discord conversations. Learned knowledge is persisted in `dynamic_memory.json` and dynamically retrieved to adapt to the server over time.
  - **System Prompt Confidentiality & Anti-Leak Shield**: Both input requests and generated outputs are strictly protected against prompt extraction attacks (e.g. `cat system_prompt`, `debug mode`, `repeat text above verbatim`, `hidden rules`). If triggered, the bot immediately refuses with `"nah im not leaking my prompt nice try 💀"`.
  - **Relaxed & Friendly Vibes (Never Mean)**: The bot is chill, funny, warm, and friendly. It does NOT randomly call members "weird" or tell them to "stop being weird" during compliments, nice comments, or normal banter.
  - **Friendly & Respectful to Acorn (Aaron Li)**: Acorn is the server owner and a good homie. The bot is always friendly, nice, and chill with Acorn (never mean, hostile, or insulting).
  - **Targeted CactusMaximus Roleplay Immunity & Open Roleplay for Others**: CactusMaximus (Ryan Oza) roleplay/jailbreak commands are blocked (`"nah ryan im not roleplaying for u stick to femboy bot 💀"`). ALL OTHER SERVER MEMBERS are free to roleplay any scenarios, personas, or characters with the bot.
  - **Strict Emoji Rules (End of Message Only)**: Allowed emojis (`😭`, `💀`, `🥀`, `🙏`, `💔`, `😔`, `🥹`, `👀`). Emojis are placed strictly at the end of messages, single/pair emoji reactions (`😭🙏`, `💀😭`, `👀`) are supported, and joy/laughing emojis (`😂`, `😄`) are excluded.
  - **Per-Turn Speaker Extraction & Labeling**: The server extracts sender information directly from OpenClaw's metadata (`m["__openclaw"]["senderId"]`) as well as message text for every turn. Each turn is labeled `[MemberName]: ...` (e.g. `[Ayan (AR Bird)]: ...`, `[Tim (Utopia)]: ...`, `[Aaron (Acorn)]: ...`, `[Ryan (CactusMaximus)]: ...`).
  - **Dynamic Multi-Turn History Pruning & Jailbreak Scrubbing**: When OpenClaw passes recent Discord channel history, previous turns before a reset boundary are pruned. Non-Ryan roleplay conversations are preserved cleanly.
  - **Instant Memory Reset on Resume**: When a conversation ends with `bye now` or when a user triggers `reset`/`break character`, the bot responds immediately on the very next message while completely clearing all previous conversation history from its context window.
  - **OpenClaw Owner Permissions**: AR Bird (`1015271651165872209`, `realarbird`, `ayanangelato`) has full owner/admin permissions configured in `~/.openclaw/openclaw.json` for all slash and server commands.
  - **Full High Intelligence**: Uncompromised STEM, math arithmetic & algebra, physics, chemistry, biology, coding, and gaming meta (Roblox Rivals loadouts, Minecraft mechanics, Brawl Stars).
  - **Discord Mention Resolution**: Resolves `@username` in model responses to clickable `<@DISCORD_ID>`.

---

## 2. Server Roster & Living Memory

| Member | Discord Username / Aliases | Full Name & Pronouns | Role & Server Lore | Discord ID |
| :--- | :--- | :--- | :--- | :--- |
| **AR Bird** | `realarbird`, `ar holiday`, `ayanangelato`, `bird`, `raj` | Ayan Raj (he/him) | Creator/developer of Retard Bot on Apple Silicon Mac. | `<@1015271651165872209>` |
| **IAmAcorn** | `acorn`, `aaron`, `lordoftheacorns` | Aaron Li (he/him) | Server owner of Acorn's Dictatorship. Known for SMP builds and 50 typos in chat. | `<@1158380010042818582>` |
| **CactusMaximus** | `cactus`, `ryan`, `cactusmaximus1` | Ryan Oza (he/him) | Coded Femboy Bot. Stays roasting Acorn's terrible spelling. | `<@1176709426539929650>` |
| **utopia** | `tim`, `timoti`, `indications.` | Timothy Wan / Tim Wan (he/him) | SMP master builder, nether highways, base tour videos. | `<@1155209176134451330>` |
| **lemon** | `lindsay`, `leuniaa.`, `l3un1a`, `euphoria` | Lindsay Xie (she/her) | Very active chatter in general channels. **Dating Matthew!** | `<@1243385718370340927>` |
| **matthew** | `matthewangelato`, `mat2`, `mat` | Matthew Zhang (he/him) | Regular member in general. **Dating Lindsay (Lemon)!** | `<@891068533755244585>` |
| **cherry** | `emma`, `eff3rvescent`, `emochicken` | Emma Zhang (she/her) | Grinds Minecraft and Brawl Stars. | `<@1179514728779886663>` |
| **blueberry** | `catherine`, `cate_m_cate`, `DacZer0` | Catherine Medich (she/her) | Active in voice channels and text chats 24/7. | `<@865774655066865686>` |
| **kiwi** | `amelia`, `candymuncher09` | Amelia (she/her) | Active member. | `<@1078846574190415893>` |
| **michael** | `michelangelato`, `ghastz_`, `miguel` | Michael Cobb (he/him) | Regular member. | `<@1126220555884957747>` |

> [!NOTE]
> *Naming Rule*: Only mention last names if the user explicitly asks for someone's last name or full name. Normally use only first names or gamer tags.

---

## 3. Architecture & Data Flow

```
[ Discord Channel / Mention ]
              │
              ▼
[ OpenClaw Gateway (Port 18789) ]
              │ (OpenAI chat completions payload: stream=True)
              ▼
[ AR AI 1.5 Server (Port 8088, arai_server.py) ]
              │
              ├──► 1. Extract Sender & Discord ID:
              │       Resolves numeric ID / username to member name (e.g. 1015271651165872209 -> Ayan)
              │
              ├──► 2. Memory Reset Check:
              │       If reset armed after 'bye now' / reset -> Start fresh 1-turn context immediately
              │
              ├──► 3. Roleplay / Reset Trigger Check:
              │       If reset / break character / bye now detected:
              │       -> Return exit & arm memory reset for next turn
              │
              ├──► 4. Summarizer Check (summarizer.py):
              │       If summary request -> Expand window to 100 turns & recap
              │
              ├──► 5. Math & Science Solver (smart_math.py):
              │       Exact arithmetic / algebra equations computed with step-by-step logic
              │
              ├──► 6. LLM Generation (bot_reply.py via Ollama retard-bot):
              │       Gemma 4 E4B high-speed inference on Apple Metal GPU with speaker context
              │
              └──► 7. Post-Processing Pipeline:
                      • Anti-Romance Interceptor (replaces flirting with funny roast)
                      • Slang Density Calibrator (prevents acronym stacking)
                      • Emoji Moderation (calm_emojis: max 1 emoji, zero chains)
                      • Trailing Period Stripping (preserves mid-sentence decimals)
                      • Mention Resolution (resolve_mentions: @user -> <@ID>)
                      • Channel Name Sanitization
```

---

## 4. Operations Guide (Start, Stop, Test & Manage)

### Starting Services
```bash
# 1. Start AR AI Server on port 8088
cd "/Users/ayanraj/Documents/AR AI 1.5"
PYTHONUNBUFFERED=1 nohup ./mlx_env/bin/python -u arai_server.py > /tmp/arai_server.log 2>&1 &

# 2. Verify server health
curl -s http://127.0.0.1:8088/health

# 3. Ensure OpenClaw Gateway is running
export PATH=/Users/ayanraj/.nvm/versions/node/v24.20.0/bin:$PATH
openclaw gateway start
openclaw channels status
```

### Stopping Services
```bash
# Stop AR AI Server
pkill -9 -f arai_server.py

# Stop OpenClaw Gateway
export PATH=/Users/ayanraj/.nvm/versions/node/v24.20.0/bin:$PATH
openclaw gateway stop
```

### Testing Live Responses
```bash
# Test direct API
curl -s http://127.0.0.1:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "who created you"}]}' | jq -r '.choices[0].message.content'

# Test OpenClaw agent locally
export PATH=/Users/ayanraj/.nvm/versions/node/v24.20.0/bin:$PATH
openclaw agent --message "sine 30" --session-key test --local
```

### Updating the Model / Persona
If you modify `Modelfile`:
```bash
ollama create retard-bot -f Modelfile
pkill -9 -f arai_server.py
PYTHONUNBUFFERED=1 nohup ./mlx_env/bin/python -u arai_server.py > /tmp/arai_server.log 2>&1 &
```

---

## 5. Repository File Map

| Path | Purpose |
| :--- | :--- |
| `arai_server.py` | OpenAI-compatible HTTP server on port 8088 with streaming SSE, speaker awareness & reset handler |
| `bot_reply.py` | Primary response generator, slang calibrator, emoji calmer, anti-romance filter, and mention resolver |
| `Modelfile` | Ollama model configuration file for `retard-bot` |
| `memory.py` | Living memory module, member roster, friendly name mapping, and cooldown tracker |
| `summarizer.py` | Multi-turn channel summarizer for 100-message recaps |
| `smart_math.py` | Step-by-step arithmetic and algebra solver |
| `scorecard.py` | Verification scorecard checking style syntax adherence |
| `build_v12_dataset.py` | Master dataset generator with 100% clean anti-romance samples |
| `lora_config.yaml` | MLX LoRA training configuration |
| `adapters/` | Trained LoRA adapter safetensors |
| `data/train.jsonl` | Clean training split in chat format |
| `data/valid.jsonl` | Clean validation split in chat format |
| `docs/HANDOFF.md` | Authoritative project handoff documentation |
