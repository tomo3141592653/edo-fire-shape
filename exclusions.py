"""長さ10町以上の抽出候補のうち台帳に採らなかった記録と、その理由を一覧にする（11/5、英語版の再査読で件数の流れを求められたため）。

理由は台帳スクリプト（build_long_fires_v2.py）の採否表と監査表から引く。引けないものは「理由の記録なし」と出す。
出力: exclusions.csv
"""
import csv
from pathlib import Path

import build_long_fires_v2 as B

HERE = Path(__file__).resolve().parent


def k(pid, koma, text):
    return (pid, str(int(float(koma))), text.strip())


reasons = {}
for r in csv.DictReader(open(HERE / "codex_check_full" / "audit.csv")):
    if B.NEW_AREA.get(r["id"]) is None:
        reasons[k(r["pid"], r["koma"], r["text"])] = ("full", r["reason"])
for name, table in (("ri", B.RI_DECISION), ("yoko", B.YOKO_DECISION), ("kin", B.KIN_DECISION)):
    for r in csv.DictReader(open(HERE / f"codex_check_{name}" / "index.csv")):
        area, why = table.get(r["id"], (None, ""))
        if area is None:
            reasons[k(r["pid"], r["koma"], r["text"])] = (name, why)

# 採否表に理由の残っていなかったものを、全文と画像で読んで分類した（11/5 19〜20時）。キーは (pid, コマ, 抽出した文字列)
D, P, Q = "同じ火事の別の記録（代表は別の記録）", "区域の一部（同じ火事を区域ごとに分けた寸法）", "地震の夜の同時多発の火事（主解析の外、参考集計）"
HAND = {
    ("1915668", "362", "幅廿町程に長百二三十町"): ("hand", D + "。享保3年5月1日 中橋、月堂見聞集「長百二三十町程の積り」は地理と合わず、萬年記の記録を代表にした"),
    ("1915668", "411", "橫五丁縱十八町"): ("hand", P + "。享保12年12月10日、伊達治家記録が麹町側と佐久間町側の二本の帯に分けて書く（codex・Opus とも一部分）"),
    ("1915668", "411", "橫二丁縱十七丁"): ("hand", P + "。同上の佐久間町〜金杉側の帯"),
    ("1915694", "311", "長凡廿三町幅員凡九町"): ("hand", D + "。天保9年4月17日の綱文、代表はコマ319"),
    ("1915694", "326", "長凡拾丁程、幅平均十間"): ("hand", P + "。在方之分"),
    ("1915694", "445", "長廿二町餘、幅員七町"): ("hand", D + "。安政5年11月15日の綱文、代表は幅を平均と明記したコマ452"),
    ("1915694", "457", "長凡一里八町、幅員平均四町"): ("hand", D + "。安政6年2月22日 青山、代表はコマ459"),
    ("1915694", "497", "長十一町、幅一町半"): ("hand", D + "。慶応2年12月29日夜 小石川白山前の綱文、代表は続武江年表のコマ504（画像に「上文春木町火災ノ記事ニ次ゲリ」）"),
}
for koma, text, why in (("417", "長三十一町十間餘、幅平均壹町四十三間", "本所深川の合計"), ("417", "幅平均二丁廿四間程、日本橋北長サ壹里二町", "日本橋北の合計"),
                        ("421", "長凡六百間程、幅平均廿間", "一つの区域、出火数不明"), ("423", "長凡拾五丁餘、幅平均七丁半", "新吉原・浅草、出火数不明"),
                        ("424", "長拾三町餘、幅平均三丁", "複数の燃え立ちをまとめた寸法"), ("424", "長貳拾壹丁拾間餘、幅平均貳丁貳拾四間", "南之方の合計"),
                        ("427", "長拾丁餘、幅平均三丁", "複数の燃え立ちをまとめた寸法"), ("427", "長三拾壹町拾間餘、幅平均壹丁四拾三間", "本所深川の合計"),
                        ("433", "長貳里拾九町の餘、幅平均よして貳町", "江戸全体の焼失を幅2町の帯に換算した長さ"), ("433", "長十三町餘、幅平均三丁", "一つの区域、出火数不明"),
                        ("434", "長十町餘、幅平均三丁", "一つの区域、出火数不明")):
    HAND[("1915694", koma, text)] = ("hand", Q + "。" + why)
for key, v in HAND.items():
    reasons.setdefault(key, v)

v2 = list(csv.DictReader(open(HERE / "edo_long_fires_v2.csv")))
old = list(csv.DictReader(open(HERE / "edo_long_fires_13.csv")))
out = []
for r in csv.DictReader(open(HERE / "hensai_shapes.csv")):
    if float(r["length_ken"]) < 600:
        continue
    if any(a["pid"] == r["pid"] and int(float(a["koma"])) == int(float(r["koma"])) and abs(float(a["length_ken"]) - float(r["length_ken"])) < 1
           and abs(float(a["width_ken"]) - float(r["width_ken"])) < 1 for a in v2):
        continue
    src, why = reasons.get(k(r["pid"], r["koma"], r["text"]), ("", ""))
    out.append(dict(pid=r["pid"], koma=r["koma"], text=r["text"], length_ken=r["length_ken"], width_ken=r["width_ken"], source=src, reason=why))
# 理由を読んで手で付けた分類（11/5）。キーは (巻のpid末尾2桁, コマ, 抽出した文字列の先頭8字)
CAT = {"quake": "安政2年10月2日 地震の夜の同時多発の火事", "part": "区域の一部", "sum": "複数の火事・出火の合計",
       "dup": "同じ火事の別の記録", "midway": "火事の途中の規模", "other": "焼け跡の寸法でない・数が読めない"}
CAT_OF = {}
for key, c in [(("68", "315"), "dup"), (("68", "362"), "dup"), (("68", "381"), "midway"), (("68", "382"), "midway"),
               (("68", "392"), "sum"), (("68", "404"), "other"), (("68", "411"), "part"), (("68", "434"), "part"),
               (("68", "435"), "part"), (("68", "436"), "part"), (("68", "444"), "part"), (("68", "456"), "other"),
               (("68", "528"), "part"), (("68", "556"), "sum"), (("68", "567"), "sum"), (("94", "65"), "midway"),
               (("94", "278"), "sum"), (("94", "311"), "dup"), (("94", "326"), "part"), (("94", "445"), "dup"),
               (("94", "457"), "dup"), (("94", "497"), "dup"), (("68", "499"), "other")]:
    CAT_OF[key] = c
for o in out:
    key = (o["pid"][-2:], str(int(float(o["koma"]))))
    if o["pid"] == "1915694" and 417 <= int(float(o["koma"])) <= 438:
        c = "quake"
    elif key == ("68", "424"):
        c = "other" if o["text"].startswith("長三十八丁") else "sum"
    else:
        c = CAT_OF[key]
    o["category"] = CAT[c]
with open(HERE / "exclusions.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
assert all(o["reason"] for o in out), [o["text"] for o in out if not o["reason"]]
print(len(out), "件、理由あり", sum(1 for o in out if o["reason"]), "件")
import collections
for c, n in collections.Counter(o["category"] for o in out).most_common():
    print(f"  {c}: {n}")
for o in out:
    if not o["reason"]:
        print("理由なし", o["pid"][-2:], o["koma"], o["text"][:30])
