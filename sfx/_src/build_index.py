"""Build sfx/index.html (audition page) from the rendered files."""
import html
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

NOTES = {
    '拳銃_単発': '標準的な拳銃の1発。屋外（ビルの谷間）の反響と薬莢の落下音つき',
    '拳銃_3連射': '拳銃の素早い3連射',
    '拳銃_屋内2発': '室内での2発。短く詰まった残響',
    'ヘビーピストル': '撃鉄を起こしてから大口径の1発。重いリボルバー系',
    'サプレッサー拳銃': '消音器つき。スライドの作動音が主役の静かな2発',
    'SMG_連射': 'サブマシンガンの短い連射（7発）',
    'SMG_屋内連射': '室内でのSMG連射（9発）',
    'アサルトライフル_3点': 'アサルトライフルの3点バースト',
    'アサルトライフル_フルオート': 'アサルトライフルのフルオート（14発）',
    'ミニガン_掃射': '回転式機関銃の掃射。ドローンや車載銃座に',
    'ショットガン+ポンプ': '散弾銃の1発とポンプアクション',
    'スナイパーライフル': '狙撃銃の1発。長いエコーとボルト操作',
    'スマートガン_ロック射撃': 'ロックオン電子音から誘導弾5連射。弾が左右に散っていく',
    'レールガン_チャージ射撃': 'テック武器。充電音、電磁加速の発射、放熱音',
    '弾切れ_カチッ': '撃とうとして弾が出ない（2回）',
    'リロード_拳銃': 'マガジン交換とスライド操作',
    'リロード_ライフル': '空マガジンを落とし、差し込み、チャージングハンドルを引く',
    '遠くの銃撃戦': '数ブロック先の撃ち合い。場面転換や緊張感の演出に',
    '被弾_肉体1': '体に弾が当たる（標準）',
    '被弾_肉体2': '体に弾が当たる（重め・骨に響く）',
    '被弾_肉体3': '体に弾が当たる（軽め）',
    '被弾_かすり傷': '弾がかすめて浅く裂く',
    '被弾_防弾プレート': '防弾プレートが弾を止める（SPで止まったとき）',
    '被弾_サイバーウェア': 'サイバーウェアへの命中。金属音、火花、サーボの異音',
    '着弾_コンクリート': '外れた弾が壁に当たり破片が散る',
    '着弾_金属': '車体や鉄板への着弾',
    'ガラス破砕': '窓ガラスが割れて床に散らばる',
    '跳弾1': '跳弾（ピュイーン）',
    '跳弾2': '跳弾（別パターン）',
    '弾がかすめる': '耳元を弾がかすめていく（3発）',
    '制圧射撃を受ける': '遮蔽の陰で撃たれ続けている状況音',
    '手榴弾_投擲から爆発': 'ピンを抜き、転がって、爆発するまで',
    '大爆発_車両': '車両や燃料の大爆発。降ってくる破片と炎の音まで',
    'EMPグレネード': 'EMP。電子機器が死んでいく音つき',
    '閃光弾_耳鳴り': '閃光弾。破裂後はこもった音と耳鳴りが残る',
    '刀_抜刀': '刀を鞘から抜いて刃が鳴る',
    '斬撃_空振り': '刃物の空振り（2回）',
    '斬撃_命中': '刃物が肉を斬る',
    'アームブレード展開': '腕に内蔵したブレードの展開',
    '打撃_パンチ': '素手の打撃（2発）',
    '打撃_サイバーアーム': '油圧義手の重い一撃',
    'ジャックイン': '首のポートに接続し、電脳空間へ潜る',
    'クイックハック送信': 'クイックハックを組んで撃ち込む',
    'アクセス許可': '認証成功・ハッキング成功',
    'アクセス拒否': '認証失敗',
    'ICE検知_警告': 'ICEに見つかった。敵対的な警告音',
    '警報_施設ロックダウン': '施設全体の警報。SEの繰り返し再生に向く',
    'ショート_感電': '火花が飛んでショートする、感電する',
    'システム異常_グリッチ': '機器やサイバーウェアの誤作動、システムダウン',
    'フラットライン': '心拍モニターが止まる',
    'スキャン': 'スキャナーやキロシ（義眼）の走査音',
    '電子ロック解除': 'キーパッドを入力して電子錠が開く',
    '自動ドア_開': 'SF風の自動ドア（空気圧）',
    'ドローン通過': 'クアッドコプター型ドローンが飛び去る',
    'AV飛行車_通過': '飛行車両（AV）が頭上を通過する',
    'パトカーサイレン通過': 'サイレンを鳴らした車両が目の前を走り抜ける',
    'エレベーター到着': 'エレベーターが到着してドアが開く',
    '雨のネオン街': '雨、濡れた路面を走る車、ネオン管の唸り、遠いサイレンと雷',
    '夜の繁華街': '人混みのざわめき（言葉は聞き取れない）、車、クラクション、頭上のAV',
    '裏路地': '風、水滴、蒸気の噴出、ネオンのちらつき。遠くで銃声が1発',
    'クラブ_壁越し': '壁の向こうのクラブ（128BPM）。重低音とこもった歓声',
    'サーバールーム': 'ファン、空調、HDDのシーク音、ステータス音',
    '電脳空間': 'ネットダイブ中の空間。ゆっくり動くパッドと電子のきらめき',
    '廃工場': 'まだ動くプレス機の周期音、隙間風、軋み、水滴。広い残響',
    '車内_雨の夜': '雨の夜の車内。エンジン、屋根を打つ雨、ワイパー',
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
<p class="lead">全{total}音。録音素材を使わず、コードで一から合成したオリジナル音源です（48kHz合成）。
環境音ループは継ぎ目なしで、VTTではBGMとして登録します。詳しくは同じフォルダのREADME.mdを参照。</p>
{"".join(sections)}
</main></body></html>'''
    with open(os.path.join(ROOT, 'index.html'), 'w') as f:
        f.write(page)
    print('index.html:', total, 'sounds')


if __name__ == '__main__':
    main()
