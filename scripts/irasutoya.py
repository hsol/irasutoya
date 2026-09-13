#!/usr/bin/env python3
"""irasutoya.py — fast search / download / inline for いらすとや (irasutoya.com).

  irasutoya.py find "リンゴを食べる"        검색만, 압축 출력
  irasutoya.py get  "リンゴを食べる" [n]    검색 + 상위 n개 다운로드 (기본 1)
  irasutoya.py b64  <query|path> [maxpx]   다운로드 후 data URI 출력 (기본 480px)
  옵션: --json (전체 필드)  --urls (원본 URL 포함)  --open (미리보기로 열기)
"""
import base64, json, os, random, re, shutil, subprocess, sys, tempfile, urllib.parse
from concurrent.futures import ThreadPoolExecutor

FEED = "https://www.irasutoya.com/feeds/posts/summary"   # summary is ~40% smaller than default
HOME = "https://www.irasutoya.com/"
CACHE = os.path.expanduser("~/.cache/irasutoya-labels.txt")
UA   = "Mozilla/5.0"
PART = "をがのにはでへとやもか"
OUT  = os.path.expanduser(os.environ.get("IRASUTOYA_OUT", "~/Downloads/irasutoya"))

def _kana(s): return all("぀" <= c <= "ヿ" for c in s)
def k2h(s):   return "".join(chr(ord(c)-0x60) if "ァ" <= c <= "ヶ" else c for c in s) if _kana(s) else s
def h2k(s):   return "".join(chr(ord(c)+0x60) if "ぁ" <= c <= "ゖ" else c for c in s) if _kana(s) else s

# 한자 <-> 가타카나 표기가 둘 다 쓰이는 명사 (いらすとや 제목 표기가 갈린다)
SYN = {}
for _a, _b in [
    ("猿","サル"),("犬","イヌ"),("猫","ネコ"),("鳥","トリ"),("魚","サカナ"),("馬","ウマ"),
    ("牛","ウシ"),("豚","ブタ"),("羊","ヒツジ"),("鼠","ネズミ"),("兎","ウサギ"),("熊","クマ"),
    ("狐","キツネ"),("狸","タヌキ"),("虎","トラ"),("蛇","ヘビ"),("亀","カメ"),("蛙","カエル"),
    ("蟹","カニ"),("海老","エビ"),("象","ゾウ"),("鹿","シカ"),("猪","イノシシ"),("鶏","ニワトリ"),
    ("蜂","ハチ"),("蝶","チョウ"),("蟻","アリ"),("貝","カイ"),("虫","ムシ"),
    ("卵","タマゴ"),("林檎","リンゴ"),("蜜柑","ミカン"),("苺","イチゴ"),("桃","モモ"),
    ("葡萄","ブドウ"),("西瓜","スイカ"),("人参","ニンジン"),("玉葱","タマネギ"),("大根","ダイコン"),
    ("鞄","カバン"),("眼鏡","メガネ"),("煙草","タバコ"),("鍵","カギ"),("傘","カサ"),("靴","クツ"),
    ("机","ツクエ"),("椅子","イス"),("箸","ハシ"),("皿","サラ"),("鋏","ハサミ"),("薬","クスリ"),
]:
    SYN.setdefault(_a, []).append(_b)
    SYN.setdefault(_b, []).append(_a)

def forms(t):
    """한 토큰의 표기 변형: 원형 + 한자/가타카나 대응어 + 가나 변환."""
    out = [t] + SYN.get(t, [])
    for x in list(out):
        for y in (k2h(x), h2k(x)):
            if y not in out:
                out.append(y)
    return out

def _cls(c):
    if "\u30a1" <= c <= "\u30fa": return "K"
    if "\u3041" <= c <= "\u3096": return "H"
    if "\u4e00" <= c <= "\u9fff": return "J"
    return "."

def hits(title, toks):
    """exact = 단어 경계가 끊긴 일치, partial = 더 긴 같은 문자종 안에 묻힌 일치."""
    ex = pa = 0
    for t in toks:
        for f in forms(t):
            i = title.find(f)
            if i < 0:
                continue
            b = title[i-1] if i else ""
            a = title[i+len(f)] if i+len(f) < len(title) else ""
            same = (b and _cls(b) == _cls(f[0])) or (a and _cls(a) == _cls(f[-1]))
            if same: pa += 1
            else:    ex += 1
            break
    return ex, pa

def nouns(tok):
    """토큰 안에서 명사로 보이는 덩어리만 뽑는다: 持ったサル -> サル (동사 활용 꼬리 제거)."""
    runs = [(m.group(), _cls(m.group()[0]))
            for m in re.finditer(r"[\u4e00-\u9fff]+|[\u30a1-\u30fa\u30fc]+|[\u3041-\u3096]+|[A-Za-z0-9]+", tok)]
    if len(runs) <= 1:
        return [tok]
    return [r for r, c in runs if (c in ("J", "K") and len(r) >= 2) or (c == "J" and len(runs) == 1)]

def split_particles(q):
    """조사는 명사(한자·가타카나) 뒤에 올 때만 경계로 본다. 「のり」의 の 를 자르지 않게."""
    out = []
    for chunk in q.split():
        cur = ""
        for c in chunk:
            if c in PART and cur and _cls(cur[-1]) in ("J", "K"):
                out.append(cur); cur = ""
            else:
                cur += c
        if cur:
            out.append(cur)
    return [t for t in out if t]

def variants(q):
    q = q.strip()
    toks = split_particles(q)
    core = []
    for t in toks:
        for n in nouns(t):
            if n not in core:
                core.append(n)
    v = [q]
    if len(toks) > 1:
        base = [forms(t)[:3] for t in toks]
        for i in range(3):
            v.append(" ".join(b[i] if i < len(b) else b[0] for b in base))
        for alt in base[0][1:3]:
            v.append(alt + " " + base[-1][0])
    if len(core) > 1 and core != toks:
        cb = [forms(t)[:2] for t in core]
        for i in range(2):
            v.append(" ".join(b[i] if i < len(b) else b[0] for b in cb))
    v += forms(core[0])[:3] if core else []
    seen, out = set(), []
    for x in v:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out[:12], (toks + [c for c in core if c not in toks])

def curl(url, binary=False, t="12"):
    return subprocess.run(["curl", "-sSL", "--compressed", "-m", t, "-A", UA, url],
                          capture_output=True).stdout

def feed_url(q=None, label=None, n=20, start=1):
    url = FEED + ("/-/" + urllib.parse.quote(label) if label else "")
    p = {"alt": "json", "max-results": n, "start-index": start}
    if q:
        p["q"] = q
    return url + "?" + urllib.parse.urlencode(p)

def fetch(q=None, label=None, n=20, start=1):
    try:
        feed = json.loads(curl(feed_url(q, label, n, start)))["feed"]
    except Exception:
        return []
    out = []
    for e in feed.get("entry", []):
        html = e.get("content", {}).get("$t", "")
        m = re.search(r'src="(https://blogger\.googleusercontent\.com/[^"]+?\.(?:png|jpg|gif))"', html)
        src = m.group(1) if m else e.get("media$thumbnail", {}).get("url", "")
        if not src:
            continue
        out.append({"title": e["title"]["$t"],
                    "img": re.sub(r"/s\d+(?:-c)?/", "/s800/", src),
                    "file": src.rsplit("/", 1)[-1],
                    "page": next((l["href"] for l in e.get("link", []) if l.get("rel") == "alternate"), ""),
                    "labels": [c["term"] for c in e.get("category", [])],
                    "q": q})
    return out

def search(q, limit=10, label=None):
    vs, toks = variants(q)
    with ThreadPoolExecutor(max_workers=len(vs)) as ex:
        groups = list(ex.map(fetch, vs))
    order, best = {v: i for i, v in enumerate(vs)}, {}
    for g in groups:
        for r in g:
            k = r["page"] or r["img"]
            if k not in best or order[r["q"]] < order[best[k]["q"]]:
                best[k] = r
    def score(r):
        t = r["title"]
        ex, pa = hits(t, toks)
        person = 1 if re.search(r"人|男|女|子|さん|くん|ちゃん", t) else 0
        return (-(ex * 10 + pa), order[r["q"]], -person, len(t))
    ranked = sorted(best.values(), key=score)
    if label:
        keep = [r for r in ranked if any(label in x for x in r["labels"])]
        if keep:
            ranked = keep
        else:
            sys.stderr.write(f"note: no result carries label {label!r}; showing unfiltered\n")
    return ranked[:limit], vs

def all_labels():
    """Site label list from the Blogger widget on the home page. Cached for a day."""
    import time
    if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < 86400:
        return open(CACHE, encoding="utf-8").read().split()
    html = curl(HOME, t="20").decode("utf-8", "replace")
    found = re.findall(r'/search/label/([^"\'?>]+)', html)
    labels, seen = [], set()
    for f in found:
        L = urllib.parse.unquote(f)
        if L not in seen:
            seen.add(L); labels.append(L)
    if labels:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        open(CACHE, "w", encoding="utf-8").write("\n".join(labels))
    return labels

def random_entries(n=1):
    try:
        total = int(json.loads(curl(feed_url(n=0)))["feed"]["openSearch$totalResults"]["$t"])
    except Exception:
        return []
    picks = [random.randint(1, max(total - 1, 1)) for _ in range(n)]
    with ThreadPoolExecutor(max_workers=min(n, 6)) as ex:
        got = list(ex.map(lambda i: fetch(n=1, start=i), picks))
    return [g[0] for g in got if g]

def dims(p):
    d = open(p, "rb").read(33)
    if d[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(d[16:20], "big"), int.from_bytes(d[20:24], "big")
    return 0, 0

def grab(url, path):
    d = curl(url, t="25")
    if not (d[:8] == b"\x89PNG\r\n\x1a\n" or d[:3] == b"\xff\xd8\xff"):
        raise SystemExit("not an image: " + url)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "wb").write(d)
    return len(d)

def shrink(path, px):
    """Resize to px on the long edge. macOS sips -> Pillow -> original."""
    small = os.path.join(tempfile.gettempdir(), "_irasutoya_small.png")
    if shutil.which("sips"):
        subprocess.run(["sips", "-Z", str(px), "--out", small, path], capture_output=True)
        if os.path.exists(small):
            return small
    try:
        from PIL import Image
        im = Image.open(path)
        im.thumbnail((px, px))
        im.save(small)
        return small
    except Exception:
        sys.stderr.write("note: no sips/Pillow, emitting full size\n")
        return path

def report(res, header, urls=False):
    print(header + f"   ({len(res)} hits)")
    for i, r in enumerate(res, 1):
        print(f"{i:2}{'*' if 'path' in r else ' '} {r['title']} | {r['file']} | {','.join(r['labels'][:3])}")
        if "path" in r:
            w, h = dims(r["path"])
            print(f"     saved {r['path']} ({r['bytes']//1024}KB {w}x{h})  src {r['page']}")
        elif urls:
            print("     " + r["img"])

def parse_args(argv):
    pos, flags, label = [], set(), None
    i = 0
    while i < len(argv):
        x = argv[i]
        if x == "--label" and i + 1 < len(argv):
            label = argv[i + 1]; i += 2; continue
        if x.startswith("--label="):
            label = x.split("=", 1)[1]; i += 1; continue
        flags.add(x) if x.startswith("--") else pos.append(x)
        i += 1
    return pos, flags, label

USAGE = """irasutoya.py \u2014 search and download \u3044\u3089\u3059\u3068\u3084 illustrations

  find   "<japanese>" [n]      search, list candidates
  get    "<japanese>" [n]      search + download the top n            (default 1)
  browse "<label>"    [n]      list everything under one label
  random              [n]      n random illustrations
  labels ["<substr>"]          list the site's labels
  b64    <query|path> [px]     print a data URI                       (default 480px)

  --label "<name>"   keep only results carrying that label
  --get              also download what was listed (browse / random)
  --open  --urls  --json

  Output dir: $IRASUTOYA_OUT (default ~/Downloads/irasutoya)"""

def main():
    a, f, label = parse_args(sys.argv[1:])
    cmd = (a + ["find"])[0]
    q = a[1] if len(a) > 1 else ""
    n = int(a[2]) if len(a) > 2 and a[2].isdigit() else (1 if cmd in ("get", "b64") else 10)
    if cmd == "random":                      # random takes its count as the first arg
        n = int(q) if q.isdigit() else 1

    if (cmd in ("-h", "--help", "help")
            or cmd not in ("find", "get", "browse", "random", "labels", "b64")
            or f & {"-h", "--help"}
            or (cmd in ("find", "get", "b64") and not q)):
        print(USAGE); return

    if cmd == "labels":
        ls = [x for x in all_labels() if not q or q in x]
        print(f"{len(ls)} labels")
        print("  ".join(ls))
        return

    path, header = None, ""
    if cmd == "b64" and os.path.exists(q):
        res = []
        path = q
    elif cmd == "random":
        res = random_entries(max(n, 1))
        header = "random"
    elif cmd == "browse":
        target = q or label
        if not target:
            print("browse needs a label \u2014 try: irasutoya.py labels"); return
        res = fetch(label=target, n=n)
        header = f"label: {target}"
    else:
        res, vs = search(q, 10, label)
        header = "tried: " + " | ".join(vs) + (f"   [label {label}]" if label else "")

    if path is None:
        if not res:
            print(header + "   (0 hits) \u2014 try one broader noun")
            return
        if cmd in ("get", "b64") or "--get" in f:
            with ThreadPoolExecutor(max_workers=4) as ex:
                fs = [(r, ex.submit(grab, r["img"], os.path.join(OUT, r["file"])))
                      for r in res[:n]]
            for r, fu in fs:
                r["path"], r["bytes"] = os.path.join(OUT, r["file"]), fu.result()
        path = res[0].get("path")

    if cmd == "b64":
        print("data:image/png;base64," + base64.b64encode(
            open(shrink(path, n if n > 8 else 480), "rb").read()).decode())
        return

    if "--json" in f:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        report(res, header, "--urls" in f)
    if "--open" in f and path:
        opener = "open" if shutil.which("open") else "xdg-open"
        subprocess.run([opener, path], capture_output=True)

main()
