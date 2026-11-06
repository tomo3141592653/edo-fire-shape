"""横の壁で延焼を止める単純な模型（研究ノート用の当たりづけ）。

風下へ頭が速さ V1 で進み、各地点は火が着いてから横へ V2 で広がる（浜田式の比 V1/V2≈3.3）。
時刻 t0 から、火元側から順に両脇へ壁を築き、壁の先端は σ/2 の速さで風下へ進む（壁の合計の速さ σ）。
地点 x の片側の幅は V2 × (壁が届く時刻 − 火が着く時刻)。壁が届かないまま T になれば T まで広がる。
平均幅÷長さを、σ/V1 と T/t0 の関数で見る。
"""
import numpy as np


def ratio(sig_over_v1, T_over_t0, v2_over_v1=1 / 3.3, n=4000):
    V1, t0 = 1.0, 1.0
    T = T_over_t0 * t0
    L = V1 * T
    x = (np.arange(n) + 0.5) / n * L
    t_ign = x / V1
    t_wall = t0 + 2 * x / (sig_over_v1 * V1)
    t_stop = np.minimum(np.maximum(t_wall, t_ign), T)
    half = v2_over_v1 * V1 * (t_stop - t_ign)
    return (2 * half).mean() / L


if __name__ == "__main__":
    print("消火なし（σ=0）:", round(ratio(1e-9, 4), 3))
    print("σ/V1   T/t0=2   4     8")
    for s in (0.5, 1, 2, 3, 5):
        print(f"{s:4}  " + "  ".join(f"{ratio(s, k):.3f}" for k in (2, 4, 8)))
