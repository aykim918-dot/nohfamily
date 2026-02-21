# ============================================================
#  삼둥이 AI 학습 앱  |  NZ Year 5-6  |  시완 · 시원 · 시호
#  Tech: Streamlit + Google Gemini AI + Google Sheets
# ============================================================

# ============================================================
#  라이브러리
# ============================================================
import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import random
import calendar
from datetime import date, datetime

try:
    from streamlit_gsheets import GSheetsConnection
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# ============================================================
#  API 키 설정 (imports 이후에 위치해야 st.secrets 사용 가능)
# ============================================================
api_key = st.secrets["GEMINI_API_KEY"]          # ← Streamlit Secrets에서 자동으로 가져옵니다
GSHEET_URL = '여기에_구글시트_URL을_넣으세요'  # ← Google Sheets URL을 여기에 입력하세요

# ============================================================
#  학생 프로파일 (학습 스타일 기반 개인화)
# ============================================================
STUDENTS = {
    "시완": {
        "emoji": "🧠",
        "style": "logical",
        "color": "#3B82F6",
        "style_desc": "논리적 · 분석적",
        "passage_style": "analytical with clear cause-and-effect relationships, logical structure, and factual information",
        "math_style": "emphasizing pattern recognition, proof-like reasoning, and systematic step-by-step logic",
        "praise": [
            "완벽한 논리야, 시완! 문제의 구조를 정확히 꿰뚫었어! 🎯",
            "역시 시완! 단계별로 완벽하게 분석해냈어! 미래의 과학자네! 🔬",
            "논리력 만점! 이 어려운 문제를 이렇게 체계적으로 풀다니! 🏆",
        ],
        "encouragement": [
            "시완아, 단계별로 다시 접근해봐! 논리적으로 따라가면 답이 보일 거야! 💪",
            "패턴을 다시 찾아봐! 시완이가 좋아하는 '왜냐하면~' 방식으로 생각해봐! 🤔",
            "괜찮아! 조건을 하나씩 정리해보면 분명히 풀 수 있어! 📋",
        ],
        "eng_tip": "글의 논리 구조(원인→결과, 주장→근거)를 먼저 파악해봐!",
        "math_tip": "공식을 먼저 쓰고, 단계별로 차근차근 계산해봐!",
        # 해설 생성 시 스타일 지침
        "expl_style": (
            "시완은 논리적 분석을 좋아해. "
            "각 풀이 단계를 ①②③ 번호로 나눠서 설명하고, "
            "'왜냐하면', '따라서', '결론적으로' 같은 논리적 연결어를 사용해줘. "
            "왜 오답인지 논리적 근거를 먼저 제시하고, 올바른 추론 과정을 단계별로 보여줘."
        ),
    },
    "시원": {
        "emoji": "🔢",
        "style": "arithmetic",
        "color": "#F97316",
        "style_desc": "계산적 · 수리적",
        "passage_style": "informational with numbers, statistics, measurements, and quantifiable data",
        "math_style": "with multiple calculation steps, precise arithmetic, and opportunities for verification",
        "praise": [
            "완벽한 계산이야, 시원! 숫자 하나도 틀리지 않았어! 계산왕! 🧮",
            "믿을 수 없어! 이런 복잡한 계산을 이렇게 정확하게! 시원 최고! ⭐",
            "수학 천재 등장! 숫자들을 이렇게 완벽하게 다루다니! 🏆",
        ],
        "encouragement": [
            "시원아, 계산을 다시 한번 검산해봐! 작은 실수일 수 있어! 🔍",
            "숫자를 천천히 다시 계산해봐! 너의 계산 실력이라면 분명히 찾을 거야! 💪",
            "단계별로 계산 결과를 확인해봐! 넌 할 수 있어! 🎯",
        ],
        "eng_tip": "모르는 단어의 뜻은 앞뒤 숫자나 수량 표현으로 추측해봐!",
        "math_tip": "중간 계산 결과를 반드시 검산하는 습관을 들여봐!",
        "expl_style": (
            "시원은 숫자와 계산을 직관적으로 이해해. "
            "시각적 비유(수직선, 도형, 분수 막대)를 텍스트로 묘사해주고, "
            "모든 숫자 계산은 LaTeX 수식으로 깔끔하게 표시해줘. "
            "'이 숫자들을 보면...', '계산해보면...' 같은 직관적 표현을 써줘. "
            "검산 방법도 마지막에 보여줘."
        ),
    },
    "시호": {
        "emoji": "📚",
        "style": "linguistic",
        "color": "#8B5CF6",
        "style_desc": "언어적 · 이야기형",
        "passage_style": "narrative and descriptive with rich vocabulary, vivid imagery, and compelling storytelling",
        "math_style": "with rich story contexts, vivid real-world scenarios, and descriptive language",
        "praise": [
            "멋져, 시호! 이야기 속 숨은 의미를 완벽하게 찾아냈어! 📖",
            "언어 감각이 최고야! 시호는 진짜 독서왕이네! 📚",
            "와~ 이렇게 어려운 글도 이해하다니! 작가가 되어도 되겠는걸! ✍️",
        ],
        "encouragement": [
            "시호야, 본문을 다시 읽어봐! 답의 힌트가 이야기 속에 숨어 있어! 🔍",
            "단어의 '느낌'으로 생각해봐! 시호는 감각이 좋으니까 분명히 알 거야! 💫",
            "이야기 흐름을 따라가봐! 주인공이라면 어떻게 했을까? 🌟",
        ],
        "eng_tip": "글의 분위기와 등장인물의 감정에 집중해봐!",
        "math_tip": "문제를 이야기로 상상하면서 풀어봐! 주인공이 되어봐!",
        "expl_style": (
            "시호는 이야기와 맥락 속에서 이해해. "
            "문제 상황을 하나의 짧은 이야기로 재구성해서 설명해줘. "
            "'이 이야기에서...', '주인공처럼 생각해보면...' 같은 표현을 써줘. "
            "단어나 개념을 일상적인 상황에 비유해서 설명하고, "
            "지문이 있다면 어느 부분이 힌트인지 직접 인용해줘."
        ),
    },
}

# ============================================================
#  배지 시스템
# ============================================================
BADGES = [
    {"name": "Explorer",     "emoji": "🗺️",  "points": 10,   "desc": "첫 번째 퀴즈 완료!"},
    {"name": "Newton",       "emoji": "🍎",  "points": 50,   "desc": "수학에서 50점 달성!"},
    {"name": "Shakespeare",  "emoji": "📖",  "points": 100,  "desc": "영어에서 100점 달성!"},
    {"name": "Magellan",     "emoji": "⛵",  "points": 150,  "desc": "총 150점 달성!"},
    {"name": "Einstein",     "emoji": "🧬",  "points": 300,  "desc": "총 300점 달성!"},
    {"name": "Archimedes",   "emoji": "💡",  "points": 500,  "desc": "총 500점 달성!"},
    {"name": "Marie Curie",  "emoji": "⚗️",  "points": 800,  "desc": "총 800점 달성!"},
    {"name": "Da Vinci",     "emoji": "🎨",  "points": 1200, "desc": "총 1200점 달성!"},
]

# ============================================================
#  Google Sheets 함수
# ============================================================
def _get_conn():
    if not GSHEETS_AVAILABLE:
        return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        return None

def _read_sheet(conn, sheet_name="오답노트"):
    try:
        df = conn.read(spreadsheet=GSHEET_URL, worksheet=sheet_name, ttl=10)
        return df if df is not None and not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def save_wrong_answer(student, subject, question, correct, user_ans, concept, difficulty):
    """오답을 Google Sheets에 저장 (폴백: 세션 상태)"""
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "student": student,
        "subject": subject,
        "question": question[:300],
        "correct_answer": correct,
        "user_answer": user_ans,
        "concept": concept,
        "difficulty": difficulty,
        "reviewed": False,
    }
    conn = _get_conn()
    if conn:
        try:
            df = _read_sheet(conn)
            updated = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            conn.update(spreadsheet=GSHEET_URL, worksheet="오답노트", data=updated)
            return
        except Exception:
            pass
    st.session_state.wrong_log.append(record)

def get_wrong_concepts(student, subject):
    """해당 학생의 미복습 오답 개념 목록"""
    conn = _get_conn()
    if conn:
        try:
            df = _read_sheet(conn)
            if not df.empty and "student" in df.columns:
                mask = (
                    (df["student"] == student) &
                    (df["subject"] == subject) &
                    (df["reviewed"].astype(str).str.lower() != "true")
                )
                return df.loc[mask, "concept"].dropna().tolist()
        except Exception:
            pass
    return [
        w["concept"]
        for w in st.session_state.wrong_log
        if w["student"] == student and w["subject"] == subject and not w.get("reviewed", False)
    ]

def save_study_record(student, subject, score, total):
    """학습 기록 + 포인트 업데이트"""
    today = date.today().isoformat()
    key = f"{student}_{today}"
    if key not in st.session_state.study_records:
        st.session_state.study_records[key] = {}
    st.session_state.study_records[key][subject] = {
        "score": score,
        "total": total,
        "pct": round(score / total * 100, 1),
    }
    pts = score * 5
    st.session_state.points[student] = st.session_state.points.get(student, 0) + pts
    return pts

# ============================================================
#  AI 핵심 호출 함수
# ============================================================
def _fix_json_escapes(s: str) -> str:
    """JSON 내 LaTeX 백슬래시 이스케이프 오류 수정 (문자 단위 처리)"""
    valid_escapes = set('"\\\/bfnrt')
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            next_char = s[i + 1]
            if next_char in valid_escapes:
                result.append('\\')
                result.append(next_char)
                i += 2
            elif (next_char == 'u' and i + 5 < len(s) and
                  all(c in '0123456789abcdefABCDEF' for c in s[i+2:i+6])):
                result.append(s[i:i+6])
                i += 6
            else:
                result.append('\\\\')
                i += 1
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)

def _parse_json(json_str: str):
    """JSON 파싱 — 실패 시 이스케이프 수정 후 재시도"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return json.loads(_fix_json_escapes(json_str))

def _call_gemini(prompt: str) -> dict | None:
    """Gemini API 호출 → JSON 반환"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    try:
        resp = model.generate_content(prompt)
        raw = resp.text
        m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
        if m:
            return _parse_json(m.group(1))
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return _parse_json(m.group())
        return None
    except Exception as e:
        st.error(f"AI 오류: {e}")
        return None

def _call_gemini_text(prompt: str) -> str:
    """Gemini API 호출 → 텍스트 반환"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return ""

# ============================================================
#  AI 문제 생성 함수
# ============================================================
def generate_english_questions(student: str, difficulty: str, wrong_concepts: list) -> dict | None:
    info = STUDENTS[student]
    diff_map = {
        "easy":   "Book 4 of '4000 Essential English Words'",
        "medium": "Book 4 and Book 5 of '4000 Essential English Words'",
        "hard":   "Book 5 of '4000 Essential English Words' (advanced vocabulary)",
    }
    review_note = (
        f"IMPORTANT: Include questions that review these vocabulary concepts "
        f"the student previously got wrong: {', '.join(wrong_concepts[:4])}. "
        if wrong_concepts else ""
    )
    prompt = f"""
You are creating an English reading quiz for a New Zealand Year 5-6 student named {student}.
Learning style: {info['style']} — write the passage in a style that is {info['passage_style']}.
Vocabulary source: {diff_map[difficulty]}.
{review_note}

TASK: Generate a JSON object with this EXACT structure:
```json
{{
  "passage_title": "Title here",
  "passage": "2-3 paragraph reading passage (150-200 words). Write key vocabulary words in ALL CAPS.",
  "questions": [
    {{
      "id": 1,
      "type": "comprehension",
      "question": "Question text?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "A",
      "concept": "main_idea",
      "explanation": "One sentence explaining the correct answer, referencing the passage."
    }}
  ]
}}
```

QUESTION RULES:
- Questions 1-10: Reading COMPREHENSION (types: main_idea, detail, inference, author_purpose, vocabulary_in_context)
- Questions 11-20: VOCABULARY (types: definition, synonym, antonym, context_clue, word_usage)
- Exactly 20 questions total, all 4-option multiple choice (A/B/C/D)
- Wrong options must reflect real student errors (plausible distractors)
- All content appropriate for 10-12 year olds
- Write entirely in English (questions and options)
- explanation field: briefly state WHERE in the passage the answer is found
"""
    return _call_gemini(prompt)

def generate_math_questions(student: str, difficulty: str, wrong_concepts: list) -> dict | None:
    info = STUDENTS[student]
    diff_map = {
        "easy":   "NZC Level 3-4 (Year 5-6): basic fractions, simple decimals, whole number operations",
        "medium": "NZC Level 4 (Year 6-7): fraction operations, decimals to 3dp, simple algebraic equations (e.g. 3x + 4 = 19)",
        "hard":   "NZC Level 4-5 (Year 7-8): complex fraction operations, multi-step algebra, ratio & proportion, percentage problems",
    }
    review_note = (
        f"IMPORTANT: Include at least 3 questions that directly address these concepts "
        f"the student previously struggled with: {', '.join(wrong_concepts[:4])}. "
        if wrong_concepts else ""
    )
    prompt = f"""
You are creating a Singapore Math-style quiz for a New Zealand Year 6-7 student named {student}.
Learning style: {info['style']} — frame word problems {info['math_style']}.
Curriculum level: {diff_map[difficulty]}.
{review_note}

TASK: Generate a JSON object with this EXACT structure:
```json
{{
  "questions": [
    {{
      "id": 1,
      "topic": "fractions",
      "question": "Full word problem text here.",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "A",
      "concept": "fraction_multiplication",
      "solution": "Step 1: [describe step]. Step 2: [formula]. Step 3: Answer = [value]",
      "explanation": "One sentence why this is correct."
    }}
  ]
}}
```

QUESTION DISTRIBUTION (exactly 20 questions, all multiple choice A/B/C/D):
- Questions 1-5: FRACTIONS (add, subtract, multiply, divide fractions & mixed numbers)
- Questions 6-10: DECIMALS & PERCENTAGES (operations, conversion, % of a quantity)
- Questions 11-15: BASIC ALGEBRA (solve for x, simplify expressions, number patterns)
- Questions 16-20: MULTI-STEP WORD PROBLEMS (Singapore bar model style, NZ contexts: rugby, farms, beaches, kiwi birds)

RULES:
- Wrong options must reflect real student errors (wrong operation, arithmetic slip, unit confusion)
- solution field: write ALL arithmetic using LaTeX notation e.g. $\\frac{{3}}{{4}} \\times \\frac{{2}}{{3}} = \\frac{{6}}{{12}} = \\frac{{1}}{{2}}$
- Use New Zealand real-world contexts in word problems
- All content appropriate for 10-12 year olds
"""
    return _call_gemini(prompt)

# ============================================================
#  AI 개인화 해설 생성 (핵심 신규 함수)
# ============================================================
def generate_ai_explanation(
    student: str,
    subject: str,
    q: dict,
    user_answer: str,
    passage: str = "",
) -> dict:
    """
    오답 1문항에 대해 학생 맞춤형 AI 튜터 해설을 생성한다.
    반환: {error_type, error_type_ko, why_wrong, steps, key_takeaway, encouragement}
    """
    info = STUDENTS[student]

    if subject == "math":
        prompt = f"""
너는 따뜻하고 친절한 초등 수학 선생님이야. 아래 수학 오답 문제를 {student}에게 설명해줘.

[학생 정보]
이름: {student} / 학습 스타일: {info['style_desc']}
해설 방식: {info['expl_style']}

[문제]
{q.get('question', '')}

[보기]
{chr(10).join(q.get('options', []))}

[학생 답]: {user_answer} (오답)
[정답]: {q.get('correct', '')}
[개념]: {q.get('concept', '')}
[모범 풀이 참고]: {q.get('solution', '')}

아래 JSON 형식으로만 출력해 (다른 말 없이):
```json
{{
  "error_type": "careless 또는 concept 중 하나",
  "error_type_ko": "단순실수 또는 개념부족 중 하나",
  "why_wrong": "학생이 고른 답이 왜 틀렸는지 1-2문장. 한국어.",
  "steps": [
    "① [풀이 첫 단계 - LaTeX 수식 포함, 예: $\\frac{{3}}{{4}} \\times \\frac{{2}}{{3}} = \\frac{{6}}{{12}}$]",
    "② [풀이 둘째 단계]",
    "③ [최종 답 확인]"
  ],
  "key_takeaway": "이 개념의 핵심을 한 문장으로. 한국어.",
  "encouragement": "10-12세 아이에게 따뜻한 격려 한 마디. 한국어."
}}
```

LaTeX 사용 규칙:
- 분수: $\\frac{{분자}}{{분모}}$
- 곱하기: $\\times$, 나누기: $\\div$
- 방정식: $3x + 4 = 19$
- 소수: $3.25 + 1.75 = 5.00$
반드시 초등학생 눈높이로 쉽고 친절하게 써줘. 학습 스타일({info['expl_style']})을 꼭 반영해줘.
"""
    else:  # English
        prompt = f"""
너는 따뜻하고 친절한 초등 영어 선생님이야. 아래 영어 독해/어휘 오답 문제를 {student}에게 설명해줘.

[학생 정보]
이름: {student} / 학습 스타일: {info['style_desc']}
해설 방식: {info['expl_style']}

[지문 (참고용)]
{passage[:600] if passage else '지문 없음'}

[문제]
{q.get('question', '')}

[보기]
{chr(10).join(q.get('options', []))}

[학생 답]: {user_answer} (오답)
[정답]: {q.get('correct', '')}
[문제 유형]: {q.get('concept', '')}
[정답 근거]: {q.get('explanation', '')}

아래 JSON 형식으로만 출력해 (다른 말 없이):
```json
{{
  "error_type": "careless 또는 concept 중 하나",
  "error_type_ko": "단순실수 또는 개념부족 중 하나",
  "why_wrong": "학생이 고른 답이 왜 틀렸는지 1-2문장. 한국어.",
  "steps": [
    "① [지문 어느 부분에 근거가 있는지 인용 포함]",
    "② [그 부분이 무엇을 의미하는지]",
    "③ [따라서 정답이 왜 맞는지]"
  ],
  "key_takeaway": "이런 유형 문제를 잘 푸는 핵심 전략 한 문장. 한국어.",
  "encouragement": "10-12세 아이에게 따뜻한 격려 한 마디. 한국어."
}}
```

반드시 초등학생 눈높이로 쉽고 친절하게 써줘. 학습 스타일({info['expl_style']})을 꼭 반영해줘.
지문의 근거가 있다면 반드시 인용해줘.
"""

    result = _call_gemini(prompt)
    if result:
        return result
    # 폴백
    return {
        "error_type": "concept",
        "error_type_ko": "개념부족",
        "why_wrong": "이 문제를 다시 한번 살펴봐!",
        "steps": [
            f"① 정답은 {q.get('correct', '')}이야.",
            f"② {q.get('explanation', '')}",
        ],
        "key_takeaway": "다음에 비슷한 문제가 나오면 더 잘 풀 수 있을 거야!",
        "encouragement": random.choice(info["encouragement"]),
    }

# ============================================================
#  AI 전체 개인화 피드백 (세션 종료 후)
# ============================================================
def generate_ai_feedback(student: str, subject: str, score: int, total: int, wrong_concepts: list) -> str:
    pct = round(score / total * 100, 1)
    info = STUDENTS[student]
    prompt = f"""
{student}(이)라는 학생에게 한국어로 따뜻한 학습 피드백을 3-4문장으로 써줘.
- 학생의 학습 스타일: {info['style_desc']}
- 학습 스타일 특성: {info['expl_style']}
- 과목: {subject}
- 점수: {score}/{total} ({pct}%)
- 틀린 개념: {', '.join(wrong_concepts) if wrong_concepts else '없음'}

조건:
1. 학습 스타일에 딱 맞는 표현과 비유 사용
2. 구체적이고 따뜻하게 칭찬 또는 격려
3. 틀린 개념이 있으면 복습 팁 1개 포함
4. 10-12세 아이 말투로
5. 한국어로만
6. 이모지 1-2개 포함

피드백만 출력해 (제목, 설명 없이).
"""
    result = _call_gemini_text(prompt)
    if result:
        return result
    if pct >= 80:
        return random.choice(info["praise"])
    return random.choice(info["encouragement"])

# ============================================================
#  난이도 자동 계산
# ============================================================
def calc_difficulty(student: str, subject: str) -> str:
    records = st.session_state.study_records
    recent = [
        v[subject]["pct"]
        for k, v in records.items()
        if k.startswith(student) and subject in v
    ][-5:]
    if not recent:
        return "easy"
    avg = sum(recent) / len(recent)
    if avg >= 80:
        return "hard"
    if avg >= 60:
        return "medium"
    return "easy"

# ============================================================
#  영어 퀴즈 UI
# ============================================================
def run_english_quiz(student: str):
    info = STUDENTS[student]
    st.markdown("## 📖 영어 읽기 & 어휘 퀴즈")
    st.caption(f"{info['emoji']} {student} · {info['style_desc']} 스타일 맞춤 문제")

    difficulty = calc_difficulty(student, "english")
    diff_labels = {"easy": "⭐ 기본", "medium": "⭐⭐ 보통", "hard": "⭐⭐⭐ 심화"}
    st.info(f"현재 난이도: **{diff_labels[difficulty]}** (정답률에 따라 자동 조정됩니다)")

    wrong_concepts = get_wrong_concepts(student, "english")
    if wrong_concepts:
        st.warning(f"📌 이전에 틀린 개념 ({', '.join(set(wrong_concepts[:3]))}) 복습 문제가 포함되었어요!")

    data_key  = f"eng_data_{student}"
    ans_key   = f"eng_ans_{student}"
    done_key  = f"eng_done_{student}"
    expl_key  = f"explanations_english_{student}"

    if data_key not in st.session_state:
        with st.spinner("🤖 AI가 맞춤 문제를 만들고 있어요... (약 30초 소요)"):
            data = generate_english_questions(student, difficulty, wrong_concepts)
        if not data or "questions" not in data:
            st.error("문제 생성에 실패했습니다. API 키와 인터넷 연결을 확인해주세요.")
            return
        st.session_state[data_key]  = data
        st.session_state[ans_key]   = {}
        st.session_state[done_key]  = False
        st.session_state[expl_key]  = {}  # 해설 캐시 초기화

    data      = st.session_state[data_key]
    answers   = st.session_state[ans_key]
    submitted = st.session_state[done_key]
    passage   = data.get("passage", "")

    # ── 지문 표시 ──
    st.markdown("---")
    st.markdown(f"### 📝 {data.get('passage_title', '읽기 지문')}")
    passage_html = passage.replace("\n", "<br>")
    st.markdown(
        f"""<div style="background:#F0F9FF; border-left:4px solid {info['color']};
        padding:18px 22px; border-radius:10px; line-height:1.9; font-size:1.05em">
        {passage_html}</div>""",
        unsafe_allow_html=True,
    )
    st.markdown(f"> 💡 **{student}의 팁**: {info['eng_tip']}")
    st.markdown("---")

    questions = data.get("questions", [])
    if not questions:
        st.error("문제 데이터가 없습니다. 다시 시도해주세요.")
        return

    # ── 문제 표시 (미제출 시) ──
    if not submitted:
        with st.form(key=f"eng_form_{student}", border=False):
            comp_qs  = [q for q in questions if q.get("type") == "comprehension"][:10]
            vocab_qs = [q for q in questions if q.get("type") != "comprehension"][:10]
            # 부족하면 채우기
            remaining = [q for q in questions if q not in comp_qs and q not in vocab_qs]
            comp_qs  += remaining[:max(0, 10 - len(comp_qs))]
            vocab_qs += remaining[max(0, 10 - len(comp_qs)):max(0, 10 - len(vocab_qs)) + max(0, 10 - len(comp_qs))]

            st.markdown("#### 📖 Part 1 — 독해 문제 (1~10번)")
            for q in comp_qs:
                _render_question(q, f"eng_{student}", answers, False)

            st.markdown("#### 📚 Part 2 — 어휘 문제 (11~20번)")
            for q in vocab_qs:
                _render_question(q, f"eng_{student}", answers, False)

            submitted_btn = st.form_submit_button(
                "✅ 제출하고 채점받기", type="primary", use_container_width=True
            )
            if submitted_btn:
                answered = sum(1 for q in questions if q.get("id") in answers)
                if answered < len(questions):
                    st.warning(f"모든 문제에 답해주세요! ({answered}/{len(questions)}개 완료)")
                else:
                    st.session_state[done_key] = True
                    st.rerun()

    # ── 채점 & 해설 화면 ──
    if submitted:
        _show_grading_screen(
            student, "english", questions, answers, difficulty,
            passage=passage, expl_cache_key=expl_key
        )
        st.markdown("---")
        if st.button("🔄 새 문제 풀기", use_container_width=True, key=f"eng_reset_{student}"):
            for k in [data_key, ans_key, done_key, expl_key]:
                st.session_state.pop(k, None)
            st.rerun()

# ============================================================
#  수학 퀴즈 UI
# ============================================================
def run_math_quiz(student: str):
    info = STUDENTS[student]
    st.markdown("## 🔢 수학 퀴즈 — 싱가포르 매쓰 스타일")
    st.caption(f"{info['emoji']} {student} · {info['style_desc']} 스타일 맞춤 문제")

    difficulty = calc_difficulty(student, "math")
    diff_labels = {"easy": "⭐ 기본 (Level 3-4)", "medium": "⭐⭐ 보통 (Level 4)", "hard": "⭐⭐⭐ 심화 (Level 4-5)"}
    st.info(f"현재 난이도: **{diff_labels[difficulty]}** (정답률에 따라 자동 조정됩니다)")

    wrong_concepts = get_wrong_concepts(student, "math")
    if wrong_concepts:
        st.warning(f"📌 이전에 틀린 개념 ({', '.join(set(wrong_concepts[:3]))}) 복습 문제가 포함되었어요!")

    data_key  = f"math_data_{student}"
    ans_key   = f"math_ans_{student}"
    done_key  = f"math_done_{student}"
    expl_key  = f"explanations_math_{student}"

    if data_key not in st.session_state:
        with st.spinner("🤖 AI가 수학 문제를 만들고 있어요... (약 30초 소요)"):
            data = generate_math_questions(student, difficulty, wrong_concepts)
        if not data or "questions" not in data:
            st.error("문제 생성에 실패했습니다. API 키와 인터넷 연결을 확인해주세요.")
            return
        st.session_state[data_key]  = data
        st.session_state[ans_key]   = {}
        st.session_state[done_key]  = False
        st.session_state[expl_key]  = {}

    data      = st.session_state[data_key]
    answers   = st.session_state[ans_key]
    submitted = st.session_state[done_key]
    questions = data.get("questions", [])

    if not questions:
        st.error("문제 데이터가 없습니다. 다시 시도해주세요.")
        return

    if not submitted:
        st.markdown(f"> 💡 **{student}의 수학 팁**: {info['math_tip']}")
        topic_sections = [
            ("🎂 분수",          questions[0:5]),
            ("💯 소수 & 백분율",  questions[5:10]),
            ("🔣 기초 대수",      questions[10:15]),
            ("📖 문장제 문제",    questions[15:20]),
        ]
        with st.form(key=f"math_form_{student}", border=False):
            for section_name, section_qs in topic_sections:
                if section_qs:
                    st.markdown(f"#### {section_name}")
                    for q in section_qs:
                        _render_question(q, f"math_{student}", answers, False)

            submitted_btn = st.form_submit_button(
                "✅ 제출하고 채점받기", type="primary", use_container_width=True
            )
            if submitted_btn:
                answered = sum(1 for q in questions if q.get("id") in answers)
                if answered < len(questions):
                    st.warning(f"모든 문제에 답해주세요! ({answered}/{len(questions)}개 완료)")
                else:
                    st.session_state[done_key] = True
                    st.rerun()

    if submitted:
        _show_grading_screen(
            student, "math", questions, answers, difficulty,
            passage="", expl_cache_key=expl_key
        )
        st.markdown("---")
        if st.button("🔄 새 문제 풀기", use_container_width=True, key=f"math_reset_{student}"):
            for k in [data_key, ans_key, done_key, expl_key]:
                st.session_state.pop(k, None)
            st.rerun()

# ============================================================
#  공통: 문제 렌더링 (퀴즈 화면)
# ============================================================
def _render_question(q: dict, prefix: str, answers: dict, submitted: bool):
    qid = q.get("id", 0)
    with st.container():
        st.markdown(f"**{qid}. {q.get('question', '')}**")
        chosen = st.radio(
            f"q_{prefix}_{qid}",
            q.get("options", []),
            key=f"radio_{prefix}_{qid}",
            label_visibility="collapsed",
            disabled=submitted,
        )
        if chosen:
            answers[qid] = chosen[0]  # 'A' / 'B' / 'C' / 'D'

# ============================================================
#  채점 & 상세 해설 화면 (Grading Screen) ← 핵심 강화 영역
# ============================================================
def _show_grading_screen(
    student: str,
    subject: str,
    questions: list,
    answers: dict,
    difficulty: str,
    passage: str = "",
    expl_cache_key: str = "",
):
    info = STUDENTS[student]

    # ── 1. 채점 계산 ──
    results = []
    for q in questions:
        qid   = q.get("id")
        user  = answers.get(qid, "?")
        corr  = q.get("correct", "")
        results.append({"q": q, "user": user, "correct": corr, "is_ok": user == corr})

    score        = sum(1 for r in results if r["is_ok"])
    wrong_list   = [r for r in results if not r["is_ok"]]
    wrong_concepts = [r["q"].get("concept", "unknown") for r in wrong_list]
    total        = len(results)
    pct          = round(score / total * 100, 1)

    # ── 2. 오답 저장 (Google Sheets / 세션) ──
    for r in wrong_list:
        save_wrong_answer(
            student, subject,
            r["q"].get("question", ""), r["correct"], r["user"],
            r["q"].get("concept", "unknown"), difficulty,
        )

    pts = save_study_record(student, subject, score, total)

    # ── 3. 스코어 헤더 ──
    if pct >= 90:
        grade_color, grade_label = "#22C55E", "🌟 완벽해요! 최고야!"
    elif pct >= 80:
        grade_color, grade_label = "#3B82F6", "😊 훌륭해요! 잘했어!"
    elif pct >= 60:
        grade_color, grade_label = "#F97316", "💪 좋아요! 조금 더 해봐요!"
    else:
        grade_color, grade_label = "#EF4444", "📚 같이 다시 살펴봐요!"

    st.markdown("---")
    st.markdown(
        f"""<div style="text-align:center; padding:28px 20px;
        background:linear-gradient(135deg,{grade_color}25,{grade_color}08);
        border-radius:18px; border:2px solid {grade_color}50; margin-bottom:22px">
        <div style="font-size:4em; font-weight:900; color:{grade_color}; line-height:1">
          {score}<span style="font-size:0.45em; color:#999; font-weight:600">/{total}</span>
        </div>
        <div style="font-size:2em; color:{grade_color}; font-weight:700; margin-top:4px">{pct}%</div>
        <div style="font-size:1.25em; margin-top:8px">{grade_label}</div>
        <div style="font-size:0.95em; color:#777; margin-top:6px">⭐ {pts}점 획득!</div>
        </div>""",
        unsafe_allow_html=True,
    )

    if pct >= 80:
        st.balloons()

    if pct >= 80:
        st.success("🎉 정답률 80% 이상! 다음 세션부터 더 어려운 문제에 도전해요!")

    # ── 4. 20문제 한눈에 보기 (그리드) ──
    st.markdown("### 🗺️ 20문제 결과 한눈에 보기")
    grid = st.columns(10)
    for i, r in enumerate(results):
        col = grid[i % 10]
        if r["is_ok"]:
            col.markdown(
                f"""<div style="text-align:center;background:#DCFCE7;border-radius:8px;
                padding:7px 3px;margin:2px;font-size:0.82em;font-weight:700;color:#16A34A">
                {r['q']['id']}<br>✅</div>""",
                unsafe_allow_html=True,
            )
        else:
            col.markdown(
                f"""<div style="text-align:center;background:#FEE2E2;border-radius:8px;
                padding:7px 3px;margin:2px;font-size:0.82em;font-weight:700;color:#DC2626">
                {r['q']['id']}<br>❌</div>""",
                unsafe_allow_html=True,
            )

    # ── 5. 틀린 문제 상세 해설 ──
    if wrong_list:
        st.markdown(f"### 🔍 틀린 문제 상세 해설 ({len(wrong_list)}개)")
        st.caption("▼ 각 문제를 클릭하면 AI 선생님의 맞춤 해설을 볼 수 있어요!")

        if expl_cache_key not in st.session_state:
            st.session_state[expl_cache_key] = {}
        expl_cache = st.session_state[expl_cache_key]

        for r in wrong_list:
            qid     = r["q"]["id"]
            concept = r["q"].get("concept", "unknown")

            with st.expander(
                f"❌  **{qid}번** — 내 답: {r['user']} | 정답: {r['correct']} | 개념: {concept}",
                expanded=True,
            ):
                # AI 해설 (캐시 우선)
                if qid not in expl_cache:
                    with st.spinner(f"🤖 {student}만을 위한 해설을 생성하고 있어요..."):
                        expl = generate_ai_explanation(
                            student, subject, r["q"], r["user"], passage
                        )
                    expl_cache[qid] = expl
                else:
                    expl = expl_cache[qid]

                # 오류 유형 뱃지
                is_careless = expl.get("error_type", "") == "careless"
                badge_color = "#F97316" if is_careless else "#EF4444"
                badge_text  = expl.get("error_type_ko", "개념부족")
                st.markdown(
                    f"""<span style="background:{badge_color};color:white;padding:3px 10px;
                    border-radius:12px;font-size:0.8em;font-weight:600">⚡ {badge_text}</span>""",
                    unsafe_allow_html=True,
                )
                st.markdown("")

                # 문제 원문
                st.markdown(
                    f"""<div style="background:#F8FAFC;border-radius:8px;padding:10px 14px;
                    margin:8px 0;font-size:0.95em;border-left:3px solid #CBD5E1">
                    📋 <b>문제:</b> {r['q'].get('question', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )

                # 왜 틀렸나
                st.markdown(
                    f"""<div style="background:#FEF2F2;border-radius:8px;padding:10px 14px;
                    margin:8px 0;border-left:3px solid #FCA5A5">
                    🔍 <b>왜 틀렸냐면:</b> {expl.get('why_wrong', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )

                # 단계별 풀이
                st.markdown("**📐 단계별 풀이:**")
                steps = expl.get("steps", [])
                for step in steps:
                    # LaTeX 포함 텍스트는 st.markdown이 $...$를 렌더링
                    st.markdown(f"&nbsp;&nbsp;&nbsp;{step}")

                # 핵심 포인트
                st.markdown(
                    f"""<div style="background:#FFFDE7;border-left:4px solid #FBBF24;
                    padding:11px 16px;border-radius:8px;margin-top:10px;line-height:1.6">
                    💡 <b>핵심 포인트:</b> {expl.get('key_takeaway', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )

                # 격려 메시지
                st.markdown(
                    f"""<div style="background:{info['color']}18;border-radius:8px;
                    padding:10px 16px;margin-top:8px;line-height:1.6">
                    {info['emoji']} <b>{student}에게:</b> {expl.get('encouragement', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )
    else:
        st.success("🎉 틀린 문제가 없어요! 오늘은 완벽한 날이에요!")

    # ── 6. 정답 문제 확인 (접기/펼치기) ──
    with st.expander("✅ 맞힌 문제 확인하기", expanded=False):
        for r in results:
            if r["is_ok"]:
                st.markdown(
                    f"✅ **{r['q']['id']}번 정답!** — {r['q'].get('explanation', '')}"
                )

    # ── 7. 개인화 총평 피드백 ──
    st.markdown("---")
    st.markdown("### 💬 오늘의 총평")
    with st.spinner("🤖 AI가 오늘의 총평을 작성하고 있어요..."):
        feedback = generate_ai_feedback(
            student, subject, score, total, list(set(wrong_concepts))
        )
    st.markdown(
        f"""<div style="background:{info['color']}15; border:2px solid {info['color']}60;
        padding:20px 24px; border-radius:14px; line-height:1.85; font-size:1.02em">
        <b>{info['emoji']} {student}에게 전하는 말</b><br><br>{feedback}
        </div>""",
        unsafe_allow_html=True,
    )

# ============================================================
#  대시보드
# ============================================================
def render_dashboard(student: str):
    info = STUDENTS[student]
    st.markdown(
        f"""<div style="background:linear-gradient(135deg,{info['color']}30,{info['color']}10);
        padding:22px; border-radius:16px; margin-bottom:18px">
        <h2>{info['emoji']} {student}의 학습 대시보드</h2>
        <p style="margin:0;color:#555">{info['style_desc']} 학습자 · NZ Year 5-6</p>
        </div>""",
        unsafe_allow_html=True,
    )

    today = date.today().isoformat()
    today_rec = st.session_state.study_records.get(f"{student}_{today}", {})
    st.markdown("### 📊 오늘의 학습 현황")
    c1, c2 = st.columns(2)
    with c1:
        er = today_rec.get("english")
        if er:
            st.success(f"✅ 영어 완료: {er['score']}/{er['total']} ({er['pct']}%)")
        else:
            st.warning("📖 영어: 아직 안 풀었어요")
    with c2:
        mr = today_rec.get("math")
        if mr:
            st.success(f"✅ 수학 완료: {mr['score']}/{mr['total']} ({mr['pct']}%)")
        else:
            st.warning("🔢 수학: 아직 안 풀었어요")

    st.markdown("---")
    _render_calendar(student)
    st.markdown("---")
    _render_badges(student)
    st.markdown("---")
    _render_stats(student)

def _render_calendar(student: str):
    today = date.today()
    y, m  = today.year, today.month
    cal_data   = calendar.monthcalendar(y, m)
    month_name = today.strftime("%B %Y")

    st.markdown(f"### 📅 {month_name} 학습 캘린더")
    st.caption("✅ 영어+수학 모두 완료 | ⭐ 오늘 | 🔵 영어만 | 🟠 수학만")

    records = st.session_state.study_records
    full_done, eng_done, math_done = set(), set(), set()
    for key, rec in records.items():
        if not key.startswith(student):
            continue
        d     = key[len(student) + 1:]
        has_e = "english" in rec
        has_m = "math" in rec
        if has_e and has_m:
            full_done.add(d)
        elif has_e:
            eng_done.add(d)
        elif has_m:
            math_done.add(d)

    header_cols = st.columns(7)
    for i, d in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        header_cols[i].markdown(f"<center><b>{d}</b></center>", unsafe_allow_html=True)

    for week in cal_data:
        wcols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                wcols[i].markdown(" ")
                continue
            ds = f"{y}-{m:02d}-{day:02d}"
            if ds in full_done:
                icon = "✅"
            elif ds == today.isoformat():
                icon = "⭐"
            elif ds in eng_done:
                icon = "🔵"
            elif ds in math_done:
                icon = "🟠"
            else:
                icon = ""
            wcols[i].markdown(
                f"<div style='text-align:center'>{icon}<br><small>{day}</small></div>",
                unsafe_allow_html=True,
            )

def _render_badges(student: str):
    pts    = st.session_state.points.get(student, 0)
    earned = [b for b in BADGES if pts >= b["points"]]
    nxt    = next((b for b in BADGES if pts < b["points"]), None)

    st.markdown(f"### 🏆 배지 현황 — 총 **{pts}점**")
    if nxt:
        st.progress(min(pts / nxt["points"], 1.0))
        st.caption(f"'{nxt['name']} {nxt['emoji']}' 배지까지 **{nxt['points'] - pts}점** 더 필요해요!")

    if earned:
        st.markdown("#### ✨ 획득한 배지")
        cols = st.columns(min(len(earned), 4))
        for i, b in enumerate(earned):
            with cols[i % 4]:
                st.markdown(
                    f"""<div style="text-align:center;background:#FFF9C4;border-radius:12px;
                    padding:12px;margin:4px">
                    <div style="font-size:2em">{b['emoji']}</div>
                    <div style="font-weight:bold">{b['name']}</div>
                    <div style="font-size:0.75em;color:#777">{b['desc']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
    else:
        st.info("첫 퀴즈를 완료하면 Explorer 🗺️ 배지를 받을 수 있어요!")

    st.markdown("#### 📋 전체 배지 목록")
    cols2 = st.columns(4)
    for i, b in enumerate(BADGES):
        is_e = b in earned
        bg   = "#FFFDE7" if is_e else "#F5F5F5"
        op   = "1.0"     if is_e else "0.35"
        with cols2[i % 4]:
            st.markdown(
                f"""<div style="text-align:center;background:{bg};opacity:{op};
                border-radius:10px;padding:10px;margin:3px">
                <div style="font-size:1.6em">{b['emoji']}</div>
                <div style="font-size:0.82em;font-weight:bold">{b['name']}</div>
                <div style="font-size:0.7em;color:#888">{b['points']}점</div>
                </div>""",
                unsafe_allow_html=True,
            )

def _render_stats(student: str):
    records = st.session_state.study_records
    student_recs = {k: v for k, v in records.items() if k.startswith(student)}
    if not student_recs:
        st.info("아직 학습 기록이 없어요. 퀴즈를 풀어보세요!")
        return

    st.markdown("### 📈 누적 학습 통계")
    eng_scores  = [v["english"]["pct"]  for v in student_recs.values() if "english"  in v]
    math_scores = [v["math"]["pct"]     for v in student_recs.values() if "math"     in v]
    sessions    = len(student_recs)

    c1, c2, c3 = st.columns(3)
    c1.metric("총 학습 세션",  f"{sessions}회")
    c2.metric("영어 평균",   f"{sum(eng_scores)/len(eng_scores):.1f}%"   if eng_scores  else "—")
    c3.metric("수학 평균",   f"{sum(math_scores)/len(math_scores):.1f}%" if math_scores else "—")

    if eng_scores or math_scores:
        chart_data = {}
        if eng_scores:
            chart_data["영어 (%)"]  = eng_scores[-5:]
        if math_scores:
            chart_data["수학 (%)"] = math_scores[-5:]
        max_len = max(len(v) for v in chart_data.values())
        for k in chart_data:
            while len(chart_data[k]) < max_len:
                chart_data[k].insert(0, None)
        st.markdown("**최근 5회 점수 추이**")
        st.line_chart(pd.DataFrame(chart_data))

# ============================================================
#  메인 앱
# ============================================================
def main():
    st.set_page_config(
        page_title="삼둥이 AI 학습앱 🌟",
        page_icon="🌟",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if api_key.strip() in ("", "여기에_키를_넣으세요"):
        st.error(
            "⚠️ **Gemini API 키가 설정되지 않았습니다!**\n\n"
            "`app.py` 상단 `api_key = '...'` 에 실제 키를 입력해주세요.\n\n"
            "**API 키 발급**: https://aistudio.google.com/app/apikey"
        )
        st.stop()

    defaults = {
        "points":        {"시완": 0, "시원": 0, "시호": 0},
        "study_records": {},
        "wrong_log":     [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── 사이드바 ──
    with st.sidebar:
        st.markdown("# 🌟 삼둥이 학습앱")
        st.caption("NZ Year 5-6 | AI 맞춤 학습")
        st.markdown("---")

        st.markdown("### 👦 누구예요?")
        student = st.radio(
            "학생",
            list(STUDENTS.keys()),
            format_func=lambda x: f"{STUDENTS[x]['emoji']} {x}",
            label_visibility="collapsed",
        )
        si = STUDENTS[student]
        st.markdown(
            f"""<div style="background:{si['color']}20;border:1px solid {si['color']};
            padding:10px;border-radius:10px;margin-bottom:8px">
            <b>{si['emoji']} {student}</b> · {si['style_desc']}</div>""",
            unsafe_allow_html=True,
        )
        pts       = st.session_state.points.get(student, 0)
        nxt_badge = next((b for b in BADGES if pts < b["points"]), None)
        st.markdown(f"⭐ **{pts}점** 보유")
        if nxt_badge:
            st.caption(f"다음 배지: {nxt_badge['name']} {nxt_badge['emoji']} ({nxt_badge['points']}점)")

        st.markdown("---")
        st.markdown("### 📚 메뉴")
        menu = st.radio(
            "메뉴",
            ["🏠 대시보드", "📖 영어 퀴즈", "🔢 수학 퀴즈"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.caption("📘 영어: 4000 Essential Words Book 4-5")
        st.caption("📐 수학: NZC Level 4 · 싱가포르 매쓰")
        if not GSHEETS_AVAILABLE:
            st.caption("⚠️ streamlit-gsheets 미설치 → 오답이 세션에만 저장됩니다")

    # ── 메인 콘텐츠 ──
    if menu == "🏠 대시보드":
        render_dashboard(student)
    elif menu == "📖 영어 퀴즈":
        run_english_quiz(student)
    elif menu == "🔢 수학 퀴즈":
        run_math_quiz(student)


if __name__ == "__main__":
    main()
