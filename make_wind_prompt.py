"""風の盲検の問いを作る（codex_check_wind と同じ形）。台帳の代表のうち、まだ風を読んでいない区域だけを出す。

本文は、前のコマの末尾600字＋対象の記述の前1800字＋後80字。対象の火事は区域名（年月日）と記述で示す。
同じページの別の日の火事の風を混ぜないよう問いで頼む。出力: <out>/prompt.md と <out>/index.csv
使い方: python3 make_wind_prompt.py codex_check_wind_add
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEAD = """以下は『東京市史稿』変災篇（江戸の火災記録の史料集）の国立国会図書館OCRからの抜粋です。OCRの誤りを含みます。
各事例について、「対象の火事」（年月日と対象の記述で示す）の最中に吹いていた風を、本文から読み取ってください。同じページにある別の日の火事の風を混ぜないでください。JSONの配列で答えてください。

- id
- wind_text: この火事の風について本文に書かれた語句（原文のまま、複数あれば「／」で区切る）。見つからなければ null
- strength: "strong"（烈風・大風・風強・風はげし等、強い風と書かれている）、"present"（風向だけ、または強さの語がない）、"none_written"（この火事の風が本文に書かれていない）、"calm"（無風・風なし等と書かれている）のどれか
- note: 迷った点を一文で
"""


def pages(pid):
    t = (HERE / "ndl" / "hensai" / f"full_{pid}.txt").read_text()
    return {int(k): b for k, b in re.findall(r"--- コマ(\d+) ---\n(.*?)(?=\n--- コマ|\Z)", t, re.S)}


def find(body, record):
    """記述の位置。MANUAL の記録は画像で読んだ字なので、OCR 本文に無ければ先頭の数文字で探す"""
    for n in (len(record), 8, 5, 3, 2):
        i = body.find(record[:n])
        if i >= 0:
            return i
    return len(body) // 2


def main():
    out = HERE / sys.argv[1]
    # 読み済みの区域（codex_check_wind と codex_check_wind_add*）は除く。既存のフォルダは上書きしない（答えと番号がずれる）
    assert not (out / "index.csv").exists(), f"{out} は既にある。新しいフォルダ名を渡す"
    done = {r["area"] for d in [HERE / "codex_check_wind", *sorted(HERE.glob("codex_check_wind_add*"))] if (d / "index.csv").exists()
            for r in csv.DictReader(open(d / "index.csv"))}
    reps = [r for r in csv.DictReader(open(HERE / "edo_long_fires_v2.csv")) if r["role"] == "代表" and r["area"] not in done]
    if not reps:
        print("読んでいない区域は無い")
        return
    out.mkdir()
    P = {pid: pages(pid) for pid in ("1915668", "1915694")}
    parts, idx = [HEAD], []
    for n, r in enumerate(reps, 1):
        pg = P[r["pid"]]
        k = int(r["koma"])
        body = pg.get(k, "")
        i = find(body, r["record"])
        prev = pg.get(k - 1, "")[-600:]
        text = (prev + body[:i])[-2400:] + body[i:i + len(r["record"]) + 80]
        parts.append(f"\n### 事例 {n}\n対象の火事: {r['area']}\n対象の記述: 「{r['record']}」\n本文:\n{text}\n")
        idx.append(dict(id=n, area=r["area"], pid=r["pid"], koma=r["koma"], record=r["record"], w_over_l=r["w_over_l"]))
    (out / "prompt.md").write_text("".join(parts))
    with open(out / "index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(idx[0]))
        w.writeheader()
        w.writerows(idx)
    print(f"{len(idx)} 区域 → {out}/prompt.md")


if __name__ == "__main__":
    main()
