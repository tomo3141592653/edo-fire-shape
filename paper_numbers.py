"""原稿（paper_draft.md）の表を台帳から作り直して差し込み、本文に書く数を一覧で出す。

台帳を直すたびに原稿の数を手で置き換えていて、一日に6回出し直して取り違えの元になったので作った（10/30）。
差し込むのは表の見出し行で見つけた表（3.1 主解析・出典の層・3.3 山川・3.4 短い火事・付表）と、
本文の数に付けた印 <!--n:名前-->値<!--/n-->（Markdown では見えない）。印の値は prose_values() が台帳から計算する。
本文に新しく数を書くときは印を付け、prose_values() に名前を足す。

使い方: python3 build_long_fires_v2.py && (cd straight_check && python3 match_yamakawa.py) && python3 paper_numbers.py
"""
import csv
import math
import re
import statistics as st
import sys
from pathlib import Path

from build_long_fires_v2 import width_avg

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper_draft.md"
R0, R37, RMAX = 0.392, 0.37, 0.499
# 主解析から外した安政2年10月2日の地震の夜の4区域（付表の除外表、第5巻421・423・433・434）
EQ = [0.033, 0.500, 0.231, 0.300]
KIND_LABEL = {
    "京の公家日記": "京の公家日記（基熙公記・基量卿記・兼香公記。江戸滞在中の基熙公記の1区域のほかは江戸から届いた伝聞）",
    "公的な書上・届・記録": "公的な書上・届・申渡・記録（町年寄手控・柳営日次記・御徒方萬年記・火事場見廻の書上・編者の綱文など）",
    "年表・炎上鑑": "年表・炎上鑑（年代炎上鑑・天享吾妻鑑・続武江年表など）",
    "月堂見聞集": "月堂見聞集",
    "その他の日記": "その他の日記・随筆",
}
VOL = {"1915668": "第4", "1915694": "第5"}


def load():
    rows = list(csv.DictReader(open(HERE / "edo_long_fires_v2.csv")))
    reps = [r for r in rows if r["role"] == "代表"]
    tags = {r["area"]: r["kind_auto"] for r in csv.DictReader(open(HERE / "source_tags.csv"))}
    missing = {r["area"] for r in reps} ^ set(tags)
    assert not missing, f"source_tags.csv と台帳の区域が合わない: {missing}"
    ys = [r for r in csv.DictReader(open(HERE / "straight_check" / "vs_yamakawa.csv")) if r["k"]]
    return rows, reps, tags, ys


def ratio(r):
    return float(r["w_over_l"])


def stat(xs, cols=(R0, R37, RMAX)):
    xs = sorted(xs)
    return [len(xs), f"{st.median(xs):.3f}"] + [sum(x < c for x in xs) for c in cols]


def row(label, cells):
    return "| " + " | ".join([label] + [str(c) for c in cells]) + " |"


def table_main(reps):
    n = len(reps)
    avg = [ratio(r) for r in reps if r["width_is_average"] == "True"]
    allr = [ratio(r) for r in reps]
    return [
        "| 数え方 | 区域数 | 中央値 | 0.392 未満 | 0.37 未満 | 0.499 未満 |",
        "|---|---|---|---|---|---|",
        row("幅に「平均」と明記の区域だけ", stat(avg)),
        row(f"全{n}区域", stat(allr)),
        row("飛び火区域を除く（本火だけ）", stat([ratio(r) for r in reps if "飛び火" not in r["area"]])),
        row("長さが「延」の記録を除く", stat([ratio(r) for r in reps if "延" not in r["record"]])),
        row("「平均」と書かれていない区域", stat([ratio(r) for r in reps if r["width_is_average"] != "True"])),
        row("（参考）地震の夜の4区域も入れる", stat(allr + EQ, (R0,)) + ["—", "—"]),
        row("（参考）同、「平均」明記だけ", stat(avg + EQ, (R0,)) + ["—", "—"]),
    ]


def table_source(reps, tags):
    out = ["| 出典の種類 | 区域数 | 中央値 | 0.392 未満 |", "|---|---|---|---|"]
    for kind, label in KIND_LABEL.items():
        out.append(row(label, stat([ratio(r) for r in reps if tags[r["area"]] == kind], (R0,))))
    return out


def table_yamakawa(reps, ys):
    ys15 = [r for r in ys if r["yamakawa_floor15"] != "True"]
    rec = lambda rs: [float(r["w_over_l"]) for r in rs]  # noqa: E731
    wst = lambda rs: [float(r["w_over_straight"]) for r in rs]  # noqa: E731
    area = lambda rs: [float(r["w_over_l"]) * float(r["k"]) ** 2 for r in rs]  # noqa: E731
    return [
        "| 物差し | 区域数 | 中央値 | 0.392 未満 |",
        "|---|---|---|---|",
        row("記録の 幅÷長さ（3.1、全区域）", stat([ratio(r) for r in reps], (R0,))),
        row("同、山川と照合できた区域だけ", stat(rec(ys), (R0,))),
        row("記録の幅 ÷ 山川の直線", stat(wst(ys), (R0,))),
        row("記録の面積（幅×記録の長さ）÷ 山川の直線²", stat(area(ys), (R0,))),
        row("（探索的）15町ちょうどの値を除く30区域: 記録の比", stat(rec(ys15), (R0,))),
        row("同、記録の幅 ÷ 山川の直線", stat(wst(ys15), (R0,))),
        row("同、記録の面積 ÷ 山川の直線²", stat(area(ys15), (R0,))),
    ]


def table_short():
    rs = [r for r in csv.DictReader(open(HERE / "hensai_shapes.csv")) if width_avg(r["text"])]
    out = ["| 長さ | 件数 | 中央値 | 0.392 以上 |", "|---|---|---|---|"]
    for label, lo, hi in (("2町未満", 0, 120), ("2〜5町", 120, 300), ("5〜10町", 300, 600), ("10町以上", 600, 1e12)):
        xs = sorted(float(r["w_over_l"]) for r in rs if lo <= float(r["length_ken"]) < hi)
        out.append(row(label, [len(xs), f"{st.median(xs):.3f}", sum(x >= R0 for x in xs)]))
    return out, len(rs)


def table_appendix(rows):
    out = ["| 区域 | 代表 | コマ（巻） | 記録の寸法 | 長さ 間 | 幅 間 | 比 | 幅「平均」 | 出所 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(row(r["area"], ["○" if r["role"] == "代表" else "", f"{r['koma']}（{VOL[r['pid']]}）", r["record"],
                                   f"{float(r['length_ken']):.0f}", f"{float(r['width_ken']):.0f}", f"{ratio(r):.3f}",
                                   "○" if r["width_is_average"] == "True" else "", r["origin"]]))
    return out


ORIGIN_EN = {"全文36件": "full-text re-extraction", "旧台帳": "first ledger", "横・竪の取りこぼし": "missed 横/竪 forms",
             "手で読んだ記録": "read by hand", "卅・巾の取りこぼし": "missed 卅/巾 forms", "里の取りこぼし": "missed widths in ri",
             "外し誤りの訂正": "wrongly excluded, restored"}


def table_appendix_en(rows):
    """付表の英語版。区域名は area_en、記録の寸法は原文（日本語）のまま"""
    from area_en import area_en
    out = ["| Area | Rep. | Frame (vol.) | Recorded dimensions (original) | Length (ken) | Width (ken) | Ratio | Mean stated | Source |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(row(area_en(r["area"]), ["✓" if r["role"] == "代表" else "", f"{r['koma']} ({VOL[r['pid']].replace('第', '')})", r["record"],
                                            f"{float(r['length_ken']):.0f}", f"{float(r['width_ken']):.0f}", f"{ratio(r):.3f}",
                                            "✓" if r["width_is_average"] == "True" else "", ORIGIN_EN[r["origin"]]]))
    return out


def table_wind(w):
    g = w["groups"]
    out = ["| 風の記述 | 区域数 | 中央値 | 0.392 未満 |", "|---|---|---|---|"]
    for key, label, show in (("strong", "強い", True), ("present", "風あり（強さの語なし）", True), ("none", "書かれていない", False), ("calm", "無風", False)):
        xs = g[key]
        out.append(row(label, [len(xs), f"{st.median(xs):.3f}" if xs else "—", sum(x < R0 for x in xs) if (xs and show) else "—"]))
    return out


# 英語版の表の訳語（セルごとに丸ごと置き換える。訳の無いセルはそのまま）
EN = {
    "数え方": "Count", "区域数": "Areas", "中央値": "Median", "0.392 未満": "Below 0.392", "0.37 未満": "Below 0.37", "0.499 未満": "Below 0.499",
    "幅に「平均」と明記の区域だけ": "Areas with width stated as a mean", "飛び火区域を除く（本火だけ）": "Without flying-ember areas (main fires only)",
    "長さが「延」の記録を除く": "Without lengths given as running totals (nobe)", "「平均」と書かれていない区域": "Areas without \"mean\" stated",
    "（参考）地震の夜の4区域も入れる": "(For reference) with the 4 areas of the earthquake night", "（参考）同、「平均」明記だけ": "(For reference) same, mean stated only",
    "出典の種類": "Kind of source", "見かけの中央値": "Apparent median", "物差し": "Yardstick",
    "長さ": "Length", "件数": "Records", "0.392 以上": "0.392 or more", "2町未満": "Under 2 chō", "2〜5町": "2–5 chō", "5〜10町": "5–10 chō", "10町以上": "10 chō or more",
    "風の記述": "Wind in the record", "強い": "Strong", "風あり（強さの語なし）": "Wind present (no word for strength)", "書かれていない": "Not written", "無風": "Calm",
    "記録の 幅÷長さ（3.1、全区域）": "Recorded width / length (3.1, all areas)", "同、山川と照合できた区域だけ": "Same, matched areas only",
    "記録の幅 ÷ 山川の直線": "Recorded width / Yamakawa's straight distance", "記録の面積（幅×記録の長さ）÷ 山川の直線²": "Recorded area (width × recorded length) / Yamakawa's straight distance²",
    "（探索的）15町ちょうどの値を除く30区域: 記録の比": "(Exploratory) 30 areas without 15-chō values: recorded ratio",
    "同、記録の幅 ÷ 山川の直線": "Same, recorded width / straight distance", "同、記録の面積 ÷ 山川の直線²": "Same, recorded area / straight distance²",
    KIND_LABEL["京の公家日記"]: "Diaries of Kyoto court nobles (Motohiro-kōki, Motokazu-kyōki, Kaneka-kōki; hearsay from Edo except one area seen by Motohiro in Edo)",
    KIND_LABEL["公的な書上・届・記録"]: "Official reports, notices and records (Machidoshiyori tebikae, Ryūei hinamiki, Okachikata mannenki, fire inspectors' reports, editors' headings, etc.)",
    KIND_LABEL["年表・炎上鑑"]: "Chronologies and fire annals (Nendai enjōkan, Tenkyō Azuma kagami, Zoku Bukō nenpyō, etc.)",
    KIND_LABEL["月堂見聞集"]: "Getsudō kenmonshū", KIND_LABEL["その他の日記"]: "Other diaries and essays",
}


def to_en(line):
    if not line.startswith("|") or set(line) <= set("|-"):
        return line
    cells = line.strip("|").split(" | ")
    cells = [EN.get(c.strip(), c.strip()) for c in cells]
    cells = [re.sub(r"^全(\d+)区域$", r"All \1 areas", c) for c in cells]
    return "| " + " | ".join(cells) + " |"


def replace_table(lines, new):
    """見出し行（列名の行）が同じ表を探し、表の行をまるごと入れ替える"""
    head = new[0]
    i = lines.index(head)
    j = i
    while j < len(lines) and lines[j].startswith("|"):
        j += 1
    lines[i:j] = new


def sigma_for(target, logs):
    """誤差の模擬計算で、見かけの中央値が target まで下がる σ（二分法。中央値は σ について単調に下がる）"""
    from error_sim import median_ratio
    lo, hi = 0.0, 1.5
    for _ in range(14):
        mid = (lo + hi) / 2
        if median_ratio(mid, logs)[0] > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


ERA_START = {"明暦": 1655, "寛文": 1661, "延宝": 1673, "天和": 1681, "貞享": 1684, "元禄": 1688, "宝永": 1704,
             "正徳": 1711, "享保": 1716, "元文": 1736, "寛保": 1741, "延享": 1744, "寛延": 1748, "宝暦": 1751, "明和": 1764,
             "安永": 1772, "天明": 1781, "寛政": 1789, "享和": 1801, "文化": 1804, "文政": 1818, "天保": 1830, "弘化": 1844,
             "嘉永": 1848, "安政": 1854, "万延": 1860, "文久": 1861, "元治": 1864, "慶応": 1865, "明治": 1868}


def year(area):
    """区域名の元号と年から西暦（年の初めで数える。改元の年のずれは時代分けに効かない）"""
    m = re.match(r"(\D{2})(元|\d+)(?:〜\d+)?年", area)
    assert m and m.group(1) in ERA_START, f"区域名から年が読めない: {area}"
    return ERA_START[m.group(1)] + (0 if m.group(2) == "元" else int(m.group(2)) - 1)


def table_sim():
    from error_sim import median_ratio, recorded_log_lengths
    logs = recorded_log_lengths(str(HERE / "hensai_shapes.csv"))
    ss = (0.15, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0)
    return ["| σ | " + " | ".join(str(x) for x in ss) + " |", "|---" * (len(ss) + 1) + "|",
            "| 見かけの中央値 | " + " | ".join(f"{median_ratio(x, logs)[0]:.3f}" for x in ss) + " |"]


def boot_ci(xs, n=10000, seed=1):
    """中央値のブートストラップ95%区間（百分位法）"""
    import random
    rng = random.Random(seed)
    m = sorted(st.median(rng.choices(xs, k=len(xs))) for _ in range(n))
    return m[int(0.025 * n)], m[int(0.975 * n)]


def cluster_ci(pairs, n=10000, seed=1):
    """(まとまりの鍵, 値) の組から、まとまりごと引き直す中央値のブートストラップ95%区間"""
    import random
    cl = {}
    for k, v in pairs:
        cl.setdefault(k, []).append(v)
    keys = list(cl)
    rng = random.Random(seed)
    m = sorted(st.median([v for k in rng.choices(keys, k=len(keys)) for v in cl[k]]) for _ in range(n))
    return m[int(0.025 * n)], m[int(0.975 * n)]


def sign_p(xs, c=R0):
    """符号検定（両側）: 中央値が c と等しいとして、c 未満の数がこれ以上偏る確率"""
    from math import comb
    n = sum(x != c for x in xs)
    k = sum(x < c for x in xs)
    tail = sum(comb(n, i) for i in range(max(k, n - k), n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fmt_p(p):
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def alexander_wind(r):
    """平均幅÷長さ r の楕円を、林野火災の L/B = 1 + 0.00120 W^2.154（Alexander 1985、W は10 m 高の風速 km/h）に当てはめた風速 m/s"""
    lb = math.pi / (4 * r)  # 楕円の 平均幅÷長さ = (π/4)·B/L
    return ((lb - 1) / 0.00120) ** (1 / 2.154) / 3.6


def alexander_values(allr):
    lo, hi = boot_ci(allr)
    return {"alex_lb": f"{math.pi / (4 * st.median(allr)):.1f}", "alex_w": f"{alexander_wind(st.median(allr)):.0f}",
            "alex_w_lo": f"{alexander_wind(hi):.0f}", "alex_w_hi": f"{alexander_wind(lo):.0f}"}


def loo_values(reps, tags):
    """出典の種類を一つずつ除いたときの中央値の幅と、95%区間の上端の最大"""
    res = []
    for k in sorted(set(tags.values())):
        xs = [ratio(r) for r in reps if tags[r["area"]] != k]
        res.append((st.median(xs), boot_ci(xs)[1], sign_p(xs)))
    return {"loo_med_min": f"{min(m for m, _, _ in res):.3f}", "loo_med_max": f"{max(m for m, _, _ in res):.3f}",
            "loo_ci_max": f"{max(c for _, c, _ in res):.3f}", "loo_p_max": fmt_p(max(p for _, _, p in res))}


def prose_values(rows, reps, tags, ys):
    """本文の <!--n:名前-->値<!--/n--> に入れる値"""
    import math
    from statistics import NormalDist
    from error_sim import median_ratio, recorded_log_lengths

    def med(xs):
        return f"{st.median(xs):.3f}"

    def below(xs, c=R0):
        return sum(x < c for x in xs)

    allr = [ratio(r) for r in reps]
    avg = [ratio(r) for r in reps if r["width_is_average"] == "True"]
    noavg = [ratio(r) for r in reps if r["width_is_average"] != "True"]
    kind = lambda k: [ratio(r) for r in reps if tags[r["area"]] == k]  # noqa: E731
    nokuge = [ratio(r) for r in reps if tags[r["area"]] != "京の公家日記"]
    ws = [float(r["w_over_straight"]) for r in ys]
    ys15 = [r for r in ys if r["yamakawa_floor15"] != "True"]
    ws15 = [float(r["w_over_straight"]) for r in ys15]
    ks = sorted(float(r["k"]) for r in ys)
    logk15 = [math.log(float(r["k"])) for r in ys15]
    sd = st.stdev(logk15)
    q = st.quantiles(ks, n=4, method="inclusive")
    logs = recorded_log_lengths(str(HERE / "hensai_shapes.csv"))
    s_all, s_ym, s_ym15 = (sigma_for(st.median(x), logs) for x in (allr, ws, ws15))
    p2 = lambda s: f"{2 * (1 - NormalDist().cdf(math.log(2) / s)):.0%}".rstrip("%")  # noqa: E731
    yoko = [ratio(r) for r in rows if re.search("横|橫", r["record"])]
    haba = [ratio(r) for r in rows if not re.search("横|橫", r["record"])]
    era = {}
    for r in reps:
        era.setdefault(0 if year(r["area"]) <= 1719 else 1 if year(r["area"]) <= 1799 else 2, []).append(ratio(r))
    kym = [r for r in ys if tags[r["area"]] == "公的な書上・届・記録"]
    kym_w = [float(r["w_over_straight"]) for r in kym]
    kym15 = [float(r["w_over_straight"]) for r in kym if r["yamakawa_floor15"] != "True"]
    return {
        "over_n": sum(x >= R0 for x in allr),
        **{f"{n}_ci": "{:.3f}〜{:.3f}".format(*boot_ci(x)) for n, x in (("all", allr), ("ym", ws), ("ym15", ws15), ("avg", avg))},
        **{f"{n}_signp": fmt_p(sign_p(x)) for n, x in (("all", allr), ("ym", ws), ("ym15", ws15), ("avg", avg))},
        "all_cci": "{:.3f}〜{:.3f}".format(*cluster_ci([(year(r["area"]) // 10, ratio(r)) for r in reps])),
        "ym_cci": "{:.3f}〜{:.3f}".format(*cluster_ci([(year(r["area"]) // 10, float(r["w_over_straight"])) for r in ys])),
        "ym15_cci": "{:.3f}〜{:.3f}".format(*cluster_ci([(year(r["area"]) // 10, float(r["w_over_straight"])) for r in ys15])),
        "n_decades": len({year(r["area"]) // 10 for r in reps}),
        **loo_values(reps, tags),
        **alexander_values(allr),
        "ym_over_n": sum(x >= R0 for x in ws),
        "ym_over_floor": sum(float(r["w_over_straight"]) >= R0 and r["yamakawa_floor15"] == "True" for r in ys),
        "ym_over_pct": f"{1 - below(ws) / len(ws):.0%}".rstrip("%"),
        "ym_over_list": "、".join(f"{r['area']} {float(r['w_over_straight']):.2f}" + ("（山川15町）" if r["yamakawa_floor15"] == "True" else "")
                                 for r in sorted(ys, key=lambda r: -float(r["w_over_straight"])) if float(r["w_over_straight"]) >= R0),
        "kym_n": len(kym_w), "kym_med": med(kym_w), "kym_below": below(kym_w),
        "kym15_n": len(kym15), "kym15_below": below(kym15), "kym15_min": f"{min(kym15):.3f}", "kym15_max": f"{max(kym15):.3f}",
        "yoko_n": len(yoko), "yoko_med": med(yoko), "haba_n": len(haba), "haba_med": med(haba),
        **{f"era{i + 1}_n": len(era[i]) for i in range(3)}, **{f"era{i + 1}_med": med(era[i]) for i in range(3)},
        **flow_counts(rows), "n_areas": len(reps), "n_records": len(rows), "n_manual": sum(r["origin"] == "手で読んだ記録" for r in rows), "n_manual_areas": len({r["area"] for r in rows if r["origin"] == "手で読んだ記録"}), "n_shapes": len(list(csv.DictReader(open(HERE / "hensai_shapes.csv")))),
        "all_med": med(allr), "all_below": below(allr), "all_pct": f"{below(allr) / len(allr):.0%}".rstrip("%"),
        "avg_n": len(avg), "avg_med": med(avg), "avg_below": below(avg),
        "noavg_n": len(noavg), "noavg_med": med(noavg), "noavg_499": below(noavg, RMAX),
        "kou_n": len(kind("公的な書上・届・記録")), "kou_med": med(kind("公的な書上・届・記録")), "kou_below": below(kind("公的な書上・届・記録")),
        "nen_med": med(kind("年表・炎上鑑")), "kuge_n": len(kind("京の公家日記")),
        "nokuge_n": len(nokuge), "nokuge_med": med(nokuge), "nokuge_below": below(nokuge),
        "ym_n": len(ws), "ym_med": med(ws), "ym_below": below(ws), "ym_pct": f"{below(ws) / len(ws):.0%}".rstrip("%"),
        "ym15_n": len(ws15), "ym15_med": med(ws15), "ym15_below": below(ws15), "ym15_pct": f"{below(ws15) / len(ws15):.0%}".rstrip("%"),
        # 同じ照合区域での物差しの比較（査読 10/31 の指摘: 全74区域と照合38区域を比べない）
        "rec38_med": med([float(r["w_over_l"]) for r in ys]), "rec38_below": below([float(r["w_over_l"]) for r in ys]),
        "a38_med": med([float(r["w_over_l"]) * float(r["k"]) ** 2 for r in ys]),
        "a38_below": below([float(r["w_over_l"]) * float(r["k"]) ** 2 for r in ys]),
        "rec30_med": med([float(r["w_over_l"]) for r in ys15]), "rec30_below": below([float(r["w_over_l"]) for r in ys15]),
        "a30_med": med([float(r["w_over_l"]) * float(r["k"]) ** 2 for r in ys15]),
        "a30_below": below([float(r["w_over_l"]) * float(r["k"]) ** 2 for r in ys15]),
        "k_med": f"{st.median(ks):.2f}", "k_q1": f"{q[0]:.2f}", "k_q3": f"{q[2]:.2f}",
        "k15_med": f"{st.median(float(r['k']) for r in ys15):.2f}", "logk_sd": f"{sd:.2f}",
        "sim_sd": f"{median_ratio(round(sd, 2), logs)[0]:.3f}",
        "sig_all_s": f"{s_all:.1f}" if s_all >= 0.95 else f"{s_all:.2f}", "sig_ym": f"{s_ym:.2f}", "sig_ym15": f"{s_ym15:.2f}",
        "p_all": p2(s_all), "p_ym": p2(s_ym), "p_ym15": p2(s_ym15),
    }


def fill_prose(text, vals):
    missing = sorted(set(re.findall(r"<!--n:(\w+)-->", text)) - set(vals))
    assert not missing, f"値の無い印: {missing}"
    return re.sub(r"<!--n:(\w+)-->.*?<!--/n-->", lambda m: f"<!--n:{m.group(1)}-->{vals[m.group(1)]}<!--/n-->", text)


def flow_counts(rows):
    """件数の流れ: 抽出 → 長さ10町以上の候補 → 除外（分類ごと）と採用、抽出の外から足した記録（11/5 英語版の再査読）"""
    import collections
    hs = list(csv.DictReader(open(HERE / "hensai_shapes.csv")))
    cand = [r for r in hs if float(r["length_ken"]) >= 600]
    ex = list(csv.DictReader(open(HERE / "exclusions.csv")))
    same = lambda a, r: (a["pid"] == r["pid"] and int(float(a["koma"])) == int(float(r["koma"]))
                         and abs(float(a["length_ken"]) - float(r["length_ken"])) < 1 and abs(float(a["width_ken"]) - float(r["width_ken"])) < 1)
    adopted = [r for r in cand if any(same(a, r) for a in rows)]
    outside = [a for a in rows if not any(same(a, r) for r in cand)]
    assert len(adopted) + len(ex) == len(cand), (len(adopted), len(ex), len(cand))
    assert len(adopted) + len(outside) == len(rows), (len(adopted), len(outside), len(rows))
    c = collections.Counter(e["category"] for e in ex)
    key = {"安政2年10月2日 地震の夜の同時多発の火事": "ex_quake", "区域の一部": "ex_part", "複数の火事・出火の合計": "ex_sum",
           "同じ火事の別の記録": "ex_dup", "火事の途中の規模": "ex_mid", "焼け跡の寸法でない・数が読めない": "ex_other"}
    assert set(c) == set(key), set(c) ^ set(key)
    import contextlib, io
    import blind_coverage
    with contextlib.redirect_stdout(io.StringIO()):
        bc = blind_coverage.main()
    assert bc["n_audited"] == len(cand) + len(outside)
    assert bc["dis_unit"] + bc["dis_sum"] + bc["dis_mid"] == bc["n_blind_dis"], bc
    return {**{k: v for k, v in bc.items() if k != "n_audited"}, "n_cand": len(cand), "n_excl": len(ex), "n_adopt_ext": len(adopted), "n_outside": len(outside),
            "n_outside_hand": sum(a["origin"] == "手で読んだ記録" for a in outside), "n_audited": len(cand) + len(outside),
            **{key[k]: v for k, v in c.items()}}


def main():
    rows, reps, tags, ys = load()
    short, n_short_avg = table_short()
    lines = PAPER.read_text().split("\n")
    from wind_vs_shape import summary as wind_summary
    wind = wind_summary()
    for t in (table_main(reps), table_source(reps, tags), table_yamakawa(reps, ys), short, table_wind(wind), table_sim(), table_appendix(rows)):
        replace_table(lines, t)
    vals = prose_values(rows, reps, tags, ys)
    vals.update(wind_n=wind["n_written"], wind_strong=len(wind["groups"]["strong"]), wind_read=wind["n_read"],
                wind_rho=f"{wind['rho']:+.2f}", wind_p=f"{wind['p']:.2f}")
    text = fill_prose("\n".join(lines), vals)
    if "--dry-run" not in sys.argv:
        PAPER.write_text(text)
    # 英語版（paper_en.md、11/5 から）: 同じ名前の印に同じ値を入れる。範囲の「〜」は en dash に
    en = HERE / "paper_en.md"
    if en.exists():
        ven = {k: str(v).replace("〜", "–") for k, v in vals.items()}
        from area_en import area_en
        ven["ym_over_list"] = "; ".join(f"{area_en(r['area'])} {float(r['w_over_straight']):.2f}" + (" (Yamakawa 15 chō)" if r["yamakawa_floor15"] == "True" else "")
                                        for r in sorted(ys, key=lambda r: -float(r["w_over_straight"])) if float(r["w_over_straight"]) >= R0)
        bad = [k for k, x in ven.items() if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", x) and f"<!--n:{k}-->" in en.read_text()]
        assert not bad, f"英語版に日本語の値が入る印: {bad}"
        elines = en.read_text().split("\n")
        for t in (table_main(reps), table_source(reps, tags), table_sim(), table_yamakawa(reps, ys), short, table_wind(wind)):   # 訳語のある表だけ（訳し進めたら足す）
            et = [to_en(x) for x in t]
            if et[0] in elines:
                replace_table(elines, et)
        ta = table_appendix_en(rows)
        if ta[0] in elines:
            replace_table(elines, ta)
        ten = fill_prose("\n".join(elines), ven)
        if "--dry-run" not in sys.argv:
            en.write_text(ten)
        print(f"英語版: 印 {len(re.findall(r'<!--n:(\w+)-->', ten))} 個を埋めた")

    # 本文に書く数の一覧（差し込まない。原稿の本文と見比べる）
    allr = sorted(ratio(r) for r in reps)
    ks = [float(r["k"]) for r in ys]
    ks15 = [float(r["k"]) for r in ys if r["yamakawa_floor15"] != "True"]
    shapes = list(csv.DictReader(open(HERE / "hensai_shapes.csv")))
    over = sorted((r for r in reps if ratio(r) >= R0), key=lambda r: -ratio(r))
    print(f"記録 {len(rows)}・区域 {len(reps)}・抽出 {len(shapes)}件（幅平均 {n_short_avg}件）")
    print(f"全区域 中央値 {st.median(allr):.3f}、0.392未満 {sum(x < R0 for x in allr)}（{sum(x < R0 for x in allr) / len(allr):.0%}）")
    print(f"山川 k 中央値 {st.median(ks):.2f}（15町除く {st.median(ks15):.2f}）")
    print(f"0.392 以上 {len(over)}区域: " + "、".join(f"{r['area']} {ratio(r):.3f}" for r in over))
    if "--check" in sys.argv:
        text = PAPER.read_text()
        for pat in (rf"{len(reps)}区域", f"{st.median(allr):.3f}", f"監査した{len(rows)}記録"):
            print(f"  原稿に「{pat}」: {'あり' if re.search(pat, text) else 'なし'}")


if __name__ == "__main__":
    main()
