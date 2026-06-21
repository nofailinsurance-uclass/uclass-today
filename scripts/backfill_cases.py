#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_cases — 유클래스 투데이 일자별 페이지에 발행됐던 보상사례 전체를
case_briefings DB로 역추출·재구축한다. (DB가 비어/오래된 상태를 정정)

- 보상사례 발행 날짜(화/금)별 '정본' 페이지를 content.json pages 맵(없으면 최신 타임스탬프)에서 고름
- 각 페이지의 <section id="section-news"> (보상사례 + 고객 응대 멘트)를 통째 추출 + 구조화 파싱
- vol = 날짜 오름차순(가장 오래된 사례 = vol 1)
- 게이트(insurance_guard) 통과 검사 후 저장. content_index(case)도 재구축.

사용: python3 scripts/backfill_cases.py          # 미리보기(=--dry)
      python3 scripts/backfill_cases.py --commit  # 실제 DB 재구축
"""
import re, os, json, glob, html as ih, sqlite3, sys, argparse
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = "/home/uclass/db/uclass_content.db"
sys.path.insert(0, "/home/uclass/scripts")
try:
    import insurance_guard
except Exception:
    insurance_guard = None

# 검색 키워드 추출용 보험 용어 사전(본문에 등장하면 키워드로 채택)
TERMS = ["실손보험", "실손", "백내장", "입원", "통원", "고지의무", "구두고지", "도수치료",
         "항암", "유방암", "암보험", "양성종양", "질병분류", "교통사고", "향후치료비",
         "교통사고처리지원금", "운전자보험", "자동차보험", "배달", "유상운송", "의료자문",
         "뇌졸중", "케모포트", "간편보험", "하이푸", "HIFU", "자궁근종", "위절제", "위소매절제",
         "비만", "당뇨", "주사", "5세대실손", "약관변경", "분쟁조정", "금융감독원", "보험금거절",
         "면책", "수술비", "경상", "염좌", "고지위반"]


def textof(s):
    return re.sub(r"\s+", " ", ih.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def canonical_pages():
    content = json.load(open(os.path.join(ROOT, "data/content.json"), encoding="utf-8"))
    pages_map = content.get("pages", {})
    cand = defaultdict(list)
    for f in glob.glob(os.path.join(ROOT, "pages/*/**/index.html"), recursive=True) + \
             glob.glob(os.path.join(ROOT, "pages/*/index.html")):
        if "보험 보상 사례" in open(f, encoding="utf-8").read():
            rel = os.path.relpath(f, ROOT).split("/")
            cand[rel[1]].append((rel[2] if len(rel) == 4 else "", f))
    out = {}
    for date in sorted(cand):
        chosen = None
        u = pages_map.get(date)
        if u:
            m = re.search(r"/pages/(.+?)/?$", u)
            lp = os.path.join(ROOT, f"pages/{m.group(1)}/index.html") if m else None
            if lp and os.path.exists(lp) and "보험 보상 사례" in open(lp, encoding="utf-8").read():
                chosen = lp
        if not chosen:
            k = lambda c: (1, int(c[0])) if c[0].isdigit() else (0, 0)
            chosen = sorted(cand[date], key=k)[-1][1]
        out[date] = chosen
    return out


def parse_case(path):
    h = open(path, encoding="utf-8").read()
    sec = re.search(r'(<section[^>]*id="section-news".*?</section>)', h, re.S)
    if not sec:
        return None
    s = sec.group(1)
    title = re.search(r"color:#0025B4[^>]*>([^<]+)<", s)
    title = ih.unescape(title.group(1)).strip() if title else ""
    badge = re.search(r'nfd-brief-case-badge">([^<]*)<', s)
    badge = badge.group(1).strip() if badge else "이번 주 사례"
    blocks = re.findall(
        r'nfd-brief-script-situation">([^<]*)<.*?nfd-brief-script-q">(.*?)</p>(.*?)'
        r'(?=<div class="nfd-brief-script"|<div class="nfd-brief-sec-header"|$)', s, re.S)
    secs = {l.strip(): textof(b) for l, q, b in blocks}
    scripts = [textof(x) for x in re.findall(r'data-copy-id="[^"]*">(.*?)</p>', s, re.S)]
    srcs = [(u, ih.unescape(t)) for u, t in re.findall(r'<a href="([^"]+)"[^>]*>([^<]*)</a>', s)]
    blob = (title + " " + " ".join(secs.values())).lower()
    kws = [t for t in TERMS if t.lower() in blob][:8]
    g = lambda k: secs.get(k, "")
    return dict(
        category=badge, issue=title, title=title,
        summary=g("사건 요약"), dispute=g("쟁점"), result=g("결과"),
        reasoning=g("왜 이렇게 됐나") or g("왜 이렇게 됐을까"),
        action_points=g("설계사가 알아둬야 할 포인트") or g("핵심 요약"),
        customer_scripts=json.dumps(scripts, ensure_ascii=False),
        sources=json.dumps([{"title": t, "url": u} for u, t in srcs], ensure_ascii=False),
        keywords=",".join(kws), html_snippet=s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    pages = canonical_pages()
    rows = []
    for vol, date in enumerate(sorted(pages), 1):
        c = parse_case(pages[date])
        if not c:
            print(f"  ! {date} 추출 실패"); continue
        c["vol"] = vol
        c["published_at"] = date
        rows.append(c)

    print(f"=== 추출 {len(rows)}건 ===")
    for c in rows:
        sev = "?"
        if insurance_guard:
            v = insurance_guard.check_case_fields(c)
            sev = v["severity"]
        print(f"vol{c['vol']:2} {c['published_at']} [게이트:{sev}] kw={c['keywords'][:40]} | {c['title'][:40]}")

    if not args.commit:
        print("\n(미리보기 — 실제 반영하려면 --commit)")
        return

    import shutil, datetime
    bak = DB + ".bak-backfill"
    shutil.copy(DB, bak)
    print(f"\nDB 백업: {bak}")
    con = sqlite3.connect(DB)
    # 기존 case 인덱스 + case_briefings 제거 후 재구축
    ids = [r[0] for r in con.execute("SELECT id FROM case_briefings")]
    for cid in ids:
        con.execute("DELETE FROM content_index WHERE content_type='case' AND content_id=?", (cid,))
    con.execute("DELETE FROM case_briefings")
    con.execute("DELETE FROM sqlite_sequence WHERE name='case_briefings'")
    cols = ["vol", "published_at", "category", "issue", "title", "summary", "dispute",
            "result", "reasoning", "action_points", "customer_scripts", "sources",
            "keywords", "html_snippet", "review_status", "review_notes"]
    for c in rows:
        sev = "ok"; notes = "{}"
        if insurance_guard:
            v = insurance_guard.check_case_fields(c)
            sev = {"block": "blocked", "warn": "flagged", "ok": "ok"}[v["severity"]]
            notes = json.dumps({"severity": v["severity"],
                                "violations": v.get("violations", []),
                                "source": "backfill"}, ensure_ascii=False)
        c["review_status"] = sev; c["review_notes"] = notes
        con.execute(f"INSERT INTO case_briefings ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                    [c[k] for k in cols])
        cid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("INSERT INTO content_index (content_type,content_id,published_at,title,full_text,keywords)"
                    " VALUES ('case',?,?,?,?,?)",
                    (cid, c["published_at"], c["title"],
                     f"{c['summary']} {c['dispute']} {c['result']} {c['reasoning']}", c["keywords"]))
    con.commit()
    print(f"재구축 완료: {con.execute('SELECT COUNT(*) FROM case_briefings').fetchone()[0]}건")


if __name__ == "__main__":
    main()
