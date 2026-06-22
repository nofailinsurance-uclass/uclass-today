#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보상사례(case_briefings) → cases/ 정적 페이지 생성기.
DB(uclass_content.db)를 단일 소스로 읽어
  - cases/index.html         (목록 + 검색 + 20개 페이징 + 이전/다음 화살표)
  - cases/<vol>/index.html   (개별 상세, 기존 UCLASS TODAY 톤앤매너)
를 생성한다. 사례가 추가되면 이 스크립트만 다시 실행하면 된다.
"""
import os, re, html as ihtml, sqlite3, datetime

DB   = "/home/uclass/db/uclass_content.db"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES_DIR = os.path.join(ROOT, "cases")
CSS_HREF  = "/assets/css/nfd-brief.css"
FONT = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'

COPY_SVG = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" '
            'width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>')


def esc(s):
    return ihtml.escape(s or "", quote=True)


def fmt_dates(d):
    y, m, day = d.split("-")
    return f"{y}.{m}.{day}", f"{y}년 {int(m)}월 {int(day)}일"


def load_cases():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    # review_status='blocked' 인 건은 발행 대상에서 제외 (게이트 차단 / 검수대기)
    has_review = any(r[1] == "review_status"
                     for r in con.execute("PRAGMA table_info(case_briefings)"))
    where = "WHERE COALESCE(review_status,'ok') <> 'blocked'" if has_review else ""
    rows = con.execute(
        "SELECT vol, published_at, category, title, summary, keywords, html_snippet "
        f"FROM case_briefings {where} ORDER BY vol DESC").fetchall()
    return [dict(r) for r in rows]


# ---------- 복사/애니메이션 공통 스크립트 (base.html에서 가져옴) ----------
COMMON_JS = r"""
<script>
(function(){
  var animEls=document.querySelectorAll('.nfd-brief-anim-text');
  if(animEls.length && 'IntersectionObserver' in window){
    var ob=new IntersectionObserver(function(es){es.forEach(function(e){
      if(e.isIntersecting){var i=Array.prototype.indexOf.call(animEls,e.target);
        setTimeout(function(){e.target.classList.add('nfd-brief-visible');},i*70);ob.unobserve(e.target);}});},
      {threshold:0.1,rootMargin:'0px 0px -30px 0px'});
    animEls.forEach(function(el){ob.observe(el);});
  } else { animEls.forEach(function(el){el.classList.add('nfd-brief-visible');}); }
})();
document.querySelectorAll('.nfd-brief-copy-btn').forEach(function(btn){
  btn.addEventListener('click',function(){
    var id=btn.getAttribute('data-copy-target');
    var src=document.querySelector('[data-copy-id="'+id+'"]'); if(!src)return;
    var tmp=document.createElement('div');
    tmp.innerHTML=src.innerHTML.replace(/<br\s*\/?>(?=)/gi,'\n').replace(/<strong[^>]*>(.*?)<\/strong>/gi,'$1').replace(/<[^>]+>/g,'');
    var text=(tmp.textContent||tmp.innerText||'').replace(/\n{3,}/g,'\n\n').trim();
    var ok='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    var cp='""" + COPY_SVG.replace('"', '\\"') + r"""';
    function done(){var o=btn.innerHTML;btn.classList.add('copied');btn.innerHTML=ok+' 복사됐어요!';
      setTimeout(function(){btn.classList.remove('copied');btn.innerHTML=cp+' 복사하기';},2000);}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done).catch(function(){fb(text);done();});}
    else{fb(text);done();}
    function fb(t){var ta=document.createElement('textarea');ta.value=t;ta.style.cssText='position:fixed;top:0;left:0;opacity:0';
      document.body.appendChild(ta);ta.focus();ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);}
  });
});

/* iframe 임베딩 시 부모창에 콘텐츠 높이 전달(모바일 높이 자동조절) */
(function(){
  if(window.parent === window) return;            // iframe 안일 때만
  var last = 0;
  function postHeight(){
    var h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight,
                     document.body.offsetHeight, document.documentElement.offsetHeight);
    if(Math.abs(h - last) < 4) return;            // 미세 변동 무시
    last = h;
    try{ window.parent.postMessage({type:'uclass-cases-height', height:h}, '*'); }catch(e){}
  }
  window.addEventListener('load', postHeight);
  window.addEventListener('resize', postHeight);
  if('ResizeObserver' in window){ new ResizeObserver(postHeight).observe(document.body); }
  // 검색/페이징/네비게이션 후 반영 보강
  document.addEventListener('click', function(){ setTimeout(postHeight, 60); });
  [120, 400, 1000].forEach(function(t){ setTimeout(postHeight, t); });
})();
</script>
"""


# ================= 상세 페이지 =================
def build_detail(case, prev_vol, next_vol):
    short, full = fmt_dates(case["published_at"])
    vol = case["vol"]
    # html_snippet 의 섹션 id(section-news)는 페이지 내 1개뿐이라 그대로 사용
    snippet = case["html_snippet"]

    prev_link = (f'<a class="nfd-case-pn nfd-case-pn--prev" href="/cases/{prev_vol}/">'
                 f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>'
                 f'<span>이전 사례</span></a>') if prev_vol else \
                '<span class="nfd-case-pn nfd-case-pn--disabled"></span>'
    next_link = (f'<a class="nfd-case-pn nfd-case-pn--next" href="/cases/{next_vol}/">'
                 f'<span>다음 사례</span>'
                 f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg></a>') if next_vol else \
                '<span class="nfd-case-pn nfd-case-pn--disabled"></span>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>보상사례 Vol.{vol} — {esc(case['title'])} | UCLASS TODAY</title>
<meta name="description" content="{esc(case['summary'][:120])}">
<meta property="og:title" content="보상사례 Vol.{vol} | UCLASS TODAY">
<meta property="og:description" content="{esc(case['summary'][:120])}">
<link rel="stylesheet" href="{CSS_HREF}">
{FONT}
{LIST_DETAIL_CSS}
</head>
<body style="margin:0;padding:0;background:#fff;">
<div class="nfd-brief nfd-case-detail">

  <section class="nfd-brief-hero nfd-case-hero">
    <div class="nfd-brief-hero-video-wrap"></div>
    <div class="nfd-brief-hero-container">
      <div class="nfd-brief-hero-content">
        <span class="nfd-case-hero-badge nfd-brief-anim-text">⚖️ 보상사례 Vol.{vol}</span>
        <h1 class="nfd-brief-hero-heading nfd-brief-anim-text nfd-case-hero-title">{esc(case['title'])}</h1>
        <p class="nfd-brief-hero-desc nfd-brief-anim-text">{full} · 유클래스랩</p>
      </div>
    </div>
  </section>

{snippet}

  <nav class="nfd-case-pn-bar">
    {prev_link}
    <a class="nfd-case-pn nfd-case-pn--list" href="/cases/">목록</a>
    {next_link}
  </nav>

</div>
{COMMON_JS}
</body>
</html>"""


# ================= 목록 페이지 =================
def build_list(cases):
    cards = []
    for c in cases:
        short, full = fmt_dates(c["published_at"])
        kws = [k.strip() for k in (c["keywords"] or "").split(",") if k.strip()]
        kw_html = "".join(f'<span class="nfd-case-tag">#{esc(k)}</span>' for k in kws[:6])
        search_blob = esc(" ".join([c["title"], c["summary"], c["keywords"] or ""]).lower())
        summary = esc((c["summary"] or "")[:120]) + ("…" if len(c["summary"] or "") > 120 else "")
        cards.append(f"""
      <a class="nfd-case-card nfd-brief-anim-text" href="/cases/{c['vol']}/" data-search="{search_blob}">
        <div class="nfd-case-card-top">
          <span class="nfd-case-card-badge">⚖️ Vol.{c['vol']}</span>
          <span class="nfd-case-card-date">{short}</span>
        </div>
        <h3 class="nfd-case-card-title">{esc(c['title'])}</h3>
        <p class="nfd-case-card-summary">{summary}</p>
        <div class="nfd-case-card-tags">{kw_html}</div>
        <span class="nfd-case-card-more">자세히 보기
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </span>
      </a>""")
    cards_html = "".join(cards)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>보상사례 브리핑 모아보기 | UCLASS TODAY</title>
<meta name="description" content="현장 설계사를 위한 보험 보상사례 브리핑 — 분쟁·판례·고객 응대 스크립트를 한곳에서.">
<link rel="stylesheet" href="{CSS_HREF}">
{FONT}
{LIST_DETAIL_CSS}
</head>
<body style="margin:0;padding:0;background:transparent;">
<div class="nfd-brief">

  <section class="nfd-brief-sec nfd-brief-sec--gray nfd-case-listsec">
    <div class="nfd-brief-sec-container">

      <div class="nfd-case-search">
        <svg class="nfd-case-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8a93a6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input id="caseSearch" type="search" placeholder="사례 제목·키워드로 검색 (예: 고지의무, 배달, 자동차보험)" autocomplete="off">
        <button id="caseSearchClear" type="button" aria-label="지우기" hidden>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <p class="nfd-case-count" id="caseCount"></p>

      <div class="nfd-case-grid" id="caseGrid">{cards_html}
      </div>

      <p class="nfd-case-empty" id="caseEmpty" hidden>검색 결과가 없어요. 다른 키워드로 찾아보세요.</p>

      <div class="nfd-case-pager" id="casePager"></div>

    </div>
  </section>

</div>

<script>
(function(){{
  var PER_PAGE=20;
  var grid=document.getElementById('caseGrid');
  var cards=Array.prototype.slice.call(grid.querySelectorAll('.nfd-case-card'));
  var search=document.getElementById('caseSearch');
  var clearBtn=document.getElementById('caseSearchClear');
  var pager=document.getElementById('casePager');
  var countEl=document.getElementById('caseCount');
  var emptyEl=document.getElementById('caseEmpty');
  var page=1, filtered=cards.slice();

  function applyFilter(){{
    var q=(search.value||'').trim().toLowerCase();
    clearBtn.hidden = !q;
    filtered = q ? cards.filter(function(c){{return c.getAttribute('data-search').indexOf(q)!==-1;}}) : cards.slice();
    page=1; render();
  }}

  function render(){{
    var total=filtered.length;
    var pages=Math.max(1, Math.ceil(total/PER_PAGE));
    if(page>pages) page=pages;
    cards.forEach(function(c){{c.style.display='none';}});
    var start=(page-1)*PER_PAGE;
    filtered.slice(start, start+PER_PAGE).forEach(function(c){{c.style.display='';}});
    emptyEl.hidden = total!==0;
    grid.style.display = total===0 ? 'none' : '';
    countEl.textContent = total===0 ? '' : ('총 '+total+'건'+(pages>1?(' · '+page+'/'+pages+' 페이지'):''));
    renderPager(pages);
  }}

  function btn(label, target, opts){{
    opts=opts||{{}};
    var b=document.createElement('button');
    b.type='button';
    b.className='nfd-case-page-btn'+(opts.cls?(' '+opts.cls):'')+(opts.active?' is-active':'');
    b.innerHTML=label;
    if(opts.disabled){{b.disabled=true;}}
    else{{b.addEventListener('click',function(){{page=target;render();window.scrollTo({{top:grid.offsetTop-100,behavior:'smooth'}});}});}}
    return b;
  }}

  function renderPager(pages){{
    pager.innerHTML='';
    if(filtered.length===0){{return;}}
    var L='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>';
    var R='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';
    pager.appendChild(btn(L, page-1, {{cls:'nfd-case-page-arrow', disabled:page<=1}}));
    // 페이지 번호 (현재 기준 최대 5개 창)
    var win=5, half=Math.floor(win/2);
    var s=Math.max(1, page-half), e=Math.min(pages, s+win-1);
    s=Math.max(1, Math.min(s, e-win+1));
    if(s>1){{pager.appendChild(btn('1',1,{{}}));
      if(s>2){{var d=document.createElement('span');d.className='nfd-case-page-dots';d.textContent='…';pager.appendChild(d);}}}}
    for(var i=s;i<=e;i++){{pager.appendChild(btn(String(i), i, {{active:i===page}}));}}
    if(e<pages){{if(e<pages-1){{var d2=document.createElement('span');d2.className='nfd-case-page-dots';d2.textContent='…';pager.appendChild(d2);}}
      pager.appendChild(btn(String(pages), pages, {{}}));}}
    pager.appendChild(btn(R, page+1, {{cls:'nfd-case-page-arrow', disabled:page>=pages}}));
  }}

  search.addEventListener('input', applyFilter);
  clearBtn.addEventListener('click', function(){{search.value='';applyFilter();search.focus();}});
  render();
}})();
</script>
{COMMON_JS}
</body>
</html>"""


# ================= 추가 CSS (목록·상세 공용) =================
# 주의: nfd-brief.css 전역 리셋이 `.nfd-brief * { margin:0!important; padding:0!important }` 이므로
#       카드/검색/페이저의 모든 padding·margin 은 반드시 !important 로 지정해야 적용된다.
LIST_DETAIL_CSS = """<style>
/* 상세 히어로 — 흰색 배경 + 어두운 폰트 */
.nfd-case-hero .nfd-brief-hero-video-wrap{background:#fff!important;border-radius:0!important;}
.nfd-case-hero .nfd-brief-hero-video-wrap::after{display:none!important;}
.nfd-case-hero{border-bottom:1px solid #eef0f5!important;}
.nfd-case-hero .nfd-brief-hero-container{padding:56px 40px 40px!important;}
.nfd-case-hero .nfd-brief-hero-heading{color:#0f1830!important;}
.nfd-case-hero .nfd-brief-hero-desc{color:#7b8496!important;}
.nfd-case-hero-title{font-size:38px!important;}
.nfd-case-hero-badge{display:inline-block;background:#eef2ff!important;color:#0025B4!important;font-size:14px;font-weight:700;
  padding:8px 16px!important;border-radius:50px;margin-bottom:20px!important;}

/* 히어로 제거된 목록 섹션 — 상단 여백 축소 + 배경색 없음(투명, 임베드 친화) */
.nfd-case-listsec{padding:44px 0 70px!important;background:transparent!important;}

/* 검색 */
.nfd-case-search{position:relative;max-width:640px;margin:0 auto 14px!important;}
.nfd-case-search-icon{position:absolute;left:22px;top:50%;transform:translateY(-50%);}
.nfd-case-search input{width:100%;box-sizing:border-box;padding:18px 52px 18px 54px!important;font-size:16px;font-family:inherit;
  border:2px solid #e3e7ef;border-radius:50px;background:#fff;color:#1a1a1a;outline:none;transition:border-color .2s,box-shadow .2s;}
.nfd-case-search input::placeholder{color:#9aa3b2;}
.nfd-case-search input:focus{border-color:#0025B4;box-shadow:0 0 0 4px rgba(0,37,180,.10);}
.nfd-case-search button{position:absolute;right:18px;top:50%;transform:translateY(-50%);background:#eef1f7;border:none;
  width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#6b7488;}
.nfd-case-search button:hover{background:#e0e4ee;color:#1a1a1a;}
.nfd-case-count{text-align:center;color:#6b7488;font-size:14px;font-weight:500;margin:0 0 34px!important;}

/* 카드 그리드 — 균일 높이(라인클램프) */
.nfd-case-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:22px!important;align-items:stretch;}
.nfd-case-card{position:relative;display:flex;flex-direction:column;height:100%;background:#fff;
  border:1px solid #e9edf5;border-radius:20px;padding:26px 26px 22px!important;text-decoration:none;color:inherit;
  overflow:hidden;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;
  box-shadow:0 2px 12px rgba(16,30,70,.05);}
.nfd-case-card::before{content:"";position:absolute;top:0;left:0;width:100%;height:4px;
  background:linear-gradient(90deg,#0025B4,#1a4fff);opacity:0;transition:opacity .18s ease;}
.nfd-case-card:hover{transform:translateY(-4px);box-shadow:0 16px 40px rgba(0,37,180,.14);border-color:#cfd9ff;}
.nfd-case-card:hover::before{opacity:1;}
.nfd-case-card-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px!important;}
.nfd-case-card-badge{display:inline-flex;align-items:center;gap:5px;background:#eef2ff;color:#0025B4;
  font-size:12.5px;font-weight:700;padding:6px 12px!important;border-radius:50px;letter-spacing:-.01em;}
.nfd-case-card-date{color:#aab2c2;font-size:12.5px;font-weight:600;}
.nfd-case-card-title{font-size:18.5px;font-weight:700;line-height:1.45em;color:#0f1830;margin:0 0 11px!important;
  word-break:keep-all;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  min-height:2.9em;}
.nfd-case-card-summary{font-size:14.5px;line-height:1.6em;color:#646e82;margin:0 0 16px!important;word-break:keep-all;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:3.2em;}
.nfd-case-card-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px!important;max-height:28px;overflow:hidden;}
.nfd-case-tag{font-size:12px;font-weight:500;color:#6b7488;background:#f4f6fb;padding:4px 10px!important;border-radius:50px;white-space:nowrap;}
.nfd-case-card-more{display:inline-flex;align-items:center;gap:4px;color:#0025B4;font-size:14px;font-weight:700;
  margin-top:auto!important;padding-top:12px!important;border-top:1px solid #f0f2f7;width:100%;}
.nfd-case-card-more svg{transition:transform .18s ease;}
.nfd-case-card:hover .nfd-case-card-more svg{transform:translateX(3px);}
.nfd-case-empty{text-align:center;color:#8a93a6;font-size:16px;font-weight:500;padding:60px 0!important;}

/* 페이저 */
.nfd-case-pager{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:48px!important;flex-wrap:wrap;}
.nfd-case-page-btn{min-width:42px;height:42px;padding:0 12px!important;border:1px solid #e3e7ef;background:#fff;border-radius:12px;
  font-family:inherit;font-size:15px;font-weight:600;color:#3a4358;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;
  transition:all .15s ease;}
.nfd-case-page-btn:hover:not(:disabled){border-color:#0025B4;color:#0025B4;}
.nfd-case-page-btn.is-active{background:#0025B4;border-color:#0025B4;color:#fff;}
.nfd-case-page-arrow{color:#3a4358;}
.nfd-case-page-btn:disabled{opacity:.35;cursor:not-allowed;}
.nfd-case-page-dots{color:#aab2c2;padding:0 2px!important;font-weight:600;}

/* 상세 페이지 하단 여백 축소 — 콘텐츠에 딱 맞게 */
.nfd-case-detail #section-news{padding-bottom:22px!important;}
.nfd-case-detail .nfd-case-pn-bar{padding:22px 24px 26px!important;margin-top:0!important;}

/* 상세 이전/다음 바 */
.nfd-case-pn-bar{max-width:920px;margin:10px auto 0!important;padding:40px 24px 10px!important;display:flex;align-items:stretch;justify-content:space-between;gap:14px;}
.nfd-case-pn{flex:1;display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:54px;padding:0 20px!important;
  border:1px solid #e3e7ef;border-radius:14px;background:#fff;color:#3a4358;font-size:15px;font-weight:600;text-decoration:none;
  transition:all .15s ease;}
.nfd-case-pn:hover{border-color:#0025B4;color:#0025B4;}
.nfd-case-pn--list{flex:0 0 auto;min-width:88px;}
.nfd-case-pn--disabled{flex:1;visibility:hidden;}

@media (max-width:760px){
  .nfd-case-hero-title{font-size:30px!important;}
  .nfd-case-hero .nfd-brief-hero-heading{font-size:34px!important;}
  .nfd-case-grid{grid-template-columns:1fr;gap:18px!important;}
  .nfd-case-card{padding:24px 22px!important;border-radius:18px;}
  .nfd-case-card-title{font-size:18px;}
  .nfd-case-pn span{display:none;}
  .nfd-case-pn--list span{display:inline;}
}
</style>"""


def main():
    cases = load_cases()                 # vol DESC (최신 먼저)
    by_vol = {c["vol"]: c for c in cases}
    vols_sorted = sorted(by_vol)         # 오름차순: 이전=작은 vol, 다음=큰 vol

    os.makedirs(CASES_DIR, exist_ok=True)
    # 목록
    with open(os.path.join(CASES_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_list(cases))
    # 상세
    for i, vol in enumerate(vols_sorted):
        prev_vol = vols_sorted[i-1] if i > 0 else None
        next_vol = vols_sorted[i+1] if i < len(vols_sorted)-1 else None
        d = os.path.join(CASES_DIR, str(vol))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_detail(by_vol[vol], prev_vol, next_vol))

    print(f"생성 완료: {len(cases)}건")
    print(f"  - cases/index.html")
    for vol in vols_sorted:
        print(f"  - cases/{vol}/index.html")


if __name__ == "__main__":
    main()
