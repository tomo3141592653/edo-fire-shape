"""49区域の代表記録を、山川（1881）の焼失直距離（大橋2011 付録1、yamakawa_ohashi2011.json）と和暦の年月日で突き合わせる。

出力: vs_yamakawa.csv（記録の長さ÷山川の直線 k、幅÷山川の直線）
区域名に日が無いもの（「享保8年2月」など）は手で山川の番号を当てる（HAND）。
山川の距離は火事全体の出火点→最遠点なので、飛び火区域・本火だけの区域とは比べない（SKIP）。
"""
import csv
import json
import math
import re
import statistics as st
from pathlib import Path

from ohashi_area import OHASHI

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
N = str.maketrans({"祿": "禄", "寳": "宝", "寶": "宝", "應": "応", "德": "徳", "曆": "暦", "萬": "万"})
K = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
HAND = {"正徳5〜6年 鍛冶橋・京橋（コマ326）": 26}
# 飛び火区域と、飛び火区域を別に持つ火事の本火は、山川の全体の距離と比べられない
# 延享3年: 山川の7.6kmは翌朔日の浅草花川戸の出火〜橋場まで含む。届け書の範囲（築地→馬喰町四丁目）は直線約3km
# 享保16年4月15日: 目白台の火は市谷田町で止まり（3km弱）、山川の60町（6.5km）は同日の麹町→芝の火事と一つにした距離と見る
SKIP = ("丸山火事", "明石屋火事", "飛び火区域", "延享3年", "享保16年4月15日")


def kn(s):
    if s.isdigit():
        return int(s)
    if s == "元":
        return 1
    if "十" in s:
        a, b = s.split("十")
        return (K[a] if a else 1) * 10 + (K[b] if b else 0)
    return K[s]


def main():
    Y = json.load(open(HERE / "yamakawa_ohashi2011.json"))
    by_no = {y["no"]: y for y in Y}
    idx = {}
    for y in Y:
        m = re.match(r"(\D+?)(\d+)", y["wareki"].translate(N))
        mo, d = y["md"].replace("閏", "").split("/")
        idx[(m[1], int(m[2]), int(mo), int(d))] = y
    out = []
    for r in csv.DictReader(open(ROOT / "edo_long_fires_v2.csv")):
        if r["role"] != "代表":
            continue
        a = r["area"].translate(N)
        y = by_no.get(HAND.get(r["area"]))
        m = re.match(r"(\D\D)(元|[一二三四五六七八九十]+|\d+)年(正|\d+)月(晦|\d+)日?", a)
        if y is None and m:
            era, yr, mo, d = m[1], kn(m[2]), 1 if m[3] == "正" else int(m[3]), m[4]
            c = [idx[k] for k in idx if k[:3] == (era, yr, mo) and (d == "晦" or abs(k[3] - int(d)) <= 1)]
            y = c[0] if c else None
        if any(s in r["area"] for s in SKIP):
            y = None
        L = float(r["length_ken"]) * 1.818 / 1000
        W = float(r["width_ken"]) * 1.818 / 1000
        # 山川の15町ちょうどは下限の値。大橋（2011）が地図で測り直した火事は、その距離を使う
        remeasured = bool(y) and y["cho"] == 15 and y["no"] in OHASHI
        D = OHASHI[y["no"]][1] if remeasured else (y["km"] if y else None)
        out.append(dict(area=r["area"], record=r["record"], w_over_l=r["w_over_l"], width_is_average=r["width_is_average"],
                        length_km=round(L, 2), yamakawa_no=y["no"] if y else "", yamakawa_km=D if y else "",
                        k=round(L / D, 2) if y else "", w_over_straight=round(W / D, 3) if y else "",
                        yamakawa_floor15=bool(y) and y["cho"] == 15 and not remeasured,
                        straight_src="大橋2011の測り直し" if remeasured else ("山川1881" if y else "")))
    with open(HERE / "vs_yamakawa.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    hit = [o for o in out if o["k"] != ""]
    ks = [o["k"] for o in hit]
    ws = sorted(o["w_over_straight"] for o in hit)
    print(f"{len(hit)}/{len(out)} 区域が山川の表と一致")
    q = st.quantiles(ks, n=4, method="inclusive")  # paper_numbers.py と同じ数え方
    print(f"k 中央値 {st.median(ks):.2f}（四分位 {q[0]:.2f}〜{q[2]:.2f}）")
    print(f"幅÷山川の直線: 中央値 {st.median(ws):.3f}  0.392未満 {sum(x < 0.392 for x in ws)}/{len(ws)}  0.499未満 {sum(x < 0.499 for x in ws)}")
    # 山川の表は89件中13件がちょうど15町（大火の定義の閾値）。下限の値とみて除いた感度
    nf = [o for o in hit if not o["yamakawa_floor15"]]
    wf = [o["w_over_straight"] for o in nf]
    lk = [math.log(o["k"]) for o in nf]
    print(f"15町ちょうどを除く: {len(nf)}区域 中央値 {st.median(wf):.3f}  0.392未満 {sum(x < 0.392 for x in wf)}"
          f"  k中央値 {st.median([o['k'] for o in nf]):.2f}  log k 標準偏差 {st.stdev(lk):.2f}")
    for o in sorted(hit, key=lambda o: -o["w_over_straight"]):
        print(f"  {o['w_over_straight']:.3f}  k={o['k']:<5} 山川No{o['yamakawa_no']:<3} {o['area']}  {o['record']}")


if __name__ == "__main__":
    main()
