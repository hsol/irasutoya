---
name: irasutoya
description: Find, download and place free いらすとや (irasutoya.com) illustrations. Use whenever a slide deck, document, blog post, web page or design canvas would be better with an illustration or icon.
---

# いらすとや illustrations

[いらすとや](https://www.irasutoya.com) is a Japanese library of ~25,000 free flat
illustrations. This skill searches it, downloads the transparent PNGs and places
them in whatever you are building.

## 0. One call does it all

Search, ranking and download happen in a **single shell call** (~1.5s). Run the
script that ships with this skill:

```bash
python3 scripts/irasutoya.py get "バナナを持ったサル"
```

```
tried: バナナを持ったサル | バナナ サル | ばなな 猿 | バナナ   (10 hits)
 1* バナナを持った猿のイラスト（申年・干支） | eto_saru_banana2.png | 動物キャラ,干支
     saved ~/Downloads/irasutoya/eto_saru_banana2.png (389KB 776x800)  src https://...
 2  頭にバナナを乗せた猿のイラスト | eto_saru_banana.png | 動物キャラ,干支
```

| Command | What it does |
|---|---|
| `find "<japanese>"` | search only, 10 candidates |
| `get "<japanese>" [n]` | search + download the top n (default 1) |
| `b64 <query\|path> [px]` | print a data URI — expensive, see §4 |
| Flags | `--open` open in a viewer / `--urls` include source URLs / `--json` full fields |

- Need several? `get "..." 3` downloads them **in one call**. Never loop one at a time.
- Downloads land in `~/Downloads/irasutoya/`. Override with `IRASUTOYA_OUT=/some/dir`.
- Requires network access to `www.irasutoya.com` and `blogger.googleusercontent.com`.
  Some sandboxes block both — see §7 before assuming the site is down.

## 1. When to reach for it

Add an illustration **without being asked** when building:

- design canvases and artboards, artifact web pages, landing pages, posters
- slide decks (HTML slides, `.pptx`)
- reports, guides, manuals (`.docx`, PDF)
- blog posts, newsletters, social posts

**Skip it** for code and config files, data-table-only output, when the user said
"no images", and for solemn or legally operative documents (contracts, official
filings, legal briefs). If the tone is ambiguous, add it and say so in one line.

**Density:** 0–1 per slide, at most 1 per document section, roughly 1 per blog
subheading. Never add one just to fill space.

## 2. Choosing the query

Queries must be **Japanese**, but the script tries the orthographic variants for you,
in parallel:

- particle stripping (`をのがにはでへと`) — only after a noun, so `のり` keeps its `の`
- katakana ↔ hiragana (`リンゴ` ↔ `りんご`)
- kanji ↔ katakana synonyms (`猿`↔`サル`, `眼鏡`↔`メガネ`, `卵`↔`タマゴ`) — titles use
  only one of the two, and which one is unpredictable
- verb-tail stripping (`持ったサル` → `サル`)

Ranking **demotes substring matches**, so searching `サル` no longer surfaces
`アンドリューサルクス` (a prehistoric mammal).

So just pick the concept word. If you get 0 hits, do **not** retry with different
spellings — call once more with a broader single noun.

| Concept | Query | Concept | Query |
|---|---|---|---|
| meeting | 会議 / ミーティング | worry, trouble | 悩む / 困る / トラブル |
| video call | ビデオ会議 / オンライン | warning | 注意 / 警告 / びっくり |
| presenting | プレゼン / 発表 | question | 質問 / はてな |
| desk work, remote | パソコン / テレワーク | success, celebration | 喜ぶ / 成功 / 万歳 |
| programming | プログラマー / プログラミング | mistake, apology | ミス / 謝る |
| AI, robots | AI / 人工知能 / ロボット | deadline, time | 締め切り / 時計 / 急ぐ |
| data, charts | グラフ / データ / 分析 | checklist, done | チェック / リスト |
| growth, decline | 上昇 / 成長 / 下降 | explaining, guiding | 説明 / 案内 / 指差し |
| money, budget | お金 / 予算 / 費用 | shopping, payment | 買い物 / キャッシュレス |
| contracts, paperwork | 契約 / 書類 / サイン | delivery | 宅配 |
| law | 弁護士 / 裁判 / 法律 | health, hospital | 病院 / 医者 / 健康 / 運動 |
| security | セキュリティ / ハッカー | study, school | 勉強 / 学校 / 学生 |
| sales, support | 営業 / 接客 / 相談 / 電話 | burnout | 疲れる / 過労 |
| email, notification | メール / 通知 | seasons, holidays | 桜 / 花火 / 紅葉 / 雪 / 正月 |
| teamwork | 協力 / チームワーク / 握手 | frames, decoration | 枠 / 吹き出し / 矢印 / 飾り罫線 |
| hiring, interviews | 採用 / 面接 / 就職 | ideas | ひらめき / アイデア |

- Pin down the person by appending a word: `会議 会社員`, `勉強 女性`, `プレゼン 子供`
- Pick the expression from the suffix in the result title: `（笑顔）` `（真剣）` `（困った顔）`
- **The filename is the description.** `kaigi_hakui_shinken.png` = meeting · white coat
  (doctor) · serious face
- Within one deliverable, stay in one filename-prefix family so the set looks coherent
- Turn abstract verbs into **the object that represents them**: copying → `コピー機`,
  pasting → `テープのり` / `接着剤`, searching → `虫眼鏡`

## 3. Placing the file

- **pptx** — pass the downloaded path straight to your pptx tooling. The PNGs have
  transparent backgrounds, so don't put a white box behind them.
- **docx / PDF** — use the format skill's image insert; 30–50% of body width.
- **Blog / Markdown** — move the file next to the post (`images/`) and use a relative
  path. Write the alt text in the reader's language, not the Japanese title.
- **Artifacts and design canvases** — see §4.

## 4. Artifacts and design canvases

Artifact pages block external image hosts via CSP. **A blogger URL in `src` renders
nothing.** In order:

1. **A folder shared with the host session — the default.** Download into it and
   reference the local path, or publish the file as an artifact asset.
   Binary transfer, no token cost.
2. **No shared folder?** Ask for one in a single line.
3. **No shell at all?** Go to §7 and pre-stage.
4. **Last resort:** `b64` prints a data URI. It is expensive — 160px ≈ 34 KB,
   240px ≈ 70 KB, 480px ≈ 254 KB of text through the conversation.
   **Icon-sized, 1–2 images, 240px or less.**

## 5. Licence — inform, don't block

**Stance: state the rule, leave the call to the user.** Never stop or refuse the work,
and never nag.

- Free for personal, corporate, commercial and non-commercial use. No credit required
  (copyright is not waived).
- Paid tier: **21 or more illustrations in one commercial design** needs a paid licence.
  Repeats of the same image count once.
- Terms: https://www.irasutoya.com/p/terms.html

### When to count

Count **only when there are commercial signals** — something sold or advertised,
customer-facing material, product or service pages, brand content, paid courses or
publications. Personal notes, internal documents, learning material and rough drafts
are **not counted and not mentioned.** When unsure, don't count — do not assume
commercial use.

The unit is **distinct illustrations in one deliverable.** Reusing an image is 1 point.

### How to raise it

At the moment the 21st image goes in, mention it **exactly once**, briefly and lightly.
Use a question tool if one is available, otherwise a single line.

> Heads up: いらすとや needs a paid licence past 20 illustrations in one commercial
> design. This is number 21 — keep going, or drop a couple to stay at 20?

- If they say go ahead, **go ahead.** Don't ask again, don't bring it up again.
- **Never ask twice in one deliverable.** At 30 images, stay quiet.
- Running unattended? Leave the one-line note and carry on.

### Not about the count

These are explicit prohibitions in the terms, so explain once and offer another route:

- use contrary to public decency; aggressive, discriminatory, sexual or extreme use
- **redistributing or selling content whose substance is the artwork itself** —
  illustration packs, sticker sets, stock-asset sites

## 6. Wrapping up

The script already verifies magic bytes, size and dimensions. **Don't re-open the image
to check** (slow and expensive) — judge from the title and filename, and when unsure show
the user with `--open`. For artifacts, just confirm the image actually renders.

Close with one line: how many you used and where. If you raised the licence note, record
what the user chose — don't re-explain it.

## 7. No shell, or blocked network

Some environments have no shell, or a fetch tool that **drops the query string**, so
search fails silently.

1. **Never use the `irasutoya.com/search?q=` HTML page.** If the parameter is dropped
   you get the home page (newest posts) and it looks like a successful search.
   Use the feed endpoint:
   ```
   https://www.irasutoya.com/feeds/posts/default?q=<query>&alt=json&max-results=20
   ```
2. **Verify the result.** Check `openSearch$totalResults` and that the top titles
   actually contain the keyword. Unrelated recent posts mean **the parameter was
   dropped** — discard and go to step 4.
3. In a shell, **always quote the URL** — an unquoted `&` truncates the command.
4. **If images can't be downloaded, do not dump a list of search-page links on the
   user.** That hands the picking back to them. Instead:
   - **Pre-stage** — have a session that does have a shell download the images into a
     shared folder, then reference **local paths only.** No network needed afterwards.
   - Give the user one line to paste: `irasutoya.py get "<query>"` and where to put it.
   - If you truly must give a link, give the **direct image URL** of the one you chose
     (`/s800/....png`), not a search page.
