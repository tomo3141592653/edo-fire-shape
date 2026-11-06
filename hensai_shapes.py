"""『東京市史稿』変災篇（第4・第5、NDL pid 1915668・1915694）の OCR から、焼失範囲の「長さ・幅」を拾って数に直す。

入力: ndl/hensai/grab_<pid>.txt（ndl_fulltext.py grab の出力、前後200字つき）
出力: hensai_shapes.csv（コマ、記述、長さ[間]、幅[間]、幅÷長さ、前の文の風の語）

単位: 1里=36町、1町(丁)=60間。OCR の崩れ（数字の欠け、別の語の混入）があるので、数に直せない記述は捨てて件数を出す。
"""
import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAN = {"〇": 0, "零": 0, "一": 1, "壹": 1, "壱": 1, "二": 2, "貳": 2, "弐": 2, "三": 3, "參": 3, "四": 4, "五": 5,
       "六": 6, "七": 7, "八": 8, "九": 9}
UNIT10 = {"十": 10, "拾": 10, "廿": 20, "卄": 20, "卅": 30, "百": 100, "千": 1000}


def kan2num(s):
    """漢数字（十・廿・百を含む）と算用数字を数にする。読めなければ None"""
    s = s.strip()
    if re.fullmatch(r"[0-9０-９.]+", s):
        return float(s.translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    if not s:
        return None
    # 「三四町」「廿五六町」のように一桁の数字が二つ続くのは幅のある概数なので、両端の平均をとる
    if len(s) >= 2 and s[-1] in KAN and s[-2] in KAN and KAN[s[-1]] == KAN[s[-2]] + 1:
        lo, hi = kan2num(s[:-1]), kan2num(s[:-2] + s[-1])
        return None if lo is None or hi is None else (lo + hi) / 2
    total, cur = 0, 0
    for ch in s:
        if ch in KAN:
            cur = cur * 10 + KAN[ch]
        elif ch in UNIT10:
            total += (cur or 1) * UNIT10[ch]
            cur = 0
        else:
            return None
    return float(total + cur)


NUM = r"[〇零一壹壱二貳弐三參四五六七八九十拾廿卄卅百千0-9０-９.]+"
# 「長(さ/サ)…X町Y間 … 幅(平均/員/凡)…X町Y間」
PAT = re.compile(
    r"(?:長|竪|縱|縦)(?:サ|さ|延)?(?:凡|凢|およそ|大凡|凡そ)?(?:平均)?\s*(?P<l1>" + NUM + r")\s*(?P<lu1>里|町|丁|間)(?P<lh1>半)?(?:\s*(?P<l2>" + NUM + r")\s*(?P<lu2>町|丁|間)(?P<lh2>半)?)?"
    r"[^。幅横橫濶巾]{0,10}?。?(?:幅|横|橫|濶|巾)(?:平均凡|員平均|員凡|員|廣狹平均して|広狭平均して|平均して|平均ニして|平均よして|平均|不均|約|凡そ|凡|所により|ハ|は)?\s*(?P<w1>" + NUM + r")\s*(?P<wu1>里|町|丁|間)(?P<wh1>半)?(?:\s*(?P<w2>" + NUM + r")\s*(?P<wu2>町|丁|間)(?P<wh2>半)?)?")
# 数の「卅」、幅を「巾」、「幅平均凡」と書く記録も拾う（10/30 17時、全文の長さの記述から逆に探して見つけた）
# 幅を「横・橫・濶」、長さを「竪」と書く記録と、「長…。幅…」と句点で区切る記録も拾う（芝神明前・元禄16年・延享2年の取りこぼし、10/30 15時）
# 幅の単位に「里」を許す（弘化3年の丸山火事の飛び火区域「幅壹里程、長サ壹里半」が漏れていた、10/30）
# 幅を先に書く型「幅三丁長サ十五六町」「幅十町程、長三十五丁」（10/30 に 19 件の取りこぼしが分かった）
PAT_REV = re.compile(
    r"(?:幅|横|橫|濶|巾)(?:員|平均凡|平均|平均して|凡|凡そ)?\s*(?P<w1>" + NUM + r")\s*(?P<wu1>里|町|丁|間)(?P<wh1>半)?(?:\s*(?P<w2>" + NUM + r")\s*(?P<wu2>町|丁|間)(?P<wh2>半)?)?"
    r"[^。幅長]{0,6}?(?:長|竪|縱|縦)(?:サ|さ|延)?(?:凡|凢|およそ|大凡|凡そ)?\s*(?P<l1>" + NUM + r")\s*(?P<lu1>里|町|丁|間)(?P<lh1>半)?(?:\s*(?P<l2>" + NUM + r")\s*(?P<lu2>町|丁|間)(?P<lh2>半)?)?")
TOKEN = {"里": 36 * 60, "町": 60, "丁": 60, "間": 1}
WIND = re.compile(r"(?:東|西|南|北|乾|巽|坤|艮|戌亥|辰巳|未申|丑寅)*風[^。、]{0,4}?(?:烈|強|激|はげし|甚|つよ|猛|大)[^。、]{0,3}|大風|烈風|強風|颶風|無風|風なく|風靜")


def to_ken(n1, u1, n2, u2, h1=None, h2=None):
    """「一町半」の半は単位の半分（30間・半間）を足す"""
    a = kan2num(n1)
    if a is None:
        return None
    v = (a + (0.5 if h1 else 0)) * TOKEN[u1]
    if n2:
        b = kan2num(n2)
        if b is None:
            return None
        b += 0.5 if h2 else 0
        if TOKEN[u1] == TOKEN[u2]:  # 「幅所により五町三町」: 同じ単位が並ぶのは足し算でなく場所ごとの値
            return (v + b * TOKEN[u2]) / 2
        v += b * TOKEN[u2]
    return v


SOURCES = {"hensai": ("1915668", "1915694"), "bukou": ("1123706",), "shinsai": ("1915621",)}


def main(src="hensai"):
    rows, seen, bad = [], set(), 0
    for pid in SOURCES[src]:
        # 全文（dump）があればそれを使う。grab は型にかかったページの前後しか持たず、母集団が欠ける（10/30）
        full = HERE / "ndl" / src / f"full_{pid}.txt"
        txt = (full if full.exists() else HERE / "ndl" / src / f"grab_{pid}.txt").read_text()
        for blk in re.split(r"(?=--- コマ\d+ ---)", txt)[1:]:
            koma = int(re.match(r"--- コマ(\d+)", blk).group(1))
            for order, m in [("長幅", m) for m in PAT.finditer(blk)] + [("幅長", m) for m in PAT_REV.finditer(blk)]:
                key = (pid, m.group(0))
                if key in seen:
                    continue
                seen.add(key)
                L = to_ken(m["l1"], m["lu1"], m["l2"], m["lu2"], m["lh1"], m["lh2"])
                W = to_ken(m["w1"], m["wu1"], m["w2"], m["wu2"], m["wh1"], m["wh2"])
                if not L or not W:
                    bad += 1
                    continue
                before = blk[max(0, m.start() - 160):m.start()]
                # 武江年表は記事が「○」で始まるので、同じ記事の中だけを見る（前の記事の風を拾わない）
                entry = before.rsplit("○", 1)[-1] if src == "bukou" else before
                winds = WIND.findall(entry)
                rows.append(dict(pid=pid, koma=koma, text=m.group(0), length_ken=L, width_ken=W,
                                 w_over_l=round(W / L, 3), wind=" / ".join(winds[-2:]), entry=entry[-120:],
                                 order=order))
    # 同じ火事を別の史料が同じ数字で引いている重複（近いコマに同じ長さ・幅、表記だけ違う）を落とす
    kept = []
    for row in rows:
        dup = [k for k in kept if k["pid"] == row["pid"] and abs(k["koma"] - row["koma"]) <= 3
               and k["length_ken"] == row["length_ken"] and k["width_ken"] == row["width_ken"]]
        if dup:
            # 同じ火事の重複は「平均」と明記した方を残す（幅が平均かどうかを解析に使うため）
            if "平均" in row["text"] and "平均" not in dup[0]["text"]:
                kept[kept.index(dup[0])] = row
            continue
        kept.append(row)
    print(f"重複 {len(rows) - len(kept)} 件を落とした")
    rows = kept
    out = HERE / f"{src}_shapes.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} 件を数に直した（読めず捨てた {bad} 件）→ {out.name}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "hensai")
