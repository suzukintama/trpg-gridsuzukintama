"""Build sfx/index.html (audition page) from the rendered files."""
import html
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

NOTES = {
    '拳銃_単発': '9mm拳銃（Walther PPQ）の1発。屋外の反響が自然に消えるまで',
    '拳銃_3点バースト': '拳銃の3点バースト',
    '拳銃_15連射': '拳銃を15発。途中で一度だけ間が空く',
    '拳銃_撃ち続けループ': '拳銃を撃ち続ける。ときどき止まってリズムを刻む（25秒ループ。BGMとして登録）',
    '拳銃_屋内': '屋内射撃場での拳銃の1発',
    'サプレッサー拳銃': 'サプレッサー付き拳銃（3発）',
    'ヘビーピストル': '撃鉄を起こす音のあと、.45口径（1911）の1発',
    'アサルトライフル_単発': 'AR-15の1発',
    'SMG_連射': 'SMG（M45）の連射の実録音',
    'サプレッサーSMG': 'サプレッサー付きSMGの連射',
    'アサルトライフル_3点': 'AR-15の3点バースト',
    'アサルトライフル_フルオート': 'AK-47のフルオート連射（1回分の実録音）',
    'アサルトライフル_バースト実録': 'ライフルの短い連射の実録音',
    'ライフル_屋内': '屋内でのライフルの1発（部屋の響き入り）',
    'サブマシンガン_長連射': 'PPShの長い連射（約20発）の実録音',
    'ショットガン+ポンプ': '散弾銃の1発、ポンプアクション、排莢',
    'スナイパーライフル': 'ボルトアクション狙撃銃の1発と、ボルト操作',
    'サプレッサー狙撃銃': 'サプレッサー付き大口径狙撃銃の1発',
    '重機関砲_掃射': '砲塔や車載の機関砲の連射',
    'ミニガン_掃射': 'ガトリング砲の掃射',
    'ショットガン': 'ポンプ式散弾銃の1発',
    'スマートガン_ロック射撃': 'サーボが動き、金属的なロックオン音が3つ鳴ってから、SMGの誘導弾の連射',
    'レールガン_チャージ射撃': 'のこぎりの唸りを加工した充電音と本物の放電、重い発射音、砲身の金属の響き、放熱',
    '弾切れ_カチッ': '撃とうとして弾が出ない（2回）',
    'リロード_拳銃': '拳銃のマガジン交換',
    'リロード_ライフル': 'ライフルのマガジン交換',
    '薬莢_落下': '薬莢がコンクリートに落ちて転がる',
    '遠くの銃撃戦': '数ブロック先の撃ち合い（屋外の反響ごと録った銃声）',
    '被弾_肉体1': '肉に強く打ち込む音（生肉を叩いた実録音）',
    '被弾_肉体2': '肉に打ち込む音と、湿った音',
    '被弾_肉体3': '肉に打ち込む短い音',
    '被弾_かすり傷': '弾がかすめて浅く裂く',
    '被弾_防弾プレート': '防弾プレートが弾を止める',
    '被弾_サイバーウェア1': '鋼板に本物の弾が当たる音に、短い火花',
    '被弾_サイバーウェア2': '金属板の響きと高い金属音、火花、サーボの異常音',
    '被弾_サイバーウェア3': 'ガシャンと潰れる金属音と、ジリッとした放電',
    '着弾_コンクリート': '外れた弾が壁に当たり、破片が落ちる',
    '着弾_金属': '鋼板への着弾（本物の弾）2発',
    'ガラス破砕': '窓ガラスが割れて床に散らばる',
    '跳弾1': '跳弾（実録）',
    '跳弾2': '跳弾（実録・別パターン）',
    '跳弾_連続': '跳弾が3回続く',
    '制圧射撃を受ける': '遠くからの連射と、すぐ周りに弾が当たる音',
    '手榴弾_投擲から爆発': 'ピンを抜き、転がって、爆発するまで（爆発は手榴弾の実録音）',
    '大爆発_車両': '大爆発の実録音に、降ってくる破片と炎',
    'EMPグレネード': '充電の唸り、破裂と高電圧の放電、周りの機械が止まっていく音',
    'ミサイル発射': 'ミサイルの発射と飛翔',
    '閃光弾_耳鳴り': '破裂のあと、世界がこもって耳鳴りが残る（耳鳴りは金属の響きを引き伸ばしたもの）',
    '刀_抜刀': '刃物を鞘から抜く',
    '斬撃_空振り': '刃物の空振り（2回）',
    '斬撃_命中': '刃物が肉を斬る',
    'アームブレード展開': 'サーボが動いて、バネ仕掛けの刃が飛び出す',
    '打撃_パンチ': '素手の打撃（2発）',
    '打撃_サイバーアーム': 'サーボが唸り、重い一撃、排気',
    '義体_サーボ駆動': '義体のサーボモーターが動く',
    '義体_排気': '義体の排気。プシューと空気が抜ける',
    'ジャックイン': 'プラグが刺さり、電波の乱れが高まって、電脳空間へ潜り込む',
    'ハッキング_タイピング': 'キーボードの速い打鍵',
    'クイックハック送信': 'キー入力、電子機器のノイズの断片、高まる充電と放電',
    'アクセス許可': 'カードをかざす音と、金属を鳴らした上昇音',
    'アクセス拒否': '鈍い音、短い電波ノイズ、くぐもった下降音',
    'ICE検知_警告': '本物のサイレンを高く細かく刻んだ警告音',
    '警報_施設ロックダウン': 'コンクリートの空間に響く警報と、防護扉が閉まる音',
    'ショート_感電': '高電圧のショート',
    '火花_スパーク': 'バチバチと火花が飛ぶ',
    '電撃_アーク放電': 'アーク放電のジリジリという音。スタン兵器や電撃系に',
    'システム異常_グリッチ': '電子機器の音が細切れになり、電源が落ちていく',
    'フラットライン': '静かな病室で心拍モニターが止まる（モニター音そのものは機器の電子音）',
    'スキャン': 'サーボが回り、走査の帯が上下し、終わると柔らかい音',
    '電子ロック解除': 'キー入力、確認音、ロックが外れて空気が抜ける',
    '通信妨害_ノイズ': '空電と携帯電話の干渉ノイズ。途切れ途切れ',
    '都市警報サイレン': '街全体に鳴り響く警報サイレン',
    '自動ドア_開': '空気圧の自動ドアが開く（電車のドアの実録音）',
    'エレベーター到着': 'モーターの唸り、到着の金属音、ドアが開く空気音',
    'パトカーサイレン通過': 'パトカーがサイレンを鳴らして走り抜ける',
    'ヘリ_頭上通過': 'ヘリが頭上を通過する。AV（飛行車）の代わりにも',
    'AV_頭上通過': '飛行車（AV）が頭上を通過する（ジェットの実録音を加工）',
    'ジェット機_通過': 'ジェット機が轟音で通過する',
    '電気自動車_通過': '電気自動車が静かに通り過ぎる',
    'ドローン_ホバリング': 'ドローンが近くで滞空している（26秒ループ。BGMとして登録）',
    'ドローン通過': 'ドローンが近づいて通り過ぎる',
    '自販機_購入': '自販機で買って、ガコンと出てくる',
    '蒸気_噴出': '配管から蒸気が噴き出す',
    'ネオン_点灯': '蛍光灯・ネオン管がチカチカして点く',
    '足音_コンクリート': 'コンクリートを歩く足音',
    '足音_金属グレーチング': '金属の格子床を歩く足音',
    '足音_金属階段': '金属の階段を上り下りする足音',
    '雨のネオン街': '街の雨、ネオン管の唸り、雨越しの広告の声、遠雷、遠いAV（54秒ループ）',
    '夜の繁華街': '夜の繁華街に、電気自動車、遠くのホログラム広告の声、頭上のAV（54秒ループ）',
    '裏路地': '静かな夜の路地、蛍光灯、配管の蒸気、奥から漏れる広告の声、頭上のAV（54秒ループ）',
    '雨の路地裏': '雨どいから落ちる水と、路地に降る雨（54秒ループ）',
    'クラブ_壁越し': '壁の向こうのクラブ。ドラムンベースの低音と、こもった人の声（57秒ループ）',
    'サーバールーム': '空調とPCのファン、電源のうなり（54秒ループ）',
    '電脳空間': '楽曲素材のパッドを引き伸ばし、金属の響きのきらめきを重ねた電脳空間（60秒ループ）',
    '廃工場': '大型ファンと動き続ける機械、金属音、圧縮空気。広い残響（54秒ループ）',
    '車内_雨の夜': '車内の走行音と、屋根を打つ雨（54秒ループ）',
    '雷雨': '雷と雨の録音そのまま（54秒ループ）',
    '地下鉄_車内': '地下鉄の車内（54秒ループ）',
    '電車_車内放送': '電車の車内に、中身のない英語の車内放送とラジオが流れ続ける（声は合成、144秒ループ）',
}


def dur(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def main():
    cats = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and d[:2].isdigit())
    sections = []
    total = 0
    for c in cats:
        order = list(NOTES)
        files = sorted((f for f in os.listdir(os.path.join(ROOT, c)) if f.endswith('.mp3')),
                       key=lambda f: (order.index(f[:-4]) if f[:-4] in order else len(order), f))
        rows = []
        for f in files:
            base = f[:-4]
            rel = f'{c}/{f}'
            ogg = os.path.exists(os.path.join(ROOT, c, base + '.ogg'))
            d = dur(os.path.join(ROOT, c, f))
            total += 1
            src = (f'<source src="{html.escape(c)}/{html.escape(base)}.ogg" type="audio/ogg">' if ogg else '') + \
                  f'<source src="{html.escape(rel)}" type="audio/mpeg">'
            dl = f'<a href="{html.escape(rel)}" download>MP3</a>' + \
                 (f' · <a href="{html.escape(c)}/{html.escape(base)}.ogg" download>OGG</a>' if ogg else '')
            rows.append(f'''<div class="row"><div class="meta"><div class="name">{html.escape(base)}</div>
<div class="note">{html.escape(NOTES.get(base, ''))}</div></div>
<div class="len">{d:.1f}s</div><audio controls preload="none"{' loop' if ogg else ''}>{src}</audio><div class="dl">{dl}</div></div>''')
        sections.append(f'<section><h2>{html.escape(c[3:])}</h2>{"".join(rows)}</section>')
    page = f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>サイバーパンクTRPG 効果音パック</title>
<style>
:root{{--bg:#0d0f14;--card:#151922;--line:#232a36;--tx:#e6e9ef;--tx2:#97a0b0;--ac:#3aa0a6;--ac2:#d14b8f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}}
main{{max-width:980px;margin:0 auto;padding:32px 20px 80px}}h1{{font-size:24px;margin:0 0 6px;letter-spacing:.02em}}
.lead{{color:var(--tx2);margin:0 0 28px}}h2{{font-size:16px;color:var(--ac);border-bottom:1px solid var(--line);padding-bottom:6px;margin:34px 0 10px}}
.row{{display:grid;grid-template-columns:1fr 56px 300px 90px;gap:12px;align-items:center;padding:10px 12px;background:var(--card);border:1px solid var(--line);border-radius:8px;margin-bottom:6px}}
.name{{font-weight:600}}.note{{color:var(--tx2);font-size:13px}}.len{{color:var(--tx2);font:12px ui-monospace,monospace;text-align:right}}
audio{{width:100%;height:34px}}.dl a{{color:var(--ac2);font-size:13px;text-decoration:none}}
@media (max-width:760px){{.row{{grid-template-columns:1fr 50px}}audio{{grid-column:1/-1}}.dl{{grid-column:1/-1}}}}
</style></head><body><main>
<h1>サイバーパンクTRPG 効果音パック</h1>
<p class="lead">全{total}音。銃と環境はCC0の生の録音そのまま、未来の音（ハッキング・義体・テック武器・AV・電脳空間）は生の録音を加工して作っています。
環境音ループは継ぎ目なしで、VTTではBGMとして登録します。詳しくは同じフォルダのREADME.mdを参照。</p>
{"".join(sections)}
</main></body></html>'''
    with open(os.path.join(ROOT, 'index.html'), 'w') as f:
        f.write(page)
    print('index.html:', total, 'sounds')


if __name__ == '__main__':
    main()
