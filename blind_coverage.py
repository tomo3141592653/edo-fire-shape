"""監査した記録（長さ10町以上の候補＋型の外から足した記録）のうち、別モデルの盲検で読ませたものを数える（11/5、英語版の再査読「盲検の範囲が全候補のどこまでか」）。

盲検の問いは codex_check_*/ に残っている（風だけを問うものは除く）。各フォルダの対象の記述の文字列を集め、
監査した記録の文字列と、句読点・空白を除いて片方がもう片方を含むかで照合する。Opus も読んだフォルダは opus_out.json の有無で見る。
旧台帳（最初の23件＋1）は edo_long_fires_13.csv の whole_fire_codex 列が盲検の跡。
"""
import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
norm = lambda t: re.sub(r"[\s、。，,.・·「」〔〕()（）\[\]]|<[^>]*>", "", t).replace("縦", "縱").replace("横", "橫")


def blind_texts():
    out = []  # (フォルダ, 文字列, Opus も読んだか)
    for d in sorted(HERE.glob("codex_check_*")):
        if "wind" in d.name or not d.is_dir():
            continue
        opus = (d / "opus_out.json").exists() and (d / "opus_out.json").read_text().strip() != ""
        texts = []
        if (d / "index.csv").exists():
            texts = [r["text"] for r in csv.DictReader(open(d / "index.csv"))]
        if (d / "audit.csv").exists():
            texts = [r["text"] for r in csv.DictReader(open(d / "audit.csv"))]
        if not texts and (d / "prompt.md").exists():
            texts = re.findall(r"対象の記述: 「(.+?)」", (d / "prompt.md").read_text())
        ans = codex_answers(d)
        if (d / "audit.csv").exists():
            ans = {i + 1: {"whole_fire": r["codex_whole"] == "True"} for i, r in enumerate(csv.DictReader(open(d / "audit.csv")))}
        out += [(d.name, t, opus, ans.get(i + 1, {}).get("whole_fire")) for i, t in enumerate(texts)]
    for r in csv.DictReader(open(HERE / "edo_long_fires_13.csv")):
        if r["whole_fire_codex"]:
            out.append(("edo_long_fires_13", r["record"], False, r["whole_fire_codex"] == "True"))
    return out


def codex_answers(d):
    """codex の答え（JSON 配列）を id → dict で。無ければ空"""
    import json
    for name in ("codex_result.json", "codex_out.txt"):
        f = d / name
        if f.exists():
            raw = f.read_text()
            try:
                return {int(x["id"]): x for x in json.loads(raw[raw.index("["):raw.rindex("]") + 1])}
            except ValueError:
                continue
    return {}


def audited():
    hs = [r for r in csv.DictReader(open(HERE / "hensai_shapes.csv")) if float(r["length_ken"]) >= 600]
    v2 = list(csv.DictReader(open(HERE / "edo_long_fires_v2.csv")))
    same = lambda a, r: (a["pid"] == r["pid"] and int(float(a["koma"])) == int(float(r["koma"]))
                         and abs(float(a["length_ken"]) - float(r["length_ken"])) < 1 and abs(float(a["width_ken"]) - float(r["width_ken"])) < 1)
    recs = [("候補", r["text"], any(same(a, r) for a in v2)) for r in hs]
    recs += [("型の外", a["record"], True) for a in v2 if not any(same(a, r) for r in hs)]
    return recs


def main():
    B = blind_texts()
    rows = []
    for kind, text, adopted in audited():
        n = norm(text)
        hits = [(d, o, w) for d, t, o, w in B if norm(t) and (norm(t) in n or n in norm(t))]
        rows.append((kind, adopted, text, hits))
    tot = len(rows)
    blind = [r for r in rows if r[3]]
    both = [r for r in rows if any(o for _, o, _ in r[3])]
    print(f"監査 {tot}件、盲検で読ませた {len(blind)}件、うち Opus も {len(both)}件")
    for kind in ("候補", "型の外"):
        for ad in (True, False):
            sub = [r for r in rows if r[0] == kind and r[1] == ad]
            if sub:
                print(f"  {kind}・{'採用' if ad else '除外'}: {len(sub)}件中 盲検 {sum(1 for r in sub if r[3])}・Opus も {sum(1 for r in sub if any(o for _, o, _ in r[3]))}")
    # 全体か部分か: codex の答えと最終の扱い（採用＝全体、除外のうち区域の一部・合計・途中＝全体でない）を比べる
    ex = {norm(r["text"]): r["category"] for r in csv.DictReader(open(HERE / "exclusions.csv"))}
    notwhole = {"区域の一部", "複数の火事・出火の合計", "火事の途中の規模", "安政2年10月2日 地震の夜の同時多発の火事"}
    comp = dis = 0
    dis_kind = {"adopted": 0, "sum": 0, "mid": 0}
    # codex が一部と読んだが採った記録の、採った単位（11/5 英語版の再査読で列挙を求められた。台帳の note と監査表の理由を読んで手で付けた）
    UNIT = {"長三十町程幅平均三丁": "main", "幅九町長二十五丁": "main", "幅三町程長十一町": "main", "幅八町餘、長二十五町": "main",
            "幅三十間餘、長三十一町": "main", "幅四町餘長サ二拾丁": "main",
            "幅七丁深川之方平均長二十一丁": "ember", "幅二町餘、長四十町": "ember", "幅壹里程、長サ壹里半": "ember",
            "長十三丁幅二丁": "separate"}
    unit_kind = {"main": 0, "ember": 0, "separate": 0}
    nocomp = {}
    for kind, ad, text, hits in rows:
        ws = [w for _, _, w in hits if w is not None]
        if not ws:
            continue
        final = True if ad else (False if ex.get(norm(text)) in notwhole else None)
        if final is None:
            nocomp[ex.get(norm(text))] = nocomp.get(ex.get(norm(text)), 0) + 1
            continue
        comp += 1
        if ws[-1] != final:
            dis += 1
            if ad:
                unit_kind[next(v for k, v in UNIT.items() if norm(k) in norm(text) or norm(text) in norm(k))] += 1
            dis_kind["adopted" if ad else {"複数の火事・出火の合計": "sum", "火事の途中の規模": "mid"}.get(ex.get(norm(text)), "other")] += 1
            print(f"  食い違い: {'採用' if ad else ex.get(norm(text))} codex={ws[-1]} {text[:30]}  ({hits[-1][0]})")
    print(f"全体か部分かを比べられた {comp}件、codex と最終の扱いの食い違い {dis}件。採ったものの単位 {unit_kind}")
    print(f"盲検にかけたが比べられない {sum(nocomp.values())}件: {nocomp}")
    assert sum(unit_kind.values()) == dis_kind["adopted"] and comp + sum(nocomp.values()) == len(blind)
    for kind, ad, text, hits in rows:
        if not hits:
            print("  盲検なし:", kind, "採用" if ad else "除外", text[:40])
    return dict(n_audited=tot, n_blind=len(blind), n_blind_opus=len(both), n_blind_comp=comp, n_blind_dis=dis,
                n_blind_none=tot - len(blind), dis_unit=dis_kind["adopted"], dis_sum=dis_kind["sum"], dis_mid=dis_kind["mid"],
                dis_main=unit_kind["main"], dis_ember=unit_kind["ember"], dis_separate=unit_kind["separate"],
                nocomp_dup=nocomp.get("同じ火事の別の記録", 0), nocomp_other=nocomp.get("焼け跡の寸法でない・数が読めない", 0))


if __name__ == "__main__":
    main()
