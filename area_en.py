"""区域名（edo_long_fires_v2.csv の area）を英語版の原稿用に書き直す（11/5、英訳のため）。

和暦の年月日は規則で「Genroku 12.4.4」の形に、地名と火事の名前は下の表で訳す。
表に無い語が残ったら例外を出す（黙って日本語を英語版に混ぜない）。
"""
import re

ERA = {
    "明暦": "Meireki", "天和": "Tenna", "元禄": "Genroku", "宝永": "Hōei", "正徳": "Shōtoku", "享保": "Kyōhō",
    "延享": "Enkyō", "宝暦": "Hōreki", "明和": "Meiwa", "天明": "Tenmei", "寛政": "Kansei", "文化": "Bunka",
    "文政": "Bunsei", "天保": "Tenpō", "弘化": "Kōka", "嘉永": "Kaei", "安政": "Ansei", "文久": "Bunkyū",
    "慶応": "Keiō", "明治": "Meiji",
}
PLACE = {
    "本石町": "Honkoku-chō", "麻布古川新屋敷": "Azabu Furukawa Shinyashiki", "上野屏風坂": "Ueno Byōbuzaka",
    "芝": "Shiba", "千駄谷": "Sendagaya", "芝三田台町": "Shiba Mita Daimachi", "青山久保町": "Aoyama Kubo-chō",
    "須田町": "Suda-chō", "丸山火事": "Maruyama fire", "本火": "main fire", "駿河台飛び火区域": "flying-ember area at Surugadai",
    "目白台": "Mejirodai", "赤坂伝馬町": "Akasaka Tenma-chō", "小石川→芝": "Koishikawa to Shiba",
    "芝三田新堀": "Shiba Mita Shinbori", "四谷伊賀町": "Yotsuya Iga-machi", "元誓願寺前": "Moto-Seiganji-mae",
    "南鞘町": "Minami Saya-chō", "中橋": "Nakabashi", "小石川": "Koishikawa", "浅草鳥越": "Asakusa Torigoe",
    "本所飛び火区域": "flying-ember area at Honjo", "神田新白銀町": "Kanda Shin-Shirogane-chō", "己丑火事": "Kichū fire",
    "青山": "Aoyama", "四谷": "Yotsuya", "青山火事": "Aoyama fire", "本所石原": "Honjo Ishiwara",
    "横田火事": "Yokota fire", "横山町": "Yokoyama-chō", "牛込天龍寺前": "Ushigome Tenryūji-mae",
    "水戸様火事": "Mito-sama fire", "小網町": "Koami-chō", "三河町": "Mikawa-chō", "丙寅火事": "Hinoe-tora fire",
    "日本橋釘店": "Nihonbashi Kugidana", "芝土器町": "Shiba Kawarake-chō", "赤坂今井谷": "Akasaka Imaidani",
    "小石川下富坂町": "Koishikawa Shimo-Tomisaka-chō", "馬喰町": "Bakuro-chō", "麹町": "Kōjimachi",
    "明石屋火事": "Akashiya fire", "深川飛び火区域": "flying-ember area at Fukagawa", "芝神明前": "Shiba Shinmei-mae",
    "京橋南五町目": "Kyōbashi Minami 5-chōme", "四谷中殿町": "Yotsuya Nakadono-chō", "神田佐久間町": "Kanda Sakuma-chō",
    "呉服町": "Gofuku-chō", "浅草→本所": "Asakusa to Honjo", "鍛冶橋・京橋": "Kajibashi and Kyōbashi",
    "下谷・箕輪": "Shitaya and Minowa", "駒込浅嘉町": "Komagome Asaka-chō", "勅額火事": "Chokugaku fire", "小石川白山前": "Koishikawa Hakusan-mae",
}


def area_en(a):
    s = a
    s = re.sub(r"\s*（コマ(\d+)、推定）", r" (frame_\1,_inferred)", s)
    s = re.sub(r"\s*（コマ(\d+)）", r" (frame_\1)", s)
    s = s.replace("正月", "1月").replace("晦日", "末日")
    m = re.match(r"^(\S{2})(元|\d+)(?:〜(\d+))?年(?:(\d+)月)?(?:(\d+|末)日?)?(夜)?\s*(.*)$", s)
    if not m:
        raise ValueError(f"日付が読めない: {a}")
    era, y, y2, mo, d, night, rest = m.groups()
    y = "1" if y == "元" else y
    date = f"{ERA[era]} {y}" + (f"–{y2}" if y2 else "")
    if mo:
        date += f".{mo}"
        if d:
            date += ".last day" if d == "末" else f".{d}"
    if night:
        date += ", night"
    parts = []
    for w in rest.split():
        if w.startswith("("):
            parts.append(w.replace("_", " "))
            continue
        if w not in PLACE:
            raise ValueError(f"訳の無い語「{w}」: {a}")
        t = PLACE[w]
        parts.append((", " if t == "main fire" or t.startswith("flying-ember") else " ") + t)
    return (date + "".join(p if p.startswith(", ") else " " + p.lstrip() for p in parts)).strip()


if __name__ == "__main__":
    import csv
    for a in sorted({r["area"] for r in csv.DictReader(open("edo_long_fires_v2.csv"))}):
        print(f"{a}\t{area_en(a)}")
