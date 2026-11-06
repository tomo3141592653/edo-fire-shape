"""記録の誤差と「長さ10町以上」で選ぶことだけで、比の中央値がどこまで下がって見えるか。

本当の形がすべて浜田式の下限（平均幅÷長さ = R0）だとする。
- 本当の長さ L: 対数正規。記録された 167 件（hensai_shapes.csv）の log 長さの平均 m・分散 s² から、
  記録の誤差の分 σ² を引いた分散 s² − σ² を持つ（記録 = 本当 × 誤差、なので分散は足し算）
- 記録の長さ L' = L·exp(σ·ε1)、記録の幅 W' = R0·L·exp(σ·ε2)（ε1, ε2 は独立な標準正規）
- 記録の長さで L' ≥ 600 間（10町）の火事を選び、W'/L' の中央値を見る

誤差は中央値ゼロなので、選ばなければ比の中央値は R0 のまま。下がるのは、記録の長さで選ぶと
長さを大きく書かれた火事が選ばれやすく、分母が大きく出るため（選択による偏り）。
"""
import csv
import math
import sys

import numpy as np

R0 = 0.392  # 浜田式（P2、風速5〜30 m/s、4〜8時間）の連続範囲での最小 0.3922
CUT = 600.0  # 10町（間）


def recorded_log_lengths(path="hensai_shapes.csv"):
    with open(path) as f:
        return np.log([float(r["length_ken"]) for r in csv.DictReader(f) if float(r["length_ken"]) > 0])


def median_ratio(sigma, logs, n=2000, reps=200, seed=1):
    rng = np.random.default_rng(seed)
    m, s2 = logs.mean(), logs.var()
    if sigma ** 2 >= s2:
        return float("nan"), 0.0
    sd_true = math.sqrt(s2 - sigma ** 2)
    meds, kept = [], []
    for _ in range(reps):
        L = np.exp(rng.normal(m, sd_true, n))
        Lr = L * np.exp(sigma * rng.normal(size=n))
        Wr = R0 * L * np.exp(sigma * rng.normal(size=n))
        sel = Lr >= CUT
        if sel.sum() >= 5:
            meds.append(np.median(Wr[sel] / Lr[sel]))
            kept.append(sel.mean())
    return float(np.median(meds)), float(np.mean(kept))


def _tests():
    logs = recorded_log_lengths()
    # 誤差なしなら選んでも比は R0 のまま
    assert abs(median_ratio(0.0, logs, reps=20)[0] - R0) < 1e-9
    # 誤差が大きいほど見かけの中央値は下がる
    a, b = median_ratio(0.2, logs, reps=50)[0], median_ratio(0.8, logs, reps=50)[0]
    assert b < a < R0


if __name__ == "__main__":
    if "--test" in sys.argv:
        _tests()
        print("ok")
        sys.exit()
    logs = recorded_log_lengths()
    print(f"記録 {len(logs)} 件: log長さの平均 {logs.mean():.3f}、標準偏差 {logs.std():.3f}（長さの中央値 {math.exp(np.median(logs)):.0f} 間）")
    print("σ（対数）  見かけの中央値  10町以上に入る割合")
    for s in (0.0, 0.15, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0):
        med, frac = median_ratio(s, logs)
        print(f"{s:5.2f}      {med:.3f}          {frac:.3f}")
