"""Build sfx/index.html (audition page) from the rendered files."""
import html
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

NOTES = {
    '拳銃_単発': '9mm拳銃の実録音1発',
    '拳銃_3連射': '9mm拳銃の実録音を3発つなげたもの',
    'ヘビーピストル': '撃鉄を起こす音のあと、大口径の重い1発',
    'SMG_連射': '9mm SMGの実録音（7発）',
    'アサルトライフル_3点': 'AK系ライフルの実録音で3点バースト',
    'アサルトライフル_フルオート': 'AK系ライフルのフルオート（14発）',
    'サブマシンガン_長連射': 'PPShの長い連射の実録音',
    'ショットガン+ポンプ': '12ゲージの1発とポンプアクション、排莢',
    'スナイパーライフル': 'SKSの1発とボルト操作',
    'スマートガン_ロック射撃': 'ロックオン音からSMGの5連射',
    'レールガン_チャージ射撃': 'テック武器。電気のうなりで充電し、大砲のような発射音',
    '弾切れ_カチッ': '撃とうとして弾が出ない（2回）',
    'リロード_拳銃': '拳銃のマガジン交換',
    'リロード_ライフル': 'ライフルのマガジン交換',
    '遠くの銃撃戦': '数ブロック先の撃ち合い（実録音を遠くの音に加工）',
    '被弾_肉体1': '体に弾が当たる。鈍い衝撃と、湿った肉の音',
    '被弾_肉体2': '体に弾が当たる（重め・水気が多い）',
    '被弾_肉体3': '体に弾が当たる（別パターン）',
    '被弾_かすり傷': '弾がかすめて浅く裂く',
    '被弾_防弾プレート': '防弾プレートが弾を止める',
    '被弾_サイバーウェア1': '金属の義体に弾が当たる（重い金属音）',
    '被弾_サイバーウェア2': '金属の義体に弾が当たる（硬く短い）',
    '着弾_コンクリート': '外れた弾が壁に当たり、破片が落ちる',
    '着弾_金属': '車体や鉄板への着弾（3発）',
    'ガラス破砕': '窓ガラスが割れて床に散らばる',
    '跳弾1': '跳弾',
    '跳弾2': '跳弾（別パターン）',
    '制圧射撃を受ける': '遮蔽の陰で撃たれ続けている。周りに弾が当たる',
    '手榴弾_投擲から爆発': 'ピンを抜き、転がって、爆発するまで',
    '大爆発_車両': '車両の大爆発。降ってくる破片と炎まで',
    'EMPグレネード': 'EMP。破裂と電気的な乱れ',
    '閃光弾_耳鳴り': '閃光弾の破裂と、そのあとに残る耳鳴り（耳鳴りのみ合成音）',
    '刀_抜刀': '刃物を鞘から抜く',
    '斬撃_空振り': '刃物の空振り（2回）',
    '斬撃_命中': '刃物が肉を斬る',
    'アームブレード展開': '機構が動いてブレードが飛び出す',
    '打撃_パンチ': '素手の打撃（2発）',
    '打撃_サイバーアーム': '機械の腕の重い一撃',
    'ジャックイン': 'ポートに接続し、電脳空間へ',
    'クイックハック送信': 'クイックハックを撃ち込む',
    'アクセス許可': '認証成功',
    'アクセス拒否': '認証失敗',
    'ICE検知_警告': 'ICEに見つかった警告音',
    '警報_施設ロックダウン': '施設全体の警報。SEの繰り返し再生に向く',
    'ショート_感電': '電気がはじけてショートする',
    'システム異常_グリッチ': '機器やサイバーウェアの誤作動',
    'フラットライン': '心拍モニターが止まる（モニター音は合成）',
    'スキャン': 'スキャナーの走査',
    '電子ロック解除': 'キー入力して電子錠が開く',
    '自動ドア_開': '重い自動ドアが開いて止まる',
    'エレベーター到着': 'エレベーターが動いて到着し、ドアが開く',
    '雨のネオン街': '雨とガラスを打つ雨、ネオン管の電気的なうなり、遠い車、遠雷（54秒ループ）',
    '夜の繁華街': '人混みと街の録音に、車・クラクション・飛行車の音（合成）を足したもの（54秒ループ）',
    '裏路地': '遠い街、室外機、ネオンのうなり、ときどき金属の物音（54秒ループ）',
    'クラブ_壁越し': '壁の向こうのクラブ。重低音とこもった歓声（音楽部分は合成、60秒ループ）',
    'サーバールーム': '空調とPCのファン、電源のうなり（54秒ループ）',
    '電脳空間': 'ネットダイブ中の空間（合成の音楽、60秒ループ）',
    '廃工場': '大型ファンと動き続ける機械、ときどき金属音（54秒ループ）',
    '車内_雨の夜': 'バス車内の走行音と、屋根を打つ雨（54秒ループ）',
    '雷雨': '雷と雨の録音そのまま（54秒ループ）',
    '地下鉄_車内': '地下鉄の車内（54秒ループ）',
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
<p class="lead">全{total}音。CC0（パブリックドメイン相当）の生の録音をほぼそのまま使っています。合成音が混じる音は説明に書いてあります。
環境音ループは継ぎ目なしで、VTTではBGMとして登録します。詳しくは同じフォルダのREADME.mdを参照。</p>
{"".join(sections)}
</main></body></html>'''
    with open(os.path.join(ROOT, 'index.html'), 'w') as f:
        f.write(page)
    print('index.html:', total, 'sounds')


if __name__ == '__main__':
    main()
