# HTML 조립 — 플레이스홀더 매핑

n8n Code 노드에서 base.html의 플레이스홀더를 치환하여 최종 HTML을 생성한다.

## 플레이스홀더 목록

| 플레이스홀더 | 예시 값 | 설명 |
|---|---|---|
| `{{INLINE_CSS}}` | (nfd-brief.css 전체 내용) | CSS를 인라인으로 삽입 |
| `{{DATE_FULL}}` | `2026년 4월 21일 · 월요일` | 히어로 메인 날짜 |
| `{{DATE_SHORT}}` | `2026.04.21 MON` | 히어로 하단 날짜 |
| `{{DATE_SHORT_DOT}}` | `2026.04.21` | title 태그 + 공유하기 텍스트용 |
| `{{SECTION_DESC}}` | `오늘의 핫이슈 TOP5 · 보험업계 뉴스 · 고객 터치 미션` | 히어로 설명 |
| `{{HERO_STAT_SECTIONS}}` | `핫이슈 TOP5, 보험 뉴스 TOP3, 고객 터치 미션` | 히어로 하단 섹션 목록 |
| `{{SECTION_TOP5}}` | (Claude 출력 HTML 스니펫) | 핫이슈 TOP5 카드 5개 |
| `{{SECTION_CATEGORY}}` | (Claude 출력 HTML 스니펫) | 요일별 카테고리 전체 section |
| `{{SECTION_TOUCH}}` | (Claude 출력 HTML 스니펫) | 터치 미션 전체 section |
| `{{NAV_CATEGORY_SVG}}` | (카테고리별 SVG 아이콘) | 플로팅 nav 카테고리 아이콘 |
| `{{NAV_CATEGORY_FULL}}` | `보험 뉴스 TOP3` | 플로팅 nav 전체 라벨 |
| `{{NAV_CATEGORY_SHORT}}` | `보험뉴스` | 플로팅 nav 축약 라벨 |

## 요일별 카테고리 매핑

| 요일 | 카테고리 | SECTION_DESC | NAV_CATEGORY_FULL | NAV_CATEGORY_SHORT | NAV SVG |
|---|---|---|---|---|---|
| 월 | 보험뉴스 | 핫이슈 TOP5 · 보험업계 뉴스 · 고객 터치 미션 | 보험 뉴스 TOP3 | 보험뉴스 | 신문 아이콘 |
| 화 | 보상사례 | 핫이슈 TOP5 · 보상사례 브리핑 · 고객 터치 미션 | 보상사례 브리핑 | 보상사례 | 저울 아이콘 |
| 수 | 직업별공감 | 핫이슈 TOP5 · 직업별 공감 · 고객 터치 미션 | 직업별 공감 포인트 | 직업별공감 | 사람들 아이콘 |
| 목 | 세일즈한입 | 핫이슈 TOP5 · 세일즈 한 입 · 고객 터치 미션 | 세일즈 스킬 한 입 | 세일즈한입 | 타겟 아이콘 |
| 금 | 보상사례 | (화와 동일) | (화와 동일) | (화와 동일) | (화와 동일) |
| 토 | 직업별공감 | (수와 동일) | (수와 동일) | (수와 동일) | (수와 동일) |
| 일 | 세일즈한입 | (목과 동일) | (목와 동일) | (목와 동일) | (목와 동일) |

## NAV SVG 아이콘 (카테고리별)

### 보험뉴스 (신문)
```html
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0025B4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
  <path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/>
</svg>
```

### 보상사례 (저울)
```html
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0025B4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 3v18M5 8l7-5 7 5M5 8l-2 8h4l-2-8zM19 8l-2 8h4l-2-8z"/>
</svg>
```

### 직업별 공감 (사람들)
```html
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0025B4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
  <circle cx="9" cy="7" r="4"/>
  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
</svg>
```

### 세일즈 한입 (타겟)
```html
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0025B4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <circle cx="12" cy="12" r="6"/>
  <circle cx="12" cy="12" r="2"/>
</svg>
```

## n8n Code 노드 조립 예시 (JavaScript)

```javascript
// CSS 파일 내용을 읽어서 인라인 삽입
const cssContent = $node["Read CSS"].json.data;

const html = baseTemplate
  .replace('{{INLINE_CSS}}', cssContent)
  .replace(/\{\{DATE_FULL\}\}/g, '2026년 4월 21일 · 월요일')
  .replace(/\{\{DATE_SHORT\}\}/g, '2026.04.21 MON')
  .replace(/\{\{DATE_SHORT_DOT\}\}/g, '2026.04.21')
  .replace('{{SECTION_DESC}}', '오늘의 핫이슈 TOP5 · 보험업계 뉴스 · 고객 터치 미션')
  .replace('{{HERO_STAT_SECTIONS}}', '핫이슈 TOP5, 보험 뉴스 TOP3, 고객 터치 미션')
  .replace('{{SECTION_TOP5}}', top5HtmlSnippet)
  .replace('{{SECTION_CATEGORY}}', categoryHtmlSnippet)
  .replace('{{SECTION_TOUCH}}', touchHtmlSnippet)
  .replace('{{NAV_CATEGORY_SVG}}', navCategorySvg)
  .replace(/\{\{NAV_CATEGORY_FULL\}\}/g, '보험 뉴스 TOP3')
  .replace(/\{\{NAV_CATEGORY_SHORT\}\}/g, '보험뉴스');
```
