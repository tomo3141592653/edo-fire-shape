"""浜田式の三方向の延焼速度から、焼け跡全体の「平均幅÷全長」を出す。

江戸の記録の「長さ・幅平均」と同じ物差しにするための式。どこまでが原典で、どこからが僕の仮定かを分けて書く。

原典にあるもの（浜田 1951 を藤田 1975 の式(1)〜(4)で読んだもの。hamada.py）
  - 風下 V1 = (1+0.01t)V1*（t≦60分）、1.6V1*（t≧60分）、横 V2、風上 V3（いずれも m/min）
原典ではなく藤田 1975 の式(5)（浜田の原典は未見なので、浜田自身の形かは確かめていない）
  - 等時延焼線は火元を中心にして、風下側が半軸 (S1, S2)、風上側が (S3, S2) の半楕円二つ
僕が足した仮定
  (P1) 風向・風速は出火から燃え止まりまで一定
  (P2) 時間の係数 (1+0.01t)→1.6 は風下にだけかける（藤田の書き方どおり）。横・風上は一定速度
       → 無風でも風下が 1.6 倍に伸びて円にならない。比べるため、三方向すべてにかける版 (P2') も出す
  (P3) 焼け跡の全長 = S1+S3（風の軸に沿った長さ）、平均幅 = 面積 ÷ 全長
       面積 = (π/2)·S2·(S1+S3) なので、平均幅÷全長 = (π/2)·S2 / (S1+S3)
  (P4) 消火・燃え止まりは考えない（時刻 t で止めた形）
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hamada as H  # noqa: E402


def _dist(v, t, scaled):
    """一定速度 v で t 分。scaled のときは風下と同じ時間の係数をかける"""
    if not scaled:
        return v * t
    if t <= 60:
        return v * (t + 0.005 * t * t)
    return v * (60 + 0.005 * 3600) + 1.6 * v * (t - 60)


def extents(t, w, all_dirs_scaled=False, **kw):
    """(S1, S2, S3) [m]"""
    S1 = H.s1(t, w, **kw)
    S2 = _dist(H.v2(w, **kw), t, all_dirs_scaled)
    S3 = _dist(H.v3(w, **kw), t, all_dirs_scaled)
    return S1, S2, S3


def mean_width_ratio(t, w, all_dirs_scaled=False, **kw):
    """平均幅÷全長 = (π/2)·S2/(S1+S3)"""
    S1, S2, S3 = extents(t, w, all_dirs_scaled, **kw)
    return (math.pi / 2) * S2 / (S1 + S3)


def _tests():
    # 無風・三方向に同じ係数なら円: 平均幅÷全長 = π/4
    for t in (30, 60, 240):
        assert abs(mean_width_ratio(t, 0, all_dirs_scaled=True) - math.pi / 4) < 1e-12
    # 無風・風下だけに係数（P2）だと t≧60 で S1 が伸びて π/4 より小さい
    assert mean_width_ratio(240, 0) < math.pi / 4
    # 面積の式を数値積分で確かめる（半楕円二つ）
    S1, S2, S3 = extents(240, 15)
    n = 200000
    area = 0.0
    for i in range(n):
        x = -S3 + (S1 + S3) * (i + 0.5) / n
        a = S1 if x >= 0 else S3
        area += 2 * S2 * math.sqrt(max(0.0, 1 - (x / a) ** 2)) * (S1 + S3) / n
    assert abs(area / ((math.pi / 2) * S2 * (S1 + S3)) - 1) < 1e-4
    print("tests ok")


if __name__ == "__main__":
    _tests()
    print("平均幅÷全長（a=8 m, b=4 m, 純木造）")
    print("  w[m/s]   P2: t=1h  2h    4h    8h  | P2': t=4h")
    for w in (0, 5, 10, 15, 19, 24, 30):
        r = [mean_width_ratio(t, w) for t in (60, 120, 240, 480)]
        print(f"  {w:5.0f}   " + "  ".join(f"{x:.3f}" for x in r) + f"  |  {mean_width_ratio(240, w, True):.3f}")
