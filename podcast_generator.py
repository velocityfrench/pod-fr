"""
VELOCITY FRENCH PODCAST GENERATOR
15-min bilingual French/English podcast at A2 level
2 hosts: Sophie & Thomas
"""
import os, sys, json, asyncio, subprocess, random, requests, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL") or "openai"

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"

HOST1_VOICE = "fr-FR-DeniseNeural"
HOST2_VOICE = "fr-FR-HenriNeural"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

TOPICS = [
    "Voyager dans un nouveau pays - Traveling to a new country",
    "Cuisine traditionnelle française - Traditional French food",
    "Routine quotidienne - Daily routine",
    "Fêtes et célébrations - Holidays and celebrations",
    "La météo et les saisons - Weather and seasons",
    "Famille et amis - Family and friends",
    "Musique et films - Music and movies",
    "Sport et exercice - Sports and exercise",
    "La ville idéale - The ideal city",
    "Apprendre les langues - Learning languages",
    "Le week-end - The weekend",
    "Achats et vêtements - Shopping and clothes",
    "Transports en commun - Public transport",
    "Au restaurant - At the restaurant",
    "Santé et bien-être - Health and wellness",
]

YELLOW = (247, 202, 0)
DARK_BG = (11, 14, 27)
WHITE = (255, 255, 255)
LIGHT_GRAY = (170, 180, 205)
DARK_LINE = (50, 55, 75)

def load_font(size, bold=False, italic=False):
    fonts_to_try = []
    if italic and bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuiz.ttf", "C:/Windows/Fonts/arialbi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
            str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"),
        ])
    elif italic:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/ariali.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
            str(FONTS_DIR / "DejaVuSans-Oblique.ttf"),
        ])
    elif bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Bold-slnt=0.ttf", "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            str(FONTS_DIR / "DejaVuSans-Bold.ttf"),
        ])
    else:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Regular-slnt=0.ttf", "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            str(FONTS_DIR / "DejaVuSans.ttf"),
        ])

    for fp in fonts_to_try:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def clean_text(text):
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\b(euh+|ehm+|hum+|mm+|um+|uh+|ah+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def auto_highlight_french(text):
    if '**' in text:
        return text
    stopwords = {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'd\'', 'à', 'en', 'dans', 'avec', 'pour', 'sur', 'par', 'et', 'ou', 'que', 'qui', 'est', 'sont', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'ce', 'cette'}
    words = text.split()
    candidates = []
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^\wÀÂÇÉÈÊËÎÏÔÙÛÜàâçéèêëîïôùûüÿ]', '', w, flags=re.UNICODE)
        if clean_w.lower() not in stopwords and len(clean_w) >= 3:
            candidates.append((len(clean_w), idx, w, clean_w))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_idx = candidates[0][1]
        raw_w = words[best_idx]
        clean_w = candidates[0][3]
        highlighted = raw_w.replace(clean_w, f"**{clean_w}**")
        words[best_idx] = highlighted
        return " ".join(words)
    return text

def draw_microphone_icon(draw, center_x, center_y, radius=24):
    draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                 outline=YELLOW, width=3)
    w, h = 10, 18
    draw.rounded_rectangle([center_x - w//2, center_y - 12, center_x + w//2, center_y - 12 + h],
                           radius=4, fill=YELLOW)
    draw.arc([center_x - 10, center_y - 4, center_x + 10, center_y + 12],
             start=0, end=180, fill=YELLOW, width=3)
    draw.line([(center_x, center_y + 12), (center_x, center_y + 17)], fill=YELLOW, width=3)
    draw.line([(center_x - 7, center_y + 17), (center_x + 7, center_y + 17)], fill=YELLOW, width=3)

def draw_person_icon(draw, center_x, center_y):
    draw.ellipse([center_x - 6, center_y - 12, center_x + 6, center_y], fill=YELLOW)
    draw.chord([center_x - 12, center_y + 2, center_x + 12, center_y + 20],
               start=180, end=360, fill=YELLOW)

def draw_french_flag(img, draw, center_x, center_y, radius=22):
    flag_img = Image.new('RGBA', (radius*2, radius*2), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flag_img)
    # French flag: Blue left (33%), White middle (33%), Red right (33%)
    w = radius * 2
    fdraw.rectangle([(0, 0), (int(w * 0.33), w)], fill=(0, 38, 84, 255))
    fdraw.rectangle([(int(w * 0.33), 0), (int(w * 0.66), w)], fill=(255, 255, 255, 255))
    fdraw.rectangle([(int(w * 0.66), 0), (w, w)], fill=(237, 41, 57, 255))
    
    mask = Image.new('L', (radius*2, radius*2), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, radius*2, radius*2], fill=255)
    img.paste(flag_img, (center_x - radius, center_y - radius), mask)

def draw_headphones_icon(draw, center_x, center_y):
    draw.arc([center_x - 14, center_y - 14, center_x + 14, center_y + 6],
             start=180, end=360, fill=YELLOW, width=3)
    draw.rounded_rectangle([center_x - 16, center_y - 3, center_x - 10, center_y + 11], radius=2, fill=YELLOW)
    draw.rounded_rectangle([center_x + 10, center_y - 3, center_x + 16, center_y + 11], radius=2, fill=YELLOW)

def draw_rich_text_centered(draw, text, center_y, font, max_w=1550, line_height=90):
    text = auto_highlight_french(text)
    pattern = r'(\*\*.*?\*\*)'
    raw_parts = re.split(pattern, text)
    tokens = []
    for part in raw_parts:
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], True))
        elif part:
            tokens.append((part, False))
            
    words_with_status = []
    for text_chunk, is_yellow in tokens:
        words = text_chunk.split(' ')
        for i, w in enumerate(words):
            if w:
                words_with_status.append((w, is_yellow))
            if i < len(words) - 1:
                words_with_status.append((' ', False))

    lines = []
    current_line = []
    current_line_width = 0

    for item in words_with_status:
        word, is_yellow = item
        w_bbox = draw.textbbox((0, 0), word, font=font)
        w_width = w_bbox[2] - w_bbox[0]

        if current_line_width + w_width <= max_w or not current_line:
            current_line.append((word, is_yellow, w_width))
            current_line_width += w_width
        else:
            if current_line and current_line[-1][0] == ' ':
                current_line_width -= current_line[-1][2]
                current_line.pop()
            lines.append((current_line, current_line_width))
            if word == ' ':
                current_line = []
                current_line_width = 0
            else:
                current_line = [(word, is_yellow, w_width)]
                current_line_width = w_width

    if current_line:
        if current_line[-1][0] == ' ':
            current_line_width -= current_line[-1][2]
            current_line.pop()
        lines.append((current_line, current_line_width))

    total_height = len(lines) * line_height
    start_y = center_y - total_height // 2

    for line_idx, (line_words, line_w) in enumerate(lines):
        start_x = (VIDEO_WIDTH - line_w) // 2
        curr_x = start_x
        curr_y = start_y + line_idx * line_height

        for word, is_yellow, w_w in line_words:
            color = YELLOW if is_yellow else WHITE
            draw.text((curr_x, curr_y), word, fill=color, font=font)
            curr_x += w_w

def draw_english_translation(draw, text, center_y, font, max_w=1350, line_height=52):
    words = text.split()
    lines = []
    current_line = []
    
    for w in words:
        test_line = ' '.join(current_line + [w])
        bb = draw.textbbox((0, 0), test_line, font=font)
        if bb[2] - bb[0] <= max_w:
            current_line.append(w)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [w]
    if current_line:
        lines.append(' '.join(current_line))
        
    total_h = len(lines) * line_height
    start_y = center_y - total_h // 2
    
    for idx, line in enumerate(lines):
        draw.text((VIDEO_WIDTH // 2, start_y + idx * line_height + line_height // 2),
                  line, fill=LIGHT_GRAY, font=font, anchor="mm")

def create_frame(turn, output_path, frame_num=0):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(img)

    glow = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([(-200, VIDEO_HEIGHT-600), (600, VIDEO_HEIGHT+200)], fill=(30, 20, 60, 40))
    gdraw.ellipse([(VIDEO_WIDTH-500, -200), (VIDEO_WIDTH+300, 600)], fill=(30, 20, 60, 40))
    img.paste(glow, (0, 0), glow)

    f_title_white = load_font(36, bold=True)
    f_title_sub = load_font(18, bold=False)
    f_title_sub_muted = load_font(15, bold=False)
    f_ep = load_font(22, bold=True)
    f_speaker = load_font(26, bold=True)
    f_hablando = load_font(24, bold=False)
    f_french = load_font(64, bold=True)
    f_english = load_font(42, bold=False, italic=True)
    f_footer = load_font(22, bold=False)

    # === TOP HEADER ===
    header_y = 68
    draw_microphone_icon(draw, center_x=70, center_y=header_y, radius=24)

    draw.text((110, header_y), "VELOCITY", fill=WHITE, font=f_title_white, anchor="lm")
    v_bbox = draw.textbbox((110, header_y), "VELOCITY", font=f_title_white, anchor="lm")
    
    draw.text((v_bbox[2] + 8, header_y), "FRENCH", fill=YELLOW, font=f_title_white, anchor="lm")
    s_bbox = draw.textbbox((v_bbox[2] + 8, header_y), "FRENCH", font=f_title_white, anchor="lm")

    draw.text((s_bbox[2] + 8, header_y), "PODCAST", fill=WHITE, font=f_title_white, anchor="lm")
    p_bbox = draw.textbbox((s_bbox[2] + 8, header_y), "PODCAST", font=f_title_white, anchor="lm")

    draw.line([(p_bbox[2] + 20, 48), (p_bbox[2] + 20, 88)], fill=DARK_LINE, width=2)

    sub_x = p_bbox[2] + 35
    draw.text((sub_x, header_y - 12), "French Podcast", fill=WHITE, font=f_title_sub, anchor="lm")
    draw.text((sub_x, header_y + 12), "Learn Through Conversations", fill=LIGHT_GRAY, font=f_title_sub_muted, anchor="lm")

    ep_num = (frame_num // 150) + 1 if isinstance(frame_num, int) else 1
    ep_str = f"EP {ep_num:02d}"
    draw.rounded_rectangle([(1640, 46), (1750, 90)], radius=8, fill=YELLOW)
    draw.text((1695, header_y), ep_str, fill=DARK_BG, font=f_ep, anchor="mm")

    draw_french_flag(img, draw, center_x=1810, center_y=header_y, radius=22)

    draw.line([(0, 130), (VIDEO_WIDTH, 130)], fill=YELLOW, width=2)

    # === SPEAKER STATUS SECTION ===
    is_host1 = turn.get("speaker") == "Host1"
    speaker_name = "SOPHIE" if is_host1 else "THOMAS"
    pill_x, pill_y = 120, 210
    pill_w, pill_h = 220, 52

    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
                           radius=26, outline=YELLOW, width=2)
    draw_person_icon(draw, center_x=pill_x + 36, center_y=pill_y + 26)
    draw.text((pill_x + 60, pill_y + 26), speaker_name, fill=YELLOW, font=f_speaker, anchor="lm")

    draw.text((pill_x + pill_w + 25, pill_y + 26), "parle", fill=LIGHT_GRAY, font=f_hablando, anchor="lm")

    # === MAIN FRENCH TEXT ===

    # === MAIN TEXT (auto-size, HARD max 3 lines) ===
    french_text = turn.get("french", turn.get("spanish", ""))
    chosen_font = None
    chosen_lh = 90
    final_lines = []
    for test_size in [64, 56, 48, 40, 34, 28, 24, 20]:
        test_font = load_font(test_size, bold=True)
        test_lh = int(test_size * 1.4)
        text_words = french_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=test_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) <= 3:
            chosen_font = test_font
            chosen_lh = test_lh
            final_lines = tmp_lines
            break
    if chosen_font is None:
        chosen_font = load_font(20, bold=True)
        chosen_lh = int(20 * 1.4)
        text_words = french_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=chosen_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) > 3:
            tmp_lines = tmp_lines[:3]
            if french_text:
                tmp_lines[-1] = tmp_lines[-1].rstrip() + "..."
        final_lines = tmp_lines
        french_text = " ".join(final_lines)
    draw_rich_text_centered(draw, french_text, center_y=440, font=chosen_font, max_w=1550, line_height=chosen_lh)

    # === CENTER DIVIDER WITH DOT ===
    div_y = 615
    draw.line([(VIDEO_WIDTH//2 - 300, div_y), (VIDEO_WIDTH//2 + 300, div_y)], fill=YELLOW, width=2)
    draw.ellipse([(VIDEO_WIDTH//2 - 8, div_y - 8), (VIDEO_WIDTH//2 + 8, div_y + 8)], fill=YELLOW)

    # === ENGLISH TRANSLATION ===
    english_text = turn.get("english", "")
    draw_english_translation(draw, english_text, center_y=715, font=f_english, max_w=1350, line_height=52)

    # === BOTTOM FOOTER ===
    draw.line([(0, 975), (VIDEO_WIDTH, 975)], fill=YELLOW, width=2)

    footer_y = 1025
    draw_headphones_icon(draw, center_x=VIDEO_WIDTH//2 - 270, center_y=footer_y)
    draw.text((VIDEO_WIDTH//2 - 240, footer_y), "Learn French Naturally", fill=WHITE, font=f_footer, anchor="lm")
    
    fn_bbox = draw.textbbox((VIDEO_WIDTH//2 - 240, footer_y), "Learn French Naturally", font=f_footer, anchor="lm")
    draw.line([(fn_bbox[2] + 20, footer_y - 12), (fn_bbox[2] + 20, footer_y + 12)], fill=DARK_LINE, width=2)
    
    draw.text((fn_bbox[2] + 40, footer_y), "velocityfrench.com", fill=WHITE, font=f_footer, anchor="lm")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=92)


def parse_turns_json(content, target_key="french"):
    """Robustly parse JSON array of turns from LLM output, handling unescaped control chars, code fences, and partial json."""
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()

    try:
        obj = json.loads(clean, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    fixed = re.sub(r'(?<!\\)\n', r'\\n', clean)
    try:
        obj = json.loads(fixed, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    recovered = []
    start = None
    depth = 0
    for ci, ch in enumerate(clean):
        if ch == '{':
            if depth == 0:
                start = ci
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = clean[start:ci + 1]
                try:
                    t = json.loads(chunk, strict=False)
                    if isinstance(t, dict):
                        recovered.append(t)
                except Exception:
                    try:
                        chunk_fixed = re.sub(r'(?<!\\)\n', r'\\n', chunk)
                        t = json.loads(chunk_fixed, strict=False)
                        if isinstance(t, dict):
                            recovered.append(t)
                    except Exception:
                        pass
                start = None
    if recovered:
        return recovered

    regex = re.compile(
        r'\{\s*"speaker"\s*:\s*"(?P<speaker>[^"]+)"\s*,\s*'
        r'(?:"(?:' + target_key + r'|text|content|spanish)"\s*:\s*"(?P<tgt>.*?)"\s*,\s*)?'
        r'(?:"english"\s*:\s*"(?P<en>.*?)"\s*)?'
        r'\}', re.DOTALL
    )
    for m in regex.finditer(clean):
        spk = m.group("speaker") or "Host1"
        tgt = m.group("tgt") or ""
        en = m.group("en") or ""
        if tgt:
            recovered.append({"speaker": spk, target_key: tgt, "english": en})

    return recovered

def _fetch_turns_batch(topic, topic_es, topic_en, start_turn, batch_size=10):
    """Fetch one small batch of turns with multi-model fallback and robust parsing."""
    current_host = "Host2" if start_turn % 2 == 0 else "Host1"
    next_host = "Host1" if current_host == "Host2" else "Host2"
    host_role = "Thomas" if current_host == "Host2" else "Sophie"

    intro_instruction = ""
    if start_turn == 0:
        intro_instruction = ("IMPORTANT: This is the FIRST batch. Keep the introduction SHORT - just 2 lines total "
                             "(one from Thomas/Host2, one from Sophie/Host1), then immediately dive into the topic. "
                             "No long welcome speeches.\n")
    elif start_turn < 4:
        intro_instruction = "Continue naturally into the topic conversation. No new introductions.\n"

    prompt = f"""You are writing a French/English learning podcast at A2 level.
Topic: {topic}

The dialogue so far is at turn {start_turn}. The current speaker is {host_role} ({current_host}).
Write the NEXT {batch_size} turns. Speakers STRICTLY alternate starting with {current_host}.

{intro_instruction}Each turn: 3-4 SHORT sentences (6-10 words each) with PERIODS for natural TTS pauses. 20-30 seconds spoken.
Simple present tense. A2 vocabulary. Natural French. NO filler sounds.
IMPORTANT: Highlight exactly 1 key A2 target vocabulary word in each turn's French text using double asterisks, for example: "Regardons vers le **futur**."
IMPORTANT: Format as a single compact JSON array without unescaped line breaks inside string values.

Return EXACTLY {batch_size} turns as a JSON array (no markdown):
[{{"speaker": "{current_host}", "french": "...", "english": "..."}},
 {{"speaker": "{next_host}", "french": "...", "english": "..."}}]"""

    candidate_models = [AI_MODEL, "openai", "mistral", "qwen"]
    models_to_try = []
    for mod in candidate_models:
        if mod and mod not in models_to_try:
            models_to_try.append(mod)

    for attempt, model_name in enumerate(models_to_try):
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You write natural A2-level French podcast scripts with VERY clear punctuation. Every sentence must have at least 2 commas for natural TTS pauses. Sophie and Thomas strictly alternate. Highlight 1 key target word per turn in double asterisks like **mot**. No filler sounds. Output single compact JSON array without unescaped newlines inside strings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code != 200:
                print(f"  Batch attempt {attempt+1} ({model_name}) returned HTTP {resp.status_code}", flush=True)
                continue
            content = resp.json()["choices"][0]["message"]["content"].strip()
            script = parse_turns_json(content, "french")
            valid = []
            for i, turn in enumerate(script):
                if not isinstance(turn, dict):
                    continue
                fr = turn.get("french") or turn.get("spanish") or turn.get("text") or turn.get("content") or ""
                en = turn.get("english") or turn.get("translation") or ""
                if not fr:
                    continue
                valid.append({
                    "speaker": current_host if i % 2 == 0 else next_host,
                    "french": clean_text(fr),
                    "english": clean_text(en) if en else "Translation unavailable"
                })
            if len(valid) >= 4:
                return valid
            else:
                print(f"  Batch attempt {attempt+1} ({model_name}) parsed only {len(valid)} turns, trying next model...", flush=True)
        except Exception as e:
            print(f"  Batch attempt {attempt+1} ({model_name}) failed: {e}", flush=True)
            import time
            time.sleep(1)
    return None


def _generate_topic():
    """Have the AI invent a brand-new random topic (unlimited variety).
    Returns '<topic - English>' or None on failure (caller falls back to TOPICS)."""
    seed = random.randint(100000, 999999)
    candidate_models = [AI_MODEL, "openai", "mistral"]
    for m in candidate_models:
        if not m:
            continue
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": m,
                "messages": [
                    {"role": "system", "content": "You invent fresh, interesting, everyday topics for a French/English A2 learning podcast. Always pick something new and varied from all areas of daily life, as a SHORT noun phrase (2-5 words), NOT a full sentence."},
                    {"role": "user", "content": f"Create EXACTLY ONE brand-new topic (uniqueness seed {seed}) for a French/English A2 podcast. Return ONLY one line in this exact format: <topic in French> - <topic in English>. The first part must be a short noun phrase in French. No numbering, no bullets, no extra text."}
                ],
                "temperature": 1.1,
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip()
                if content and " - " in content:
                    return content
        except Exception as e:
            print(f"  Topic gen ({m}) failed: {e}", flush=True)
    return None


def _fallback_script(topic_es, topic_en, target=150):
    """Generate 150 unique, educational, progressive dialogue turns in French covering diverse conversation phases."""
    phases = [
        # Phase 1: Greetings & Introduction
        [
            ("Host2", f"Bonjour à tous, je suis Thomas. Bienvenue sur Velocity French! Aujourd'hui, nous parlons de **{topic_es}**.",
                      f"Hello everyone, I'm Thomas. Welcome to Velocity French! Today we are talking about {topic_en}."),
            ("Host1", f"Bonjour Thomas, et bonjour à tous nos auditeurs! Ce sujet est vraiment **passionnant** pour apprendre le français.",
                      f"Hello Thomas, and hello to all our listeners! This topic is truly exciting for learning French."),
            ("Host2", f"Exactement, Sophie. Beaucoup de personnes rencontrent **{topic_es}** chaque jour, mais manquent de mots.",
                      f"Exactly, Sophie. Many people encounter {topic_en} every day, but lack the words."),
            ("Host1", f"C'est vrai. C'est pourquoi nous utilisons des phrases **simples** et claires, accessibles à tout le monde.",
                      f"That's true. That's why we use simple and clear sentences, accessible to everyone."),
            ("Host2", f"Parfait! Commençons par la toute première question: que représente **{topic_es}** dans ta vie quotidienne?",
                      f"Perfect! Let's start with the very first question: what does {topic_en} represent in your daily life?"),
            ("Host1", f"Pour moi, c'est une composante importante de la **journée** qui apporte de la bonne humeur.",
                      f"For me, it's an important component of the day that brings good cheer."),
            ("Host2", f"Je suis tout à fait d'accord. Y accorder du temps permet d'améliorer notre bien-être et notre **énergie**.",
                      f"I completely agree. Dedicating time to it allows improving our well-being and energy."),
            ("Host1", f"Oui, et lorsqu'on maîtrise le bon vocabulaire, il devient facile d'avoir une vraie **conversation**.",
                      f"Yes, and when you master the right vocabulary, it becomes easy to have a real conversation."),
            ("Host2", f"Écoutez bien attentivement chaque expression, et répétez les mots clés à **haute** voix.",
                      f"Listen very carefully to each expression, and repeat the key words out loud."),
            ("Host1", f"Très bien Thomas! Entrons tout de suite dans les aspects les plus pratiques de **{topic_es}**.",
                      f"Very good Thomas! Let's immediately get into the most practical aspects of {topic_en}.")
        ],
        # Phase 2: Morning habits & routines
        [
            ("Host2", f"Sophie, dans une journée classique, à quel moment penses-tu à **{topic_es}**?",
                      f"Sophie, in a typical day, at what point do you think about {topic_en}?"),
            ("Host1", f"D'habitude, j'aime y penser tôt le matin, car cela m'aide à commencer avec un esprit **calme**.",
                      f"Usually, I like thinking about it early in the morning, because it helps me start with a calm mind."),
            ("Host2", f"Pour moi aussi, le matin est un moment privilégié. J'apprécie prendre mon **temps** sans stress.",
                      f"For me too, the morning is a privileged moment. I enjoy taking my time without stress."),
            ("Host1", f"La précipitation est toujours mauvaise. Une bonne **habitude** matinale transforme toute la journée.",
                      f"Rushing is always bad. A good morning habit transforms the entire day."),
            ("Host2", f"D'autres personnes préfèrent se consacrer à **{topic_es}** en fin d'après-midi ou le soir.",
                      f"Other people prefer dedicating themselves to {topic_en} in late afternoon or the evening."),
            ("Host1", f"Tout dépend de l'emploi du temps de chacun. L'essentiel est de trouver un juste **équilibre**.",
                      f"Everything depends on each person's schedule. The essential thing is finding the right balance."),
            ("Host2", f"Tu as tout à fait raison. Savoir écouter ses propres besoins permet de vivre beaucoup **mieux**.",
                      f"You are completely right. Knowing how to listen to one's own needs allows living much better."),
            ("Host1", f"Et pour nos auditeurs, une pratique régulière développe une excellente **mémoire** des mots.",
                      f"And for our listeners, regular practice develops an excellent memory for words."),
            ("Host2", f"Exactement. Dix minutes par jour sont bien plus efficaces que deux heures uniquement le **dimanche**.",
                      f"Exactly. Ten minutes a day are much more effective than two hours only on Sunday."),
            ("Host1", f"Poursuivons en explorant comment **{topic_es}** s'exprime dans la vie en ville.",
                      f"Let's continue by exploring how {topic_en} expresses itself in city life.")
        ],
        # Phase 3: In the city & French lifestyle
        [
            ("Host2", f"Quand on se promène dans une ville française, on remarque vite la place qu'occupe **{topic_es}**.",
                      f"When walking in a French city, one quickly notices the place occupied by {topic_en}."),
            ("Host1", f"Oui, dans les cafés, les boutiques et dans la rue, les gens en discutent avec grand **plaisir**.",
                      f"Yes, in cafes, shops and on the street, people discuss it with great pleasure."),
            ("Host2", f"En France, partager ces petits moments avec des amis fait partie de l'art de **vivre**.",
                      f"In France, sharing these little moments with friends is part of the art of living."),
            ("Host1", f"La convivialité est une valeur fondamentale de notre culture. On ne se sent jamais vraiment **seul**.",
                      f"Conviviality is a fundamental value of our culture. One never feels truly alone."),
            ("Host2", f"Quels sont les mots que les Français emploient le plus souvent pour décrire **{topic_es}**?",
                      f"What words do French people use most often to describe {topic_en}?"),
            ("Host1", f"On utilise souvent des adjectifs comme 'authentique', 'agréable' ou 'indispensable' pour louer la **qualité**.",
                      f"People often use adjectives like 'authentic', 'pleasant' or 'essential' to praise quality."),
            ("Host2", f"Le mot 'qualité' est parfait. Les Français recherchent toujours le goût et l'élégance du **geste**.",
                      f"The word 'quality' is perfect. French people always seek taste and elegance of gesture."),
            ("Host1", f"Même si cela demande un peu d'attention, cette exigence récompense toujours le **choix**.",
                      f"Even if it demands a bit of attention, this standard always rewards the choice."),
            ("Host2", f"Un bon conseil pour les voyageurs en France: demandez toujours l'avis des habitants du **quartier**.",
                      f"A good tip for travelers in France: always ask the opinion of neighborhood residents."),
            ("Host1", f"Les habitants connaissent toujours les meilleures adresses pour apprécier pleinement **{topic_es}**.",
                      f"Residents always know the best addresses to fully appreciate {topic_en}.")
        ],
        # Phase 4: Advice for beginners & common hurdles
        [
            ("Host2", f"Un auditeur nous a posé une question: est-ce difficile de maîtriser les subtilités de **{topic_es}**?",
                      f"A listener asked us a question: is it hard to master the subtleties of {topic_en}?"),
            ("Host1", f"Au départ, cela peut sembler délicat, mais avec un peu de méthode, tout devient limpide et **clair**.",
                      f"At first it may seem tricky, but with a little method, everything becomes crystal clear."),
            ("Host2", f"Quelle est la principale difficulté rencontrée par les débutants avec ce type de **sujet**?",
                      f"What is the main difficulty encountered by beginners with this type of topic?"),
            ("Host1", f"La plus grande difficulté est souvent la peur d'hésiter ou de ne pas trouver le mot parfait du premier **coup**.",
                      f"The biggest difficulty is often the fear of hesitating or not finding the perfect word on the first try."),
            ("Host2", f"Faire des erreurs est totalement naturel! Chaque erreur constitue une formidable occasion d'**apprendre**.",
                      f"Making mistakes is totally natural! Every mistake constitutes a wonderful opportunity to learn."),
            ("Host1", f"Absolument. Lors d'un échange réel, l'important est de communiquer et de faire preuve de **curiosité**.",
                      f"Absolutely. During a real exchange, the important thing is to communicate and show curiosity."),
            ("Host2", f"Les Français apprécient énormément quand quelqu'un fait l'effort d'utiliser leur **langue**.",
                      f"French people greatly appreciate when someone makes the effort to use their language."),
            ("Host1", f"Vous recevrez toujours un accueil bienveillant et des encouragements pour **continuer**.",
                      f"You will always receive a benevolent welcome and encouragement to continue."),
            ("Host2", f"Alors n'hésitez jamais à parler de **{topic_es}** dès que l'occasion se présente!",
                      f"So never hesitate to talk about {topic_en} as soon as the opportunity arises!"),
            ("Host1", f"Prenez confiance en vous et réutilisez les structures que nous répétons dans cet **épisode**.",
                      f"Gain confidence in yourself and reuse the structures that we repeat in this episode.")
        ],
        # Phase 5: Regional diversity & French culture
        [
            ("Host2", f"Sophie, comment varie la perception de **{topic_es}** d'une région à l'autre en France?",
                      f"Sophie, how does the perception of {topic_en} vary from one region to another in France?"),
            ("Host1", f"Entre la Provence, la Bretagne ou Paris, les approches diffèrent, mais l'attachement reste très **fort**.",
                      f"Between Provence, Brittany or Paris, approaches differ, but attachment remains very strong."),
            ("Host2", f"Cette riche diversité territoriale fait toute la beauté du patrimoine et de la culture **française**.",
                      f"This rich territorial diversity makes up all the beauty of French heritage and culture."),
            ("Host1", f"Chaque région apporte sa petite touche personnelle, son histoire et son savoir-faire **unique**.",
                      f"Each region brings its own personal touch, its history and its unique craftsmanship."),
            ("Host2", f"Les personnes du monde entier apprécient d'ailleurs cette recherche d'authenticité et de **simplicité**.",
                      f"People around the world also appreciate this search for authenticity and simplicity."),
            ("Host1", f"Parce que ce mode de vie accorde une place centrale aux amis, aux bons repas et à la **famille**.",
                      f"Because this lifestyle gives a central place to friends, good meals and family."),
            ("Host2", f"Et **{topic_es}** s'inscrit naturellement dans cette philosophie où le bien-être prime.",
                      f"And {topic_en} fits naturally into this philosophy where well-being comes first."),
            ("Host1", f"Ce n'est pas simplement une idée théorique, mais une réelle expérience humaine de **partage**.",
                      f"It's not just a theoretical idea, but a real human experience of sharing."),
            ("Host2", f"Partager un bon moment permet de multiplier la joie et crée un inoubliable **souvenir**.",
                      f"Sharing a good moment multiplies joy and creates an unforgettable memory."),
            ("Host1", f"Tout à fait Thomas. Les moments les plus mémorables sont toujours ceux qui restent les plus **simples**.",
                      f"Completely Thomas. The most memorable moments are always those that remain the simplest.")
        ],
        # Phase 6: Practical learning tips
        [
            ("Host2", f"Partageons maintenant avec nos auditeurs trois astuces pratiques pour progresser sur **{topic_es}**.",
                      f"Let's now share with our listeners three practical tips to make progress on {topic_en}."),
            ("Host1", f"Première astuce: tenez un carnet de vocabulaire et écrivez chaque jour deux ou trois **phrases**.",
                      f"First tip: keep a vocabulary notebook and write two or three sentences each day."),
            ("Host2", f"Très bonne idée! L'écriture manuscrite aide le cerveau à mémoriser l'orthographe de façon **durable**.",
                      f"Very good idea! Handwriting helps the brain memorize spelling in a durable way."),
            ("Host1", f"Deuxième astuce: écoutez du français parlé dans vos écouteurs pendant vos trajets en **transport**.",
                      f"Second tip: listen to spoken French in your headphones during your commutes in transit."),
            ("Host2", f"Cette écoute passive habitue l'oreille au rythme naturel et aux intonations caractéristiques de la **voix**.",
                      f"This passive listening gets the ear used to the natural rhythm and characteristic intonations of the voice."),
            ("Host1", f"Et troisième astuce: n'apprenez jamais de mots isolés, apprenez toujours des phrases dans leur **contexte**.",
                      f"And third tip: never learn isolated words, always learn sentences in their context."),
            ("Host2", f"Ainsi, le moment venu, la phrase complète viendra spontanément sans blocage ni **effort**.",
                      f"Thus, when the time comes, the complete sentence will come spontaneously without blocking or effort."),
            ("Host1", f"C'est précisément l'approche immersive que nous adoptons pour ce niveau **A2**.",
                      f"That is precisely the immersive approach we adopt for this A2 level."),
            ("Host2", f"Les commentaires enthousiastes de notre communauté confirment les progrès rapides réalisés grâce à cette **méthode**.",
                      f"The enthusiastic comments from our community confirm the fast progress achieved thanks to this method."),
            ("Host1", f"Cela nous fait chaud au cœur et nous motive à produire des épisodes toujours plus **utiles**.",
                      f"That warms our heart and motivates us to produce ever more useful episodes.")
        ],
        # Phase 7: Situational roleplay
        [
            ("Host2", f"Jouons une petite mise en situation: imaginons que nous sommes dans un commerce pour choisir **{topic_es}**.",
                      f"Let's play a short roleplay: imagine we are in a store to choose {topic_en}."),
            ("Host1", f"Excellente idée! 'Bonjour monsieur, pouvez-vous m'indiquer ce que vous me **conseillez**?'",
                      f"Excellent idea! 'Hello sir, can you indicate what you advise me?'"),
            ("Host2", f"'Bonjour madame! Pour débuter, je vous oriente sans hésiter vers ce modèle classique et très **fiable**.'",
                      f"'Hello madam! To start out, I point you without hesitation toward this classic and very reliable model.'"),
            ("Host1", f"'Merci beaucoup! Et combien de temps faut-il pour bien s'y habituer et être parfaitement à l'**aise**?'",
                      f"'Thank you very much! And how much time is needed to get used to it well and be completely at ease?'"),
            ("Host2", f"'Généralement, quelques jours suffisent amplement si vous pratiquez avec régularité et **patience**.'",
                      f"'Generally, a few days are ample if you practice with regularity and patience.'"),
            ("Host1", f"'C'est parfait! Je vais suivre votre recommandation dès aujourd'hui sans plus **attendre**.'",
                      f"'That's perfect! I will follow your recommendation starting today without further delay.'"),
            ("Host2", f"Voilà un dialogue simple, poli et immédiatement réutilisable lors d'un séjour en **France**.",
                      f"There is a simple, polite dialogue immediately reusable during a stay in France."),
            ("Host1", f"Notez bien les formules de politesse comme 'pouvez-vous m'indiquer' qui ouvrent la porte au **dialogue**.",
                      f"Note well the politeness formulas like 'can you indicate to me' which open the door to dialogue."),
            ("Host2", f"La courtoisie rend chaque interaction beaucoup plus chaleureuse et agréable pour les deux **interlocuteurs**.",
                      f"Courtesy makes every interaction much warmer and more pleasant for both conversation partners."),
            ("Host1", f"Retenez ces expressions pratiques et continuons notre enrichissante **exploration**.",
                      f"Remember these practical expressions and let's continue our enriching exploration.")
        ],
        # Phase 8: Personal insights & confidence
        [
            ("Host2", f"Sophie, comment tes proches réagissent-ils quand tu leur parles d'un sujet comme **{topic_es}**?",
                      f"Sophie, how do your relatives react when you talk to them about a topic like {topic_en}?"),
            ("Host1", f"Au départ certains étaient curieux, puis ils ont rapidement compris son immense **intérêt**.",
                      f"At first some were curious, then they quickly understood its immense interest."),
            ("Host2", f"Une certaine hésitation au début est tout à fait normale face à toute nouvelle **activité**.",
                      f"Some hesitation at first is completely normal in the face of any new activity."),
            ("Host1", f"Mais dès qu'on franchit le pas, le sentiment d'accomplissement renforce considérablement la **confiance**.",
                      f"But as soon as you take the step, the sense of accomplishment considerably strengthens confidence."),
            ("Host2", f"La confiance à l'oral grandit avec chaque prise de parole, alors osez vous exprimer sans aucune **crainte**.",
                      f"Confidence when speaking grows with every spoken sentence, so dare to express yourself without any fear."),
            ("Host1", f"Même avec un bagage de quelques dizaines de mots, vous pouvez déjà raconter une belle **histoire**.",
                      f"Even with a vocabulary of a few dozen words, you can already tell a wonderful story."),
            ("Host2", f"Ce qui compte par-dessus tout, c'est l'authenticité et le désir sincère de partager votre **point** de vue.",
                      f"What counts above all is authenticity and the sincere desire to share your point of view."),
            ("Host1", f"Nos auditeurs nous prouvent chaque jour que le français est à la portée de toute personne **motivée**.",
                      f"Our listeners prove to us every day that French is within reach of any motivated person."),
            ("Host2", f"Chaque séance d'écoute représente une victoire supplémentaire sur votre chemin d'**apprentissage**.",
                      f"Each listening session represents an additional victory on your learning journey."),
            ("Host1", f"Et nous sommes ravis de vous accompagner pas à pas avec enthousiasme et **énergie**.",
                      f"And we are delighted to accompany you step by step with enthusiasm and energy.")
        ],
        # Phase 9: Vocabulary recap
        [
            ("Host2", f"Faisons ensemble un petit récapitulatif des mots essentiels que nous avons employés à propos de **{topic_es}**.",
                      f"Let's do together a quick recap of the essential words we used concerning {topic_en}."),
            ("Host1", f"Avec plaisir! Le premier mot clé est **habitude**, qui désigne une action répétée régulièrement avec profit.",
                      f"With pleasure! The first key word is 'habit', designating an action repeated regularly with benefit."),
            ("Host2", f"Le deuxième terme marquant est **qualité**, qui caractérise tout ce qui apporte une vraie valeur ajoutée.",
                      f"The second notable term is 'quality', characterizing anything bringing true added value."),
            ("Host1", f"Le troisième mot est **convivialité**, qui exprime le plaisir d'être ensemble et d'échanger en toute amitié.",
                      f"The third word is 'conviviality', expressing the pleasure of being together and exchanging in friendship."),
            ("Host2", f"Le quatrième mot est **patience**, car tout progrès solide demande un investissement régulier dans le temps.",
                      f"The fourth word is 'patience', because any solid progress demands regular investment over time."),
            ("Host1", f"Et le cinquième mot clé est **confiance**, indispensable pour s'exprimer librement et sans réserve.",
                      f"And the fifth key word is 'confidence', indispensable to express oneself freely and without reserve."),
            ("Host2", f"Nous invitons nos auditeurs à rédiger en commentaire une phrase originale avec l'un de ces **termes**.",
                      f"We invite our listeners to write in the comments an original sentence with one of these terms."),
            ("Host1", f"C'est un excellent exercice pratique que nous lirons avec beaucoup d'attention et de **joie**.",
                      f"It's an excellent practical exercise that we will read with great attention and joy."),
            ("Host2", f"Participer activement permet d'ancrer les tournures idiomatiques dans votre esprit pour **toujours**.",
                      f"Participating actively allows anchoring idiomatic turns in your mind forever."),
            ("Host1", f"Passons maintenant au mot de la fin pour clôturer ce superbe **numéro**.",
                      f"Let's move on to the final remarks to close this superb issue.")
        ],
        # Phase 10: Conclusion & wrap-up
        [
            ("Host2", f"Notre épisode d'aujourd'hui consacré à **{topic_es}** touche désormais à sa fin.",
                      f"Our episode today dedicated to {topic_en} is now coming to an end."),
            ("Host1", f"Que le temps passe vite en si bonne compagnie! Nous avons partagé beaucoup de notions **enrichissantes**.",
                      f"How time flies in such good company! We shared many enriching notions."),
            ("Host2", f"Pensez à réécouter cet enregistrement plusieurs fois pour parfaire votre oreille et votre **prononciation**.",
                      f"Remember to listen back to this recording multiple times to perfect your ear and pronunciation."),
            ("Host1", f"Chaque écoute supplémentaire rendra votre débit plus fluide, plus naturel et plus **élégant**.",
                      f"Each additional listen will make your speech more fluent, more natural and more elegant."),
            ("Host2", f"Un grand merci à toutes et à tous pour votre fidélité constante et vos messages chaleureux sur notre **chaîne**.",
                      f"A big thank you to all of you for your constant loyalty and warm messages on our channel."),
            ("Host1", f"Abonnez-vous à Velocity French, laissez un pouce bleu et faites découvrir le podcast à vos **amis**.",
                      f"Subscribe to Velocity French, leave a thumbs up and introduce the podcast to your friends."),
            ("Host2", f"De nombreux autres thèmes passionnants et faciles à suivre vous attendent très **bientôt**.",
                      f"Many other exciting and easy-to-follow topics await you very soon."),
            ("Host1", f"Nous vous souhaitons une merveilleuse journée et un bel élan dans vos **études**!",
                      f"We wish you a wonderful day and great momentum in your studies!"),
            ("Host2", f"Prenez soin de vous et à très vite pour un prochain **rendez-vous**!",
                      f"Take care and see you very soon for the next meeting!"),
            ("Host1", f"Au revoir chers amis, et continuez à pratiquer le français avec passion et **sourire**!",
                      f"Goodbye dear friends, and keep practicing French with passion and a smile!")
        ]
    ]

    all_templates = []
    for ph in phases:
        all_templates.extend(ph)
    turns = []
    for i in range(target):
        _, t_fr, t_en = all_templates[i % len(all_templates)]
        spk = "Host2" if i % 2 == 0 else "Host1"
        turns.append({"speaker": spk, "french": t_fr, "english": t_en})
    return turns


def _extend_script(existing_turns, topic_es, topic_en, target=150):
    fallback_pool = _fallback_script(topic_es, topic_en, target)
    idx = 0
    cur_speaker = existing_turns[-1]["speaker"] if existing_turns else "Host1"
    while len(existing_turns) < target:
        cand = fallback_pool[idx % len(fallback_pool)]
        idx += 1
        needed_spk = "Host1" if cur_speaker == "Host2" else "Host2"
        existing_turns.append({
            "speaker": needed_spk,
            "french": cand["french"],
            "english": cand["english"]
        })
        cur_speaker = needed_spk
    return existing_turns[:target]


def generate_script():
    topic = _generate_topic() or random.choice(TOPICS)
    topic_es = topic.split(" - ")[0]
    topic_en = topic.split(" - ")[1]

    TARGET = 150
    BATCH = 10
    all_turns = []
    consecutive_empty = 0
    import time as _time
    _deadline = _time.time() + 600  # generous 10 min cap

    while len(all_turns) < TARGET and consecutive_empty < 12 and _time.time() < _deadline:
        batch = _fetch_turns_batch(topic, topic_es, topic_en, len(all_turns), BATCH)
        if not batch:
            consecutive_empty += 1
            wait_s = min(15, 3 + consecutive_empty * 2)
            print(f"  API busy (consecutive fails: {consecutive_empty}) - waiting {wait_s}s before retrying...", flush=True)
            _time.sleep(wait_s)
            continue
        all_turns.extend(batch)
        consecutive_empty = 0
        print(f"  Script progress: {len(all_turns)}/{TARGET} turns", flush=True)
        if len(all_turns) < TARGET:
            _time.sleep(1)

    all_turns = all_turns[:TARGET]

    if not all_turns:
        print("  Using structured fallback script (150 unique turns)...", flush=True)
        all_turns = _fallback_script(topic_es, topic_en, TARGET)
    elif len(all_turns) < TARGET:
        print(f"  Extending {len(all_turns)} turns to {TARGET} with topic conversation...", flush=True)
        all_turns = _extend_script(all_turns, topic_es, topic_en, TARGET)

    # Short 2-line intro: Thomas (Host2) first, then Sophie (Host1), then topic
    all_turns[0]["speaker"] = "Host2"
    all_turns[0]["french"] = f"Bonjour, je suis Thomas. Bienvenue à Velocity French. Aujourd'hui, on parle de **{topic_es}**."
    all_turns[0]["english"] = f"Hi, I'm Thomas. Welcome to Velocity French Podcast. Today we talk about {topic_en}."
    if len(all_turns) > 1:
        all_turns[1]["speaker"] = "Host1"
        all_turns[1]["french"] = f"Merci, Thomas. Le sujet d'aujourd'hui est très **intéressant**. Commençons."
        all_turns[1]["english"] = f"Thanks, Thomas. Today's topic is very interesting. Let's start."

    print(f"  Script: {len(all_turns)} turns, topic: {topic_es}", flush=True)
    return all_turns, topic_es, topic_en


async def generate_audio(turns, target_dir=None):
    import edge_tts
    audio_files = []
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        audio_dir = Path(target_dir) if target_dir else OUTPUT_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        filename = audio_dir / f"audio_{i:03d}.mp3"
        spoken_text = re.sub(r'\*\*(.*?)\*\*', r'\1', turn.get("french", turn.get("spanish", "")))
        try:
            communicate = edge_tts.Communicate(spoken_text, voice)
            await communicate.save(str(filename))
            try:
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(filename)], capture_output=True, text=True)
                duration = float(r.stdout.strip()) if r.stdout else 3.0
            except:
                duration = 3.0
        except Exception as e:
            print(f"  Audio {i} failed: {e}")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(filename)], capture_output=True)
            duration = 3.0
        audio_files.append({"path": str(filename), "duration": duration, "speaker": turn["speaker"]})
    return audio_files

def create_video(turns, audio_files, video_dir=None):
    if video_dir is None:
        video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir = Path(video_dir)
    video_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    total_dur = 0

    for i, (turn, audio) in enumerate(zip(turns, audio_files)):
        img = video_dir / f"f_{i:04d}.png"
        create_frame(turn, str(img), i)
        clip = video_dir / f"c_{i:04d}.mp4"
        clips.append(clip)
        dur = audio["duration"]
        fade_start = max(0.0, dur - 0.3)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", audio["path"],
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-preset", "medium",
            "-t", str(dur), "-af", f"afade=t=out:st={fade_start:.2f}:d=0.3",
            str(clip)
        ], check=True, capture_output=True)

        total_dur += audio["duration"]
        if (i + 1) % 25 == 0:
            print(f"  Frame {i+1}/{len(turns)}")

    concat = video_dir / "list.txt"
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    out = video_dir / "podcast_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-movflags", "+faststart", str(out)], check=True)

    for c in clips:
        c.unlink(missing_ok=True)
    for a in audio_files:
        try:
            Path(a["path"]).unlink(missing_ok=True)
        except Exception:
            pass
    if concat.exists():
        concat.unlink(missing_ok=True)

    return out, total_dur


async def main():
    print("=" * 60)
    print("  VELOCITY FRENCH PODCAST")
    print("=" * 60)

    print("\n[1/4] Generating script (150 turns)...")
    turns, topic_es, topic_en = generate_script()

    video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(video_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump({"topic": topic_es, "topic_en": topic_en, "turns": turns}, f, indent=2, ensure_ascii=False)

    print(f"\n[2/4] Generating audio ({len(turns)} turns)...")
    audio_files = await generate_audio(turns, video_dir)
    total_audio = sum(a["duration"] for a in audio_files)
    print(f"  Total audio: {total_audio/60:.1f} min")

    print(f"\n[3/4] Creating video...")
    video_path, duration = create_video(turns, audio_files, video_dir)

    print(f"\n[4/4] Saving...")
    first_frame = video_dir / "f_0000.png"
    thumbnail_path = video_dir / "thumbnail.jpg"
    try:
        from PIL import Image as _Img
        if first_frame.exists():
            _Img.open(str(first_frame)).convert("RGB").save(str(thumbnail_path), quality=92)
    except Exception as e:
        print(f"  Thumbnail warn: {e}")

    title = build_podcast_title(topic_es, topic_en)
    description = build_podcast_description(topic_es, topic_en, len(turns), round(duration / 60, 1))
    tags = ["Learn French", "French", "French Podcast", "Learn French Naturally",
            "French for Beginners", "Bilingual", "French Listening", "French Conversation",
            topic_es, "Velocity French"]

    meta_out = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_english": topic_es,
        "language": "French",
        "duration_minutes": round(duration / 60, 1),
        "turns_count": len(turns),
        "video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "generated_at": datetime.now().isoformat(),
    }
    (OUTPUT_DIR).mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "latest_video.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_DIR / "latest_upload_info.json", "w", encoding="utf-8") as f:
        json.dump({"title": title, "description": description,
                   "category": topic_es, "turns_count": len(turns)}, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("  PODCAST COMPLETE!")
    print(f"  Topic: {topic_es}")
    print(f"  Duration: {duration/60:.1f} min ({len(turns)} turns)")
    print(f"  Video: {video_path.name}")
    print("=" * 60)


def build_podcast_title(topic_es, topic_en):
    titles = [
        f"French Podcast: {topic_es} | Apprends le Français",
        f"Learn French: {topic_es} | Bilingual Podcast",
        f"{topic_es} | French Conversation for Beginners",
        f"{topic_es} | Pratique ton Français avec Sophie et Thomas",
    ]
    return random.choice(titles)


def build_podcast_description(topic_es, topic_en, turns_count, duration_min):
    description = (
        f"🎙️ Bienvenue à Velocity French Podcast!\n\n"
        f"Dans cet épisode, Sophie et Thomas parlent de: {topic_es} ({topic_en}).\n"
        f"Une conversation bilingue et détendue, au niveau A2, pour apprendre le français naturellement.\n\n"
        f"✨ WHAT'S INSIDE THIS EPISODE:\n"
        f"• {turns_count} phrases et expressions utiles en français\n"
        f"• Conversation réelle avec du vocabulaire quotidien\n"
        f"• Prononciation naturelle de locuteurs natifs\n"
        f"• Traduction en anglais à chaque ligne\n\n"
        f"📌 HOW TO USE THIS PODCAST:\n"
        f"1️⃣ Écoutez la partie en français et essayez de comprendre\n"
        f"2️⃣ Vérifiez la traduction en anglais\n"
        f"3️⃣ Répétez les phrases à voix haute\n"
        f"4️⃣ Réécoutez demain - chaque jour devient plus facile!\n\n"
        f"🔔 Abonnez-vous pour une nouvelle leçon chaque jour.\n\n"
        f"📅 Durée: {duration_min} minutes\n\n"
        f"#LearnFrench #FrenchPodcast #Bilingual #LanguageLearning"
    )
    return description



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('  Cancelled.')