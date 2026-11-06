"""原稿の図1: 台帳の全区域の 幅÷長さ を三つの物差しで並べ、浜田式の下限と比べる。

横軸は区域（記録の比の小さい順）、縦軸は比。
- 黒丸: 記録の 幅÷長さ（edo_long_fires_v2.csv の代表）
- 白抜きの丸: 記録の幅 ÷ 山川（1881）の直線距離（straight_check/vs_yamakawa.csv、15町ちょうどの値は灰色）
- 菱形: 大橋（2011）の復元面積 ÷ 直線²（5件）
- 横線: 浜田式の既定の下限 0.392、帯: 家屋の寸法3組での範囲 0.385〜0.476
出力: fig_main_v2.png
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "straight_check"))
from ohashi_area import OHASHI  # noqa: E402

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f.replace(" ", "") or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"

INK, MUTED, ACCENT, BAND = "#1f2328", "#8a8f98", "#b5452a", "#f3e3dc"
# 大橋の番号 → 区域名（edo_long_fires_v2.csv の area）
OHASHI_AREA = {78: "天保9年4月17日", 85: "安政2年3月2日 小網町", 87: "安政5年11月15日", 88: "安政6年2月22日 青山"}


def main():
    reps = [r for r in csv.DictReader(open(HERE / "edo_long_fires_v2.csv")) if r["role"] == "代表"]
    reps.sort(key=lambda r: float(r["w_over_l"]))
    pos = {r["area"]: i for i, r in enumerate(reps)}
    ys = {r["area"]: r for r in csv.DictReader(open(HERE / "straight_check" / "vs_yamakawa.csv")) if r["k"]}

    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.axhspan(0.385, 0.476, color=BAND, zorder=0, lw=0)
    ax.axhline(0.392, color=ACCENT, lw=1.6, zorder=1)
    ax.text(0, 0.485, "浜田式の下限 0.392（帯は家屋の寸法3組で 0.385〜0.476）",
            color=ACCENT, fontsize=9, ha="left", va="bottom")

    for r in reps:
        x = pos[r["area"]]
        y = ys.get(r["area"])
        if y:
            v = float(y["w_over_straight"])
            ax.plot([x, x], [float(r["w_over_l"]), v], color=MUTED, lw=0.8, zorder=2)
            floor = y["yamakawa_floor15"] == "True"
            ax.scatter(x, v, s=42, facecolor="white", edgecolor=MUTED if floor else INK, lw=1.4, zorder=3)
    ax.scatter(range(len(reps)), [float(r["w_over_l"]) for r in reps], s=30, color=INK, zorder=4)
    for no, area in OHASHI_AREA.items():
        name, D, A, _ = OHASHI[no]
        ax.scatter(pos[area], A / D ** 2, marker="D", s=46, color=ACCENT, zorder=5)

    ax.set_xlim(-1, len(reps))
    ax.set_ylim(0, 1.1)
    ax.set_xticks([])
    ax.set_xlabel(f"区域（記録の 幅÷長さ の小さい順、{len(reps)}区域）", color=INK)
    ax.set_ylabel("幅 ÷ 長さ", color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e8eb", lw=0.8)
    ax.set_axisbelow(True)
    handles = [
        plt.Line2D([], [], marker="o", ls="", color=INK, ms=6, label="記録の 幅÷長さ"),
        plt.Line2D([], [], marker="o", ls="", mfc="white", mec=INK, mew=1.4, ms=7, label="記録の幅 ÷ 山川の直線距離"),
        plt.Line2D([], [], marker="o", ls="", mfc="white", mec=MUTED, mew=1.4, ms=7, label="同（山川の値が閾値の15町ちょうど）"),
        plt.Line2D([], [], marker="D", ls="", color=ACCENT, ms=6, label="大橋の復元面積 ÷ 直線距離²"),
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=9)
    fig.tight_layout()
    out = HERE / "fig_main_v2.png"
    fig.savefig(out, dpi=160)
    print(out)


if __name__ == "__main__":
    main()
