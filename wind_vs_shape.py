"""代表記録の 幅÷長さ を、同じ火事の風の記述（監査・codex 盲検で読んだもの）の強さで分けて比べる。

風の分類: 「烈・大風・強・猛・はげし・激・颶・吹詰」があれば強、ほかに「風」の字があれば風あり、無ければ記載なし。
順位相関（記載なし=0, 風あり=1, 強=2 と 比）と、強と記載なしの中央値の差の並べ替え検定（2万回）。
"""
import csv
import json
import random
import re
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent


def winds():
    W = {}
    for r in csv.DictReader(open(HERE / "edo_long_fires_13.csv")):
        W[(r["pid"], r["koma"], r["record"])] = r["wind"]
    for d in ("codex_check_full", "codex_check_ri", "codex_check_yoko"):
        raw = (HERE / d / "codex_out.txt").read_text()
        a = {x["id"]: x for x in json.loads(raw[raw.index("["):raw.rindex("]") + 1])}
        for r in csv.DictReader(open(HERE / d / "index.csv")):
            W[(r["pid"], r["koma"], r["text"])] = a[int(r["id"])].get("wind") or ""
    return W


def wide_levels():
    """広い本文（前1800字と前のコマ）で読み直した風（codex_check_wind）。あればこちらを使う。area → 0/1/2、書かれていなければ None"""
    m = {"strong": 2, "present": 1, "calm": 0, "none_written": None}
    out = {}
    # あとから台帳に足した区域は codex_check_wind_add（make_wind_prompt.py で同じ形の問い）。codex の答えがあればそれ、無ければ Opus の答え
    dirs = [("codex_check_wind", ("codex_out.txt",))] + [(p.name, ("codex_out.txt", "opus_out.json")) for p in sorted(HERE.glob("codex_check_wind_add*"))]
    for d, names in dirs:
        f = next((HERE / d / n for n in names if (HERE / d / n).exists() and (HERE / d / n).read_text().strip()), None)
        if f is None:
            continue
        raw = f.read_text()
        a = {int(x["id"]): x for x in json.loads(raw[raw.index("["):raw.rindex("]") + 1])}
        out.update({r["area"]: m[a[int(r["id"])]["strength"]] for r in csv.DictReader(open(HERE / d / "index.csv"))})
    return out or None


def level(w):
    if re.search(r"烈|大風|强|強|猛|はげし|激|颶|吹詰", w):
        return 2
    if "風" in w:
        return 1
    return 0


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return num / (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5


def summary():
    """原稿の 3.6 の表と本文の数（paper_numbers.py が使う）。広い本文で読んだ風だけを使う"""
    wide = wide_levels()
    reps = [r for r in csv.DictReader(open(HERE / "edo_long_fires_v2.csv")) if r["role"] == "代表"]
    groups = {"strong": [], "present": [], "none": [], "calm": []}
    rows = []
    for r in reps:
        if r["area"] not in wide:
            continue
        lv, v = wide[r["area"]], float(r["w_over_l"])
        groups[{2: "strong", 1: "present", 0: "calm", None: "none"}[lv]].append(v)
        if lv is not None:
            rows.append((lv, v))
    ls, ys = [l for l, _ in rows], [v for _, v in rows]
    rho = spearman(ls, ys)
    rng = random.Random(1)
    p = sum(abs(spearman(ls, rng.sample(ys, len(ys)))) >= abs(rho) for _ in range(5000)) / 5000
    return dict(groups=groups, n_read=sum(len(g) for g in groups.values()), n_written=len(rows), rho=rho, p=p,
                n_unread=len(reps) - sum(r["area"] in wide for r in reps))


def main():
    W = winds()
    wide = wide_levels()
    rows = []
    for r in csv.DictReader(open(HERE / "edo_long_fires_v2.csv")):
        if r["role"] != "代表":
            continue
        if wide is not None:
            lv = wide.get(r["area"])
            if lv is None:  # この火事の風が本文に書かれていない区域は比べない
                continue
            rows.append((lv, float(r["w_over_l"]), r["area"], ""))
            continue
        w = W.get((r["pid"], r["koma"], r["record"]))
        if w is None:
            continue
        rows.append((level(w), float(r["w_over_l"]), r["area"], w))
    for lv, name in ((0, "記載なし（広い本文では無風）"), (1, "風あり"), (2, "強")):
        xs = [v for l, v, *_ in rows if l == lv]
        if xs:
            print(f"{name}: {len(xs)}区域 中央値 {st.median(xs):.3f}  0.392未満 {sum(x < 0.392 for x in xs)}")
    rho = spearman([l for l, *_ in rows], [v for _, v, *_ in rows])
    rng = random.Random(1)
    ys = [v for _, v, *_ in rows]
    ls = [l for l, *_ in rows]
    n_ge = sum(abs(spearman(ls, rng.sample(ys, len(ys)))) >= abs(rho) for _ in range(5000))
    print(f"順位相関 ρ = {rho:.3f}（並べ替え5000回で |ρ| 以上の割合 {n_ge / 5000:.4f}、{len(rows)}区域）")
    a = [v for l, v, *_ in rows if l == 2]
    # 広い本文で読み直した場合、0（無風と明記）はごく少ないので「風あり」と比べる
    base = 0 if sum(l == 0 for l, *_ in rows) >= 5 else 1
    b = [v for l, v, *_ in rows if l == base]
    d = st.median(b) - st.median(a)
    pool = a + b
    cnt = 0
    for _ in range(20000):
        rng.shuffle(pool)
        if st.median(pool[len(a):]) - st.median(pool[:len(a)]) >= d:
            cnt += 1
    print(f"中央値の差（{['記載なし', '風あり'][base]} − 強）= {d:.3f}、片側の並べ替え p = {cnt / 20000:.4f}")
    # 出典の種類（source_tags.csv）で層に分け、層の中だけで比を並べ替える。公的な記録が風を書かず太いことの交絡を除く
    T = {x["area"]: x["kind_auto"] for x in csv.DictReader(open(HERE / "source_tags.csv"))}
    strata = {}
    for i, (_, _, area, _) in enumerate(rows):
        strata.setdefault(T[area], []).append(i)
    ys = [v for _, v, *_ in rows]
    n_ge = 0
    for _ in range(5000):
        perm = ys[:]
        for idx in strata.values():
            vals = [ys[i] for i in idx]
            rng.shuffle(vals)
            for i, v in zip(idx, vals):
                perm[i] = v
        n_ge += spearman(ls, perm) <= rho
    print(f"出典の層の中だけで並べ替えた片側 p（ρ が観測以下になる割合）= {n_ge / 5000:.4f}")


if __name__ == "__main__":
    main()
