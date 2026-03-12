"""
삼둥이 AI 학습앱 — 퀴즈 플로우 테스트 에이전트
=====================================================
영어/수학 퀴즈의 제출→채점 흐름을 Streamlit 없이 시뮬레이션합니다.
파일 기반 퍼시스턴스(hot-reload 대응) 로직도 검증합니다.
문제가 발견되면 명확한 설명과 함께 출력합니다.

실행: python test_quiz_flow.py
"""

import re
import sys
import json
import os
import tempfile
import random
from copy import deepcopy

# Windows 터미널 인코딩 UTF-8 강제
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# ──────────────────────────────────────────────────────────────
#  Streamlit session_state 모의 객체
# ──────────────────────────────────────────────────────────────
class MockSessionState(dict):
    """st.session_state처럼 dict 접근과 속성 접근을 모두 지원"""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def get(self, key, default=None):
        return super().get(key, default)

    def pop(self, key, *args):
        return super().pop(key, *args)


# ──────────────────────────────────────────────────────────────
#  테스트용 더미 데이터 생성
# ──────────────────────────────────────────────────────────────
def _make_dummy_eng_questions(n=20):
    """영어 퀴즈 더미 데이터 (20문제)"""
    questions = []
    for i in range(1, n + 1):
        q_type = "comprehension" if i <= 8 else "vocabulary"
        questions.append({
            "id": i,
            "type": q_type,
            "question": f"Question {i}?",
            "options": [f"A) Option A{i}", f"B) Option B{i}", f"C) Option C{i}", f"D) Option D{i}"],
            "correct": "A",
            "concept": "main_idea" if q_type == "comprehension" else "context_clue",
            "explanation": f"Explanation for Q{i}",
        })
    return {
        "passage_title": "Test Passage",
        "passage": "This is a test passage about testing.",
        "grammar_focus": {"title": "테스트", "point": "테스트 포인트", "examples": []},
        "key_words": [],
        "questions": questions,
    }


# ──────────────────────────────────────────────────────────────
#  app.py에서 순수 로직 함수들을 인라인으로 복제 (import 없이 테스트)
# ──────────────────────────────────────────────────────────────
def _collect_answers(questions, prefix, session_state):
    """app.py의 _collect_answers 로직 복제"""
    answers = {}
    for q in questions:
        qid = q.get("id", 0)
        val = session_state.get(f"radio_{prefix}_{qid}")
        if val is None:
            continue
        opts = q.get("options", [])
        try:
            idx = opts.index(val)
            answers[qid] = chr(ord("A") + idx)
        except ValueError:
            m = re.search(r"[A-D]", str(val)[:5])
            if m:
                answers[qid] = m.group(0).upper()
    return answers


def _extract_correct(q):
    """app.py의 _extract_correct 로직 복제"""
    raw = (q.get("correct") or "").strip().upper()
    m = re.search(r"[A-D]", raw[:15])
    return m.group(0) if m else ""


# ──────────────────────────────────────────────────────────────
#  테스트 케이스
# ──────────────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f"\n         → {detail}" if detail else ""))
    return condition


# ──────────────────────────────────────────────────────────────
#  테스트 1: 정상 제출 플로우
# ──────────────────────────────────────────────────────────────
def test_normal_submission():
    print("\n[테스트 1] 정상 제출 플로우 (모든 문제 답함)")
    ss = MockSessionState()
    student = "Siwan"
    data_key = f"eng_data_{student}"
    ans_key = f"eng_ans_{student}"
    done_key = f"eng_done_{student}"
    rendered_key = f"eng_rendered_{student}"
    missing_key = f"eng_missing_{student}"
    prefix = f"eng_{student}"

    # Step 1: 데이터 초기화
    data = _make_dummy_eng_questions(20)
    ss[data_key] = data
    ss[ans_key] = {}
    ss[done_key] = False

    # Step 2: 문제 분류 (app.py 로직 복제)
    questions = data["questions"]
    comp_qs = [q for q in questions if q.get("type") == "comprehension"][:10]
    vocab_qs = [q for q in questions if q.get("type") != "comprehension"][:10]
    remaining = [q for q in questions if q not in comp_qs and q not in vocab_qs]
    need_comp = max(0, 10 - len(comp_qs))
    comp_qs += remaining[:need_comp]
    need_vocab = max(0, 10 - len(vocab_qs))
    vocab_qs += remaining[need_comp:need_comp + need_vocab]
    rendered_qs = comp_qs + vocab_qs

    check("rendered_qs 총 20문제", len(rendered_qs) == 20,
          f"실제: {len(rendered_qs)}문제")
    check("rendered_qs 중복 없음",
          len({q['id'] for q in rendered_qs}) == len(rendered_qs),
          f"ID 목록: {[q['id'] for q in rendered_qs]}")

    # Step 3: 모든 문제에 답 선택 (라디오 버튼 시뮬레이션)
    for q in rendered_qs:
        ss[f"radio_{prefix}_{q['id']}"] = q["options"][0]  # A 선택

    # Step 4: 제출 처리
    collected = _collect_answers(rendered_qs, prefix, ss)
    missing = [q.get("id", "?") for q in rendered_qs if q.get("id") not in collected]

    check("모든 답 수집됨 (missing=[])", len(missing) == 0,
          f"미답: {missing}")
    check("collected 20개", len(collected) == 20,
          f"실제: {len(collected)}개")

    # Step 5: 세션 상태 업데이트
    if not missing:
        ss[ans_key] = collected
        ss[rendered_key] = [q.get("id") for q in rendered_qs]
        ss[done_key] = True

    # Step 6: rerun 시뮬레이션 — 채점 화면 진입 조건 확인
    check("done_key=True", ss.get(done_key) is True)
    check("ans_key 비어있지 않음", bool(ss.get(ans_key)))

    # Step 7: 채점 로직 확인
    answers_for_grading = ss.get(ans_key, {})
    rendered_ids = ss.get(rendered_key, [])
    qs_to_grade = [q for q in questions if q.get("id") in rendered_ids] if rendered_ids else questions

    grading_results = []
    for q in qs_to_grade:
        qid = q.get("id")
        if qid not in answers_for_grading:
            continue
        user = answers_for_grading[qid]
        corr = _extract_correct(q)
        grading_results.append({"qid": qid, "user": user, "correct": corr,
                                 "is_ok": bool(user) and bool(corr) and user == corr})

    check("채점 결과 20문제", len(grading_results) == 20,
          f"실제: {len(grading_results)}문제")
    check("모두 정답 (A 선택 = A 정답)", all(r["is_ok"] for r in grading_results))


# ──────────────────────────────────────────────────────────────
#  테스트 2: 일부 문제 미답 시 플로우
# ──────────────────────────────────────────────────────────────
def test_partial_submission():
    print("\n[테스트 2] 일부 문제 미답 제출 (missing 경고 플로우)")
    ss = MockSessionState()
    student = "Siwon"
    data_key = f"eng_data_{student}"
    ans_key = f"eng_ans_{student}"
    done_key = f"eng_done_{student}"
    missing_key = f"eng_missing_{student}"
    prefix = f"eng_{student}"

    data = _make_dummy_eng_questions(20)
    ss[data_key] = data
    ss[ans_key] = {}
    ss[done_key] = False

    questions = data["questions"]
    comp_qs = [q for q in questions if q.get("type") == "comprehension"][:10]
    vocab_qs = [q for q in questions if q.get("type") != "comprehension"][:10]
    rendered_qs = comp_qs + vocab_qs

    # 처음 15문제만 답함 (5문제 미답)
    for q in rendered_qs[:15]:
        ss[f"radio_{prefix}_{q['id']}"] = q["options"][1]  # B 선택

    collected = _collect_answers(rendered_qs, prefix, ss)
    missing = [q.get("id", "?") for q in rendered_qs if q.get("id") not in collected]

    check("미답 문제 감지됨 (1개 이상)",
          len(missing) > 0, f"미답 IDs: {missing}")

    # 수정된 플로우: missing을 session_state에 저장하고 rerun (경고 표시용)
    if missing:
        ss[missing_key] = missing
        # done_key는 True로 설정하지 않음

    check("done_key=False 유지 (채점 미진행)", ss.get(done_key) is False)
    check("missing_key 저장됨 (rerun 후 표시 가능)", bool(ss.get(missing_key)))
    check("ans_key 비어있음 (채점 데이터 없음)", not bool(ss.get(ans_key)))

    # rerun 후 missing 경고 표시 시뮬레이션
    if ss.get(missing_key):
        missing_str = ', '.join(str(m) for m in ss[missing_key])
        check("경고 메시지 생성 가능", bool(missing_str),
              f"미답 번호: {missing_str}번")


# ──────────────────────────────────────────────────────────────
#  테스트 3: ans_key 비어있을 때 방어 코드
# ──────────────────────────────────────────────────────────────
def test_empty_answers_defense():
    print("\n[테스트 3] ans_key 비어있을 때 방어 로직")
    ss = MockSessionState()
    student = "Siho"
    ans_key = f"eng_ans_{student}"
    done_key = f"eng_done_{student}"

    # 비정상 상태: done_key=True지만 ans_key 없음
    ss[done_key] = True
    # ans_key는 설정하지 않음

    answers = ss.get(ans_key, {})
    check("answers 빈 dict 반환 (KeyError 없음)", answers == {},
          f"실제: {answers}")
    check("방어 코드 분기: not answers=True", not answers,
          "채점 시도하지 않고 에러 메시지 표시해야 함")


# ──────────────────────────────────────────────────────────────
#  테스트 4: rendered_key 없을 때 폴백
# ──────────────────────────────────────────────────────────────
def test_rendered_key_fallback():
    print("\n[테스트 4] rendered_key 없을 때 폴백 (전체 questions 사용)")
    ss = MockSessionState()
    student = "Siwan"
    rendered_key = f"eng_rendered_{student}"

    data = _make_dummy_eng_questions(20)
    questions = data["questions"]

    # rendered_key 없는 경우
    rendered_ids = ss.get(rendered_key, [])
    qs_to_grade = [q for q in questions if q.get("id") in rendered_ids] if rendered_ids else questions

    check("rendered_key 없으면 전체 questions 사용", len(qs_to_grade) == 20,
          f"실제: {len(qs_to_grade)}문제")


# ──────────────────────────────────────────────────────────────
#  테스트 5: _extract_correct 엣지 케이스
# ──────────────────────────────────────────────────────────────
def test_extract_correct():
    print("\n[테스트 5] _extract_correct 정답 정규화")
    cases = [
        ({"correct": "A"}, "A"),
        ({"correct": "B) Option B"}, "B"),
        ({"correct": "correct answer is C"}, "C"),
        ({"correct": ""}, ""),
        ({"correct": None}, ""),
        ({}, ""),
    ]
    for q, expected in cases:
        result = _extract_correct(q)
        check(f"correct={q.get('correct')!r} → '{expected}'",
              result == expected, f"실제: '{result}'")


# ──────────────────────────────────────────────────────────────
#  테스트 6: 새 문제 풀기 클린업
# ──────────────────────────────────────────────────────────────
def test_reset_cleanup():
    print("\n[테스트 6] '새 문제 풀기' 클린업 완전성")
    ss = MockSessionState()
    student = "Siwan"
    prefix = f"eng_{student}"

    # 퀴즈 완료 상태 설정
    ss[f"eng_data_{student}"] = {"questions": []}
    ss[f"eng_ans_{student}"] = {1: "A", 2: "B"}
    ss[f"eng_done_{student}"] = True
    ss[f"eng_rendered_{student}"] = [1, 2]
    ss[f"eng_missing_{student}"] = []
    ss[f"explanations_english_{student}"] = {}
    ss[f"record_done_explanations_english_{student}"] = True
    ss[f"ai_feedback_explanations_english_{student}"] = "Great job!"
    # 라디오 버튼 상태
    for i in range(1, 21):
        ss[f"radio_{prefix}_{i}"] = f"A) Option A{i}"

    # 클린업 실행 (app.py 로직 복제)
    expl_key = f"explanations_english_{student}"
    data_key = f"eng_data_{student}"
    ans_key = f"eng_ans_{student}"
    done_key = f"eng_done_{student}"
    rendered_key = f"eng_rendered_{student}"
    missing_key = f"eng_missing_{student}"

    for k in [data_key, ans_key, done_key, expl_key, rendered_key, missing_key,
              f"record_done_{expl_key}", f"ai_feedback_{expl_key}"]:
        ss.pop(k, None)
    for k in list(ss.keys()):
        if k.startswith(f"radio_{prefix}_"):
            del ss[k]

    check("data_key 삭제됨", data_key not in ss)
    check("ans_key 삭제됨", ans_key not in ss)
    check("done_key 삭제됨", done_key not in ss)
    check("missing_key 삭제됨", missing_key not in ss)
    check("라디오 키 모두 삭제됨",
          not any(k.startswith(f"radio_{prefix}_") for k in ss.keys()),
          f"남은 라디오 키: {[k for k in ss.keys() if k.startswith(f'radio_{prefix}_')]}")
    check("세션 스테이트 완전히 비워짐", len(ss) == 0,
          f"남은 키: {list(ss.keys())}")


# ──────────────────────────────────────────────────────────────
#  메인 실행
# ──────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────
#  테스트 7: session_state 유실 후 공유스토어에서 복구
# ──────────────────────────────────────────────────────────────
def test_shared_store_restore():
    print("\n[테스트 7] session_state 유실 후 공유 스토어 복구")
    student = "Siwan"
    data_key    = f"math_data_{student}"
    ans_key     = f"math_ans_{student}"
    done_key    = f"math_done_{student}"
    plan_key    = f"math_plan_{student}"
    pending_key = f"math_pending_{student}"

    # 공유스토어 시뮬레이션
    shared_store = {}

    # 제출 당시: 공유스토어에 백업 저장
    dummy_data = {"questions": [{"id": i+1, "question": f"Q{i+1}", "options": ["A","B","C","D"], "correct": "A"} for i in range(20)]}
    dummy_answers = {i+1: "A" for i in range(20)}
    dummy_plan = {"current_level": 1}
    shared_store[pending_key] = {
        "data":    dummy_data,
        "answers": dummy_answers,
        "plan":    dummy_plan,
    }

    # session_state 유실 시뮬레이션: 완전히 새로운 session_state
    ss = MockSessionState()
    check("session_state 비어있음 (유실 시뮬레이션)", done_key not in ss)

    # 복구 로직 (app.py 로직 복제)
    if pending_key in shared_store and not ss.get(done_key, False):
        _mp = shared_store[pending_key]
        ss[data_key] = _mp["data"]
        ss[ans_key]  = _mp["answers"]
        ss[plan_key] = _mp["plan"]
        ss[done_key] = True

    check("공유스토어에서 done_key 복구됨", ss.get(done_key) is True)
    check("공유스토어에서 ans_key 복구됨", len(ss.get(ans_key, {})) == 20)
    check("공유스토어에서 data_key 복구됨", bool(ss.get(data_key)))
    check("공유스토어에서 plan_key 복구됨", bool(ss.get(plan_key)))

    # 복구 후 채점 화면으로 진입 가능한지 확인
    _data     = ss.get(data_key, {})
    _answers  = ss.get(ans_key, {})
    _questions = _data.get("questions", [])
    check("채점 가능: questions 있음", len(_questions) == 20)
    check("채점 가능: answers 있음", len(_answers) == 20)


# ──────────────────────────────────────────────────────────────
#  테스트 8: 리셋 시 공유스토어 pending 삭제
# ──────────────────────────────────────────────────────────────
def test_shared_store_reset_cleanup():
    print("\n[테스트 8] '새 문제 풀기' 시 공유스토어 pending 삭제")
    student = "Siwon"
    pending_key = f"math_pending_{student}"

    shared_store = {
        pending_key: {"data": {}, "answers": {}, "plan": {}},
    }

    check("리셋 전: pending 존재", pending_key in shared_store)

    # 리셋 실행 (app.py 로직 복제)
    shared_store.pop(pending_key, None)

    check("리셋 후: pending 삭제됨", pending_key not in shared_store)
    check("리셋 후: 스토어 비어있음", len(shared_store) == 0)

# ──────────────────────────────────────────────────────────────
#  테스트 9: 파일 퍼시스턴스 — 저장/로드/삭제
# ──────────────────────────────────────────────────────────────
def test_file_persistence():
    print("\n[테스트 9] 파일 퍼시스턴스 (hot-reload 대응)")
    # 임시 파일 사용
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
    tmp.write("{}")
    tmp.close()
    persist_file = tmp.name

    def _file_load_all():
        try:
            if os.path.exists(persist_file):
                with open(persist_file, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _file_save_pending(key, value):
        try:
            state = _file_load_all()
            state[key] = value
            with open(persist_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, default=str)
        except Exception:
            pass

    def _file_delete_pending(key):
        try:
            state = _file_load_all()
            if key in state:
                state.pop(key)
                with open(persist_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False, default=str)
        except Exception:
            pass

    try:
        # 저장 테스트
        _file_save_pending("eng_pending_Siwan", {"data": {"q": 1}, "answers": {1: "A"}})
        loaded = _file_load_all()
        check("파일 저장 후 로드 가능", "eng_pending_Siwan" in loaded)
        check("파일 저장 데이터 정확성", loaded.get("eng_pending_Siwan", {}).get("answers", {}).get("1") == "A",
              f"실제: {loaded.get('eng_pending_Siwan', {})}")

        # 두 번째 키 저장 (기존 키 덮어쓰지 않음)
        _file_save_pending("math_pending_Siho", {"data": {}, "answers": {}, "plan": {}})
        loaded = _file_load_all()
        check("두 키 동시 존재", "eng_pending_Siwan" in loaded and "math_pending_Siho" in loaded,
              f"키 목록: {list(loaded.keys())}")

        # 삭제 테스트
        _file_delete_pending("eng_pending_Siwan")
        loaded = _file_load_all()
        check("파일 삭제 후 키 없음", "eng_pending_Siwan" not in loaded)
        check("다른 키 유지됨", "math_pending_Siho" in loaded)

        # hot-reload 시나리오: 서버 재시작 후 파일에서 복구
        # 새 메모리 스토어 생성 + 파일에서 로드
        new_store = {"points": {}, "study_records": {}, "math_mastery": {}}
        for k, v in _file_load_all().items():
            new_store[k] = v
        check("hot-reload 후 스토어 복구됨", "math_pending_Siho" in new_store,
              f"스토어 키: {list(new_store.keys())}")

    finally:
        os.unlink(persist_file)


# ──────────────────────────────────────────────────────────────
#  테스트 10: option-text 비교 채점 (AI 레이블 불일치 대응)
# ──────────────────────────────────────────────────────────────
def test_option_text_grading():
    print("\n[테스트 10] option-text 비교 채점 (AI correct 레이블 불일치 대응)")

    def _letter_to_opt(letter, opts):
        if not letter or not opts:
            return ""
        idx = ord(letter) - ord("A")
        return opts[idx] if 0 <= idx < len(opts) else ""

    def grade(user_letter, corr_letter, opts):
        user_opt = _letter_to_opt(user_letter, opts)
        corr_opt = _letter_to_opt(corr_letter, opts)
        if user_opt and corr_opt:
            return user_opt.strip().upper() == corr_opt.strip().upper()
        return bool(user_letter) and bool(corr_letter) and user_letter == corr_letter

    opts = ["12", "24", "36", "48"]

    # 정상: 정답=A, 선택=A → 정답
    check("정상: 정답A=선택A → 정답", grade("A", "A", opts))
    # 정상: 정답=A, 선택=B → 오답
    check("정상: 정답A=선택B → 오답", not grade("B", "A", opts))

    # AI 불일치 시나리오: correct="C"라고 했지만 실제 정답 텍스트는 options[0]("12")에 있는 경우
    # AI가 options=[24,12,36,48]로 잘못 배치한 케이스 → 텍스트 비교라면 같은 값이면 정답
    opts_mismatch = ["24", "12", "36", "48"]  # 올바른 답 "12"가 B 위치
    # correct="A"(24)지만 user는 "B"(12)를 선택 — 실제 정답은 "12"
    # 텍스트 비교: user_opt="12", corr_opt="24" → 오답 (올바른 판정)
    check("텍스트비교: 선택B(12) vs AI정답A(24) → 오답", not grade("B", "A", opts_mismatch))
    # AI가 correct="B"로 제대로 설정한 경우: user=B(12) vs correct=B(12) → 정답
    check("텍스트비교: 선택B(12) vs 정답B(12) → 정답", grade("B", "B", opts_mismatch))

    # 빈 옵션 폴백
    check("빈 opts 폴백: 레터 비교", grade("A", "A", []))
    check("빈 opts 폴백: 오답", not grade("A", "B", []))


if __name__ == "__main__":
    print("=" * 60)
    print("  삼둥이 AI 학습앱 퀴즈 플로우 테스트")
    print("=" * 60)

    test_normal_submission()
    test_partial_submission()
    test_empty_answers_defense()
    test_rendered_key_fallback()
    test_extract_correct()
    test_reset_cleanup()
    test_shared_store_restore()
    test_shared_store_reset_cleanup()
    test_file_persistence()
    test_option_text_grading()

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    print(f"  결과: {passed}개 통과 / {failed}개 실패 (총 {len(results)}개)")
    if failed:
        print("\n  실패한 테스트:")
        for status, name, detail in results:
            if status == FAIL:
                print(f"    ❌ {name}")
                if detail:
                    print(f"       {detail}")
        sys.exit(1)
    else:
        print("  모든 테스트 통과! ✅")
    print("=" * 60)
