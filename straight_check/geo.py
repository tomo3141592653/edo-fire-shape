"""記録の「長さ」と、出火点〜最も遠い端の直線距離を比べる。

入力: straight_check/index.csv、straight_check/codex_out.txt（codex が本文から読んだ出火地・遠端と現在の地名）
出力: straight_check/straight.csv（直線距離 km、記録の長さ km、比）。座標は Nominatim（1秒1件）で引き、geocache.json に残す

1間 = 1.818 m。比 = 記録の長さ ÷ 直線距離。1 を大きく超えるなら「長さ」は直線でない（延べ・誇張）。
"""
import csv
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "geocache.json"
KEN_M = 1.818


# 手で監査して座標を直した区域（id: (出火点, 最遠端)）。理由は audit_notes.md
MANUAL = {
    "47": ([35.6866, 139.7630], [35.6665, 139.7585]),  # 辰ノ口（大手町1）→ 芝口御門（新橋駅付近）。「丸の内付近」の重心では近すぎた
}


def clean(q):
    """codex の地名は「千代田区内神田付近」「中央区銀座・築地境付近」の形。付近・境を落とし、並記は最初の一つにする"""
    q = re.sub(r"(付近|周辺|一帯|あたり|地区|境)", "", q)
    q = re.split(r"[・、/（(]", q)[0]
    return q.replace(" ", "").strip()


def geocode(q, cache):
    q = clean(q)
    if q in cache:
        return cache[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": "東京都 " + q, "format": "json", "limit": 1, "countrycodes": "jp"})
    req = urllib.request.Request(url, headers={"User-Agent": "ayumu-research/1.0"})
    time.sleep(1.1)
    res = json.load(urllib.request.urlopen(req, timeout=30))
    cache[q] = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return cache[q]


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def main():
    raw = (HERE / "codex_out.txt").read_text()
    ans = {a["id"]: a for a in json.loads(raw[raw.index("["):raw.rindex("]") + 1])}
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    out = []
    for r in csv.DictReader(open(HERE / "index.csv")):
        a = ans.get(int(r["id"]), {})
        s, e = a.get("start_modern"), a.get("far_end_modern")
        ps = geocode(s, cache) if s else None
        pe = geocode(e, cache) if e else None
        if r["id"] in MANUAL:
            ps, pe = MANUAL[r["id"]]
        d = km(ps, pe) if ps and pe else None
        L = float(r["length_ken"]) * KEN_M / 1000
        out.append(dict(id=r["id"], area=r["area"], record=r["record"], start=a.get("start_place"), far_end=a.get("far_end_place"),
                        start_modern=s, far_end_modern=e, straight_km=round(d, 2) if d else None, length_km=round(L, 2),
                        length_over_straight=round(L / d, 2) if d else None, w_over_l=r["w_over_l"], note=a.get("note")))
    with open(HERE / "straight.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    got = sorted(x["length_over_straight"] for x in out if x["length_over_straight"])
    print(f"{len(got)}/{len(out)} 区域で直線距離が取れた")
    if got:
        print("記録の長さ÷直線距離: 中央値", got[len(got) // 2], " 四分位", got[len(got) // 4], got[3 * len(got) // 4])


if __name__ == "__main__":
    main()
