"""長い火事（記録の長さ600間以上）の区域ごとの台帳を作り直す（10/30、全文から抜き直した後）。

入力:
  edo_long_fires_13.csv           — grab から作った旧台帳（24行=23火事）
  codex_check_full/audit.csv      — 全文から新しく出た36件の採否
  codex_check_ri/index.csv        — 幅の単位「里」の取りこぼし5件（採否はこのファイルの RI_DECISION）
出力:
  edo_long_fires_v2.csv           — 1行1記録。area（区域の名）ごとに代表を1行だけ role=代表 にする
  標準出力に要約（中央値・下限未満の割合）と感度

区域の単位: 1つの出火から一続きに焼けた区域。飛び火で始まった区域は別の区域として数える。
同じ区域に複数の記録があるときの代表: 幅が「平均」と明記された記録、なければ幅÷長さが大きい方（仮説に不利な側）。
"""
import csv
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
R0, RMAX = 0.392, 0.499  # 浜田式の平均幅基準の格子最小値、最大幅基準の値

# 旧台帳の区域名（era_guess + day_guess の頭）と、置き換え
OLD_AREA_OVERRIDE = {("1915668", "500"): "宝暦10年2月6日 明石屋火事 本火",
                     ("1915694", "357"): "弘化3年1月15日 丸山火事 本火",
                     ("1915694", "387"): "嘉永3年2月5日 麹町",
                     ("1915694", "459"): "安政6年2月22日 青山", ("1915694", "461"): "安政6年2月22日 青山",
                     # 変災篇は寛政11年「三月十日火災」の節に入れ、池魚録抄も寛政十一年。「寛政十二年」は歴代炎上鑑の記事に付いた年の注
                     ("1915694", "98"): "寛政11年3月10日 麻布古川新屋敷",
                     # 欄外の「慶應三年正月二日火災」は左の附記（辰の口）の見出し。白山前の記事には「上文春木町火災ノ記事ニ次ゲリ」とあり、綱文（497）は慶応2年12月29日（11/5 画像で確認）
                     ("1915694", "504"): "慶応2年12月29日夜 小石川白山前"}
# 町年寄手控の「平均幅九町長二十五丁」「(深川之方)平均…幅七丁長二十一丁」は、抜き出した文字列が「幅」から始まり「平均」が外れている
NEW_AVG = {"21", "22"}
# 引用欄に出す文字列（11/5 英語版の査読で「平均」が見えないと指摘。画像 第4巻499コマでは「平均」の下に幅と長さが2行の割注で並ぶ）
AVG_TEXT = {"21": "旅籠丁より靈岸橋迄之分 平均〔割注: 幅九町・長二十五丁〕", "22": "深川之方 平均〔割注: 幅七丁・長二十一丁〕"}

# 全文の36件: id → 区域名（None は採らない）
NEW_AREA = {
    "1": "元禄8年2月8日 四谷", "2": "元禄10年10月17日 小石川→芝", "3": "宝永4年8月1日 小石川",
    "4": "宝永4年8月1日 小石川", "5": "正徳元年1月4日 芝土器町", "6": "正徳元年1月4日 芝土器町",
    "7": "正徳4年11月25日 本所石原", "8": "正徳5年1月5日 馬喰町", "9": "正徳5〜6年 鍛冶橋・京橋（コマ326）",
    "10": "享保2年1月22日 小石川", "11": "享保2年1月 下谷・箕輪（コマ355）", "12": "享保3年5月1日 中橋",
    "13": "享保3年12月5日 小石川", "14": "享保5年7月19日 南鞘町", "18": "享保8年2月16日 赤坂伝馬町",
    "20": "享保10年2月14日 青山久保町", "21": "宝暦10年2月6日 明石屋火事 本火",
    "22": "宝暦10年2月6日 明石屋火事 深川飛び火区域", "23": "宝暦14年2月20日 神田新白銀町",
    "25": "天明3年12月20日 浅草鳥越 本所飛び火区域", "26": "天明4年12月26日 横田火事 本火",
    "27": "天明5年5月27日 横山町", "29": "寛政2年1月晦日 駒込浅嘉町 本火", "30": "文化3年3月4日 丙寅火事",
    "31": "文政12年3月21日 己丑火事", "33": "弘化元年4月5日 小石川下富坂町", "34": "弘化2年1月24日 青山火事",
    "35": "弘化3年1月15日 丸山火事 本火", "36": "嘉永3年2月5日 麹町",
}
# id12 は月堂見聞集の「長百二三十町」が地理と合わないので、同じ見開きの萬年記「凡及三十餘町、但横三四町歟」に差し替える
NEW_RECORD_TEXT = {"12": "萬年記「凡及三十餘町、但横三四町歟」（月堂見聞集は「幅廿町程に長百二三十町」）"}
NEW_VALUE_OVERRIDE = {"12": (1800, 210, "萬年記「凡及三十餘町、但横三四町歟」（月堂見聞集の長百二三十町は中橋→築地の距離と合わない）")}

# 幅の単位「里」の取りこぼし5件（codex_check_ri の判定を読んで決めた）
RI_DECISION = {
    "1": ("享保2年12月28日 牛込天龍寺前", "採る。区域名の年は月堂見聞集の記事に付いた注から享保3年と拾い違えていた（変災篇の節は享保2年「十二月廿八日火災」、柳営日次記も元天龍寺前からの出火）。長さ4里は牛込→芝海手の直線（約1.5里）より長く、延べか誇張の疑い"),
    "2": (None, "外す。明和9年の大火は目黒行人坂と本郷丸山の別々の出火の合計（武江年表「雙方の火鎭り」）"),
    "3": (None, "外す。明和9年の大火、複数の書付の数を並べた箇所で、別々の出火の合計"),
    "4": ("弘化3年1月15日 丸山火事 駿河台飛び火区域", "採る（飛び火区域）。火事場見廻の書上。火先が二口に分かれた区域の外形"),
    "5": (None, "外す。明和9年の大火、別口の出火を含む（codex も合計と判定）"),
}


# 幅を「横」、長さを「竪」と書く記録などの取りこぼし26件（codex_check_yoko、codex 盲検と本文で決めた）。値は (区域名, 理由)、区域名 None は外す
YOKO_DECISION = {
    "1": ("元禄11年9月6日 勅額火事", "京の日記（基熙公記）に届いた伝聞「竪二里許、横一里餘」"),
    "2": ("元禄11年12月10日 本石町", "年代炎上鑑「本石町二丁目より出火八丁堀迄…橫二十町長サ二里餘」"),
    "3": ("元禄12年4月4日 日本橋釘店", "年代炎上鑑「日本橋釘店〓出火、神田橋限にて燒止ル。橫十五町長サ廿七八丁」"),
    "4": ("元禄16年11月18日 四谷伊賀町", "江戸から京への書付「火本より燒留迄長サ貳里餘、横五十六町程」。同じ火事の基熙公記は「橫二十町竪二□餘」。三口に分かれた火事"),
    "5": (None, "「横二三十町」の数の読み違い（2.13）。codex の読み（25町）でも id6 と同じ火事の別記録"),
    "6": ("正徳2年2月8日 浅草→本所", "年代炎上鑑「橫三十町、長三里餘」。月堂見聞集「凡横二三十町長三里餘」"),
    "7": ("享保2年1月7日 京橋南五町目", "京の日記（兼香公記）に届いた伝聞「橫五町長二十町斗」"),
    "8": (None, "「燒ケ申いテ靜謐、其後…又々」と再燃する前の範囲（火事の途中の書付と同じ扱い）"),
    "9": ("享保10年2月14日 青山久保町", "兼香公記の注「橫十四五町長二里半」。既存区域の別記録"),
    "10": ("享保15年11月23日 四谷", "柳営日録「四谷〓出火、竪廿町·橫三丁程燒」"),
    "11": ("享保16年3月17日 芝三田新堀", "月堂見聞集「凡横二町に長さ一里程の積り」"),
    "12": (None, "検証の町積り。浅草分の一区域"), "13": (None, "検証の町積り。深川方の飛火区域"),
    "14": (None, "検証の町積り。多数の火元・飛火区域の一つ"), "15": (None, "検証の町積り。最初の区域だけ"),
    "16": (None, "「其外」の範囲で、上野御本坊などの焼失を含まない"),
    "17": (None, "続史愚抄「長二里濶九里」。京の伝聞で数が崩れている"),
    "18": ("宝暦10年2月6日 芝神明前", "「平均凡長十三丁。幅八十間」（平均は長さに付く）。明石屋火事と同じ夕方の別の火事"),
    "19": (None, "外す。OCR が割注の2行（旅籠丁より靈岸橋迄之分 平均〔幅九町・長二十五丁〕／深川之方 平均〔幅七丁・長二十一丁〕）をまたいで、本火の長さと深川の幅をつないだもの（11/5 画像 第4巻499コマで確認。以前は本火の別記録として採っていた）"),
    "20": ("文化3年3月4日 丙寅火事", "「竪二里餘り、幅十六七町」の伝聞。既存区域の別記録"),
    "21": ("文化8年2月11日 芝（コマ142）", "政鄰記「道法橫十三町、長サ一里二十丁の間燒失」"),
    "22": ("文化3年3月4日 丙寅火事", "作事方の比較「長二里半。幅七町。此坪數二百二十六萬八千坪」。既存区域の別記録"),
    "23": ("文政12年3月21日 己丑火事", "作事方の比較「長壹里。幅二拾町。此坪數二百五十九萬二千坪」。既存区域の別記録"),
    "24": ("文政12年3月21日 己丑火事", "「横壹里餘竪二里餘」。三口に分かれた火事。既存区域の別記録"),
    "25": ("天保5年2月7日 神田佐久間町", "「横十二三町、竪壹里許、丑年の大火より四分許少し。竪は佐久間町より」"),
    "26": (None, "地震の夜の本所深川の絵図七枚の合計"),
}
# 数の「卅」・幅の「巾」・「幅平均凡」の取りこぼし8件（codex_check_kin。codex が上限で使えず Opus の盲検 opus_out.json と本文・画像で決めた、10/30 17時）
KIN_DECISION = {
    "1": ("元禄16年11月29日 水戸様火事", "月堂見聞集。南は鉄砲洲・深川、北は感応寺、西は小石川・駒込・本郷と範囲を述べたあと「凡幅卅町ニ長サ三里餘積也」"),
    "2": ("正徳3年12月22日 （コマ319、推定）", "月堂見聞集「幅卅町に長さ四里程の積り」「申の下刻火留る」。焼けた町（馬喰町・浜町・小網町）が綱文の12月22日の火事と合う"),
    "3": ("享保6年2月7日 四谷中殿町", "「凡幅四五丁長サ卅丁、申下刻過留ル」。四谷中殿町→赤坂→麻布一本松の火事"),
    "4": ("享保16年4月15日 目白台", "柳営日次記。目白台→牛込を町ごとに挙げたあと「凡巾二町餘、竪三十五町程」。同日の麹町の火事は別の火元"),
    "5": (None, "画像でも「凡巾五口程、長三十八丁」で幅が読めない（麹町の火事）"),
    "6": (None, "「二口合巾三町長九十二町」。同日の別々の火元二つの合計"),
    "7": ("文化3年3月4日 丙寅火事", "3月8日付の上申「長凡三里程、幅平均凡拾町餘」。既存区域の別記録"),
    "8": (None, "安政2年10月2日の地震の夜、日本橋北の町屋だけの小計（日本橋南・本所深川が別に挙がる）"),
}
# 第4巻コマ500「神明前〓海際迄、長十三丁幅二丁」（北叟遺言）は明石屋火事の区間ではなく芝神明前の火事（最初の選定で外し誤り、10/30 15時）
EXTRA = [("宝暦10年2月6日 芝神明前", "1915668", "500", "長十三丁幅二丁", "北叟遺言「神明前〓海際迄、長十三丁幅二丁」")]

# OCR が崩れて正規表現で拾えず、画像で読んだ記録（区域名, pid, コマ, 画像で読んだ記述, 長さ間, 幅間, 幅平均, 理由）
MANUAL = [("享保12年12月6日 麹町", "1915668", "411", "縱十一丁橫一丁半許延燒", 660, 90, False,
           "伊達治家記録「麹町ヨリ赤坂邊ニ至リ、縱十一丁橫一丁半許延燒」。柳営日次記は「善國寺谷·麴町六七丁目通·〓水谷·貝坂邊、赤坂御門內武士屋敷燒失」。抽出済みだったが採否の記録が無かった（11/5 除外の洗い出しで発見、画像と codex・Opus の盲検 codex_check_unaudited/ で全体の寸法と一致）"),
          ("安政2年3月2日 小網町", "1915694", "412", "延長十三町餘幅員平均四町", 780, 240, True,
           "綱文「小網町ニ火有リ、延燒淺草藏前ニ及ブ。被害ノ町數六十八延長十三町餘幅員平均四町ニ亘ル」。OCR は「四聞」と崩れて抽出から漏れた（画像で確認、10/30 17時）"),
          ("宝暦10年2月4日 赤坂今井谷", "1915668", "488", "長平均三十三丁。但シ南北同斷。巾平均五丁", 1980, 300, True,
           "町年寄手控「二月四日出火、赤坂今井谷より海際。」の割注。OCR では割注が後ろの行と混ざり長さと幅が離れて抽出から漏れた（画像で確認、10/30 17時半）"),
          ("享保3年12月11日 上野屏風坂", "1915668", "370", "竪一里半餘、横十町程", 3240, 600, False,
           "編者の引く萬年記「東叡山屏風坂上梁善院出火、下谷·淺草·本所」の割注「亥下刻消。竪一里半餘、横十町程」。OCR は割注が本文に混ざって「竪一里若干災。半餘」と崩れた（画像で確認）"),
          ("享保5年3月27日 中橋", "1915668", "375", "長さ二里餘廣狹は所に依て十町十五町程の不同あり", 4320, 750, False,
           "月堂見聞集「凡そ長さ二里餘廣狹は所に依て十町十五町程の不同あり」。幅は所により違うと書くので10町と15町の中間（享保7年の「幅所により五町三町」と同じ扱い）"),
          ("享保6年3月3日 三河町", "1915668", "388", "大法竪三十八町程、横十五町程", 2280, 900, False,
           "天享吾妻鑑。三河町→上野→千住大橋の焼失を挙げたあと「大法」の割注「竪三十八町程。横十五町程」。OCR は割注と出典名が混ざった（画像で確認）。山川の焼失直距離も38町"),
          ("享保4年2月13日 芝三田台町", "1915668", "371", "凡長サ三十四五町餘、幅ハ所々ニヨリ二三町も、又ハ壹町も", 2070, 120, False,
           "基熙公記に届いた別紙。芝三田台町→泉岳寺→品川浜川。幅は書かれた最小1町と最大3町の中間（幅が範囲で書かれた記録は、書かれた最小と最大の中間を取る）"),
          ("文化3年3月4日 丙寅火事", "1915694", "108", "長サ凡二里餘、幅平均七町", 4320, 420, True,
           "編者の綱文「淺草新堀ニ至テ火始メテ熄ム。長サ凡二里餘、幅平均七町」。OCR は「七內町」と崩れた。既存区域の別記録"),
          ("安政元年12月28日", "1915694", "410", "長十町三十間餘、町幅平均まして四町四十間程", 630, 280, True,
           "続武江年表「町數ハ百一ヶ町、長十町三十間餘、町幅平均まして四町四十間程といふ」。OCR は行の境と月岑日記の割注「廿八日」が混ざり「廿八町三十間餘」と読めた（画像で確認）。綱文 409 と同じ寸法で、幅を平均と明記"),
          # 山川の表で照合できなかった火事の節を、ゆるい型で当たって見つけた記録（straight_check/yamakawa_unmatched_scan.py、10/30 18時）
          ("宝永7年12月19日 元誓願寺前", "1915668", "310", "三十五六丁、橫平均八九丁", 2130, 510, True,
           "基熙公記（江戸滞在中の記事）「元誓願寺前御原トイフ。松平伊豆守中屋鋪出火…卽時及大火、辰巳方、三十五六丁、橫平均八九丁云々。亥刻火消了」。長さの語が無く、幅が「橫平均」"),
          ("享保3年12月5日 小石川", "1915668", "363", "横八丁程竪里半餘", 3240, 480, False,
           "萬年記「小石川傳通院後商家出火、至駒込·千駄木·谷中·田畑村燒亡、酉下刻消。横八丁程竪里半餘」。「一」が省かれた「里半」。既存区域の別記録"),
          ("享保6年1月8日 呉服町", "1915668", "381", "凡幅六町半に廿三町程", 1380, 390, False,
           "月堂見聞集。焼けた屋敷と町数八十九町を挙げたあとの「凡幅六町半に廿三町程」（長さの語が無い）。同じ見開きの「幅五六町程に長さ一里」は鎮火前の書付で外してある"),
          ("延享2年2月12日 千駄谷", "1915668", "456", "凡ソ長サ靑山ヨリ品川マテ一里半許リ、横十五町餘", 3240, 900, False,
           "続日本王代一覧。青山六道辻→品川海晏寺門前。長さの語と数のあいだに「靑山ヨリ品川マテ」が挟まって型から漏れた。山川68町（No48）で見つけた"),
          ("延享2年2月12日 千駄谷", "1915668", "456", "芝品川驛迄三里餘類燒。幅十壹貳町計", 6480, 690, False,
           "政鄰記「千駄ヶ谷瀧川播磨守殿屋敷より出火…芝品川驛迄三里餘類燒。幅十壹貳町計」。長さの語が無い。同じ見開きの続史愚抄「長二里濶九里」は数が崩れていて外してある"),
          ("宝永3年1月14日 須田町", "1915668", "305", "南北壹里横十町餘", 2160, 600, False,
           "年代炎上鑑「神田須田町より出火…翌十五日鎭ル。晝大體町家計、南北壹里横十町餘」。長さを「南北」と書き、OCR では歴代炎上鑑の割注が間に入って崩れた（画像で確認）。山川 No21（15町）で見つけた")]


def rows_old():
    for r in csv.DictReader(open(HERE / "edo_long_fires_13.csv")):
        area = OLD_AREA_OVERRIDE.get((r["pid"], r["koma"]))
        if area is None:
            area = f"{r['era_guess'].split('（')[0]}{r['day_guess'].split('（')[0].split('〜')[0]}"
        yield dict(area=area, pid=r["pid"], koma=r["koma"], record=r["record"], length_ken=float(r["length_ken"]),
                   width_ken=float(r["width_ken"]), width_is_average=r["width_is_average"] == "True",  # 旧台帳は監査済みの旗
                   origin="旧台帳", note=r["note"][:80])


def rows_new():
    for r in csv.DictReader(open(HERE / "codex_check_full" / "audit.csv")):
        area = NEW_AREA.get(r["id"])
        if area is None:
            continue
        ix = next(x for x in csv.DictReader(open(HERE / "codex_check_full" / "index.csv")) if x["id"] == r["id"])
        L, W = float(ix["length_ken"]), float(ix["width_ken"])
        note = r["reason"][:80]
        text = AVG_TEXT.get(r["id"], r["text"])
        if r["id"] in NEW_VALUE_OVERRIDE:
            L, W, note = NEW_VALUE_OVERRIDE[r["id"]]
            text = NEW_RECORD_TEXT.get(r["id"], text)  # 換算値の出どころの記録を引用欄に出す（査読 10/31）
        yield dict(area=area, pid=r["pid"], koma=r["koma"], record=text, length_ken=L, width_ken=W,
                   width_is_average=width_avg(r["text"]) or r["id"] in NEW_AVG,
                   origin="全文36件", note=note)
    for r in csv.DictReader(open(HERE / "codex_check_ri" / "index.csv")):
        area, why = RI_DECISION[r["id"]]
        if area is None:
            continue
        yield dict(area=area, pid=r["pid"], koma=r["koma"], record=r["text"], length_ken=float(r["length_ken"]),
                   width_ken=float(r["width_ken"]), width_is_average=False, origin="里の取りこぼし", note=why)


def rows_yoko():
    for r in csv.DictReader(open(HERE / "codex_check_yoko" / "index.csv")):
        area, why = YOKO_DECISION[r["id"]]
        if area is None:
            continue
        yield dict(area=area, pid=r["pid"], koma=r["koma"], record=r["text"], length_ken=float(r["length_ken"]),
                   width_ken=float(r["width_ken"]), width_is_average=width_avg(r["text"]), origin="横・竪の取りこぼし", note=why)
    for r in csv.DictReader(open(HERE / "codex_check_kin" / "index.csv")):
        area, why = KIN_DECISION[r["id"]]
        if area is None:
            continue
        yield dict(area=area, pid=r["pid"], koma=r["koma"], record=r["text"], length_ken=float(r["length_ken"]),
                   width_ken=float(r["width_ken"]), width_is_average=width_avg(r["text"]), origin="卅・巾の取りこぼし", note=why)
    shapes = list(csv.DictReader(open(HERE / "hensai_shapes.csv")))
    for area, pid, koma, text, why in EXTRA:
        r = next(x for x in shapes if x["pid"] == pid and x["koma"] == koma and x["text"] == text)
        yield dict(area=area, pid=pid, koma=koma, record=text, length_ken=float(r["length_ken"]), width_ken=float(r["width_ken"]),
                   width_is_average=False, origin="外し誤りの訂正", note=why)


def rows_manual():
    for area, pid, koma, text, L, W, avg, why in MANUAL:
        yield dict(area=area, pid=pid, koma=koma, record=text, length_ken=float(L), width_ken=float(W),
                   width_is_average=avg, origin="手で読んだ記録", note=why)


def width_avg(text):
    """「平均」が幅に掛かっているか（「長サ平均…幅九丁半」は幅の平均ではない）"""
    return any(i >= 0 and "平均" in text[i:i + 8] for i in (text.find("幅"), text.find("巾")))


def main():
    rows = list(rows_old()) + list(rows_new()) + list(rows_yoko()) + list(rows_manual())
    for r in rows:
        r["w_over_l"] = round(r["width_ken"] / r["length_ken"], 3)
    rows = [r for r in rows if r["length_ken"] >= 600]
    # 平均明記の旗と引用の文言が食い違っていたら止める（11/5: 旧台帳の安政5年11月15日「幅員七町」に旗が立っていた）
    bad = [r["area"] for r in rows if r["width_is_average"] and "平均" not in r["record"]]
    assert not bad, f"平均明記なのに引用に「平均」が無い: {bad}"
    by = {}
    for r in rows:
        by.setdefault(r["area"], []).append(r)
    for recs in by.values():
        avg = [r for r in recs if r["width_is_average"]]
        rep = max(avg or recs, key=lambda r: r["w_over_l"])
        for r in recs:
            r["role"] = "代表" if r is rep else "別記録"
            r["area_max_ratio"] = max(x["w_over_l"] for x in recs)
    out = HERE / "edo_long_fires_v2.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["area", "role", "pid", "koma", "record", "length_ken", "width_ken",
                                          "w_over_l", "width_is_average", "area_max_ratio", "origin", "note"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["area"], r["role"] != "代表")))
    reps = [r for r in rows if r["role"] == "代表"]
    assert len(reps) == len(by)

    def line(name, xs):
        xs = sorted(xs)
        if not xs:
            return f"{name}: 0件"
        return (f"{name}: {len(xs)}区域 中央値 {st.median(xs):.3f}  {R0}未満 {sum(x < R0 for x in xs)}"
                f"（{sum(x < R0 for x in xs) / len(xs):.0%}）  {RMAX}未満 {sum(x < RMAX for x in xs)}  最大 {xs[-1]:.3f}")
    print(f"{len(rows)} 記録 / {len(by)} 区域 → {out.name}")
    print(line("全区域（代表）", [r["w_over_l"] for r in reps]))
    print(line("  幅平均明記", [r["w_over_l"] for r in reps if r["width_is_average"]]))
    print(line("  平均なし", [r["w_over_l"] for r in reps if not r["width_is_average"]]))
    print(line("  本火だけ（飛び火区域を除く）", [r["w_over_l"] for r in reps if "飛び火" not in r["area"]]))
    print(line("感度: 区域ごとに最大の比", [r["area_max_ratio"] for r in reps]))
    alt1 = [0.5 if r["area"] == "元禄8年2月8日 四谷" else r["w_over_l"] for r in reps]
    print(line("感度: 元禄8年を基熙公記の0.5に", alt1))
    alt2 = [0.667 if r["area"] == "享保2年12月28日 牛込天龍寺前" else r["w_over_l"] for r in reps]
    print(line("感度: 享保2年牛込を直線1.5里で0.67に", alt2))
    for r in sorted(reps, key=lambda r: -r["w_over_l"])[:8]:
        print(f"   {r['w_over_l']:.3f} {'平均' if r['width_is_average'] else '    '} {r['area']}  {r['record']}")


if __name__ == "__main__":
    main()
