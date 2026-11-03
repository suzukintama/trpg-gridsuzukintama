"""Pack v7 housekeeping: remove the files that the 2026-11-01 reorganisation retired.

01_銃 keeps only the six gun families, the heavy weapons, reload / empty / casings and the far
gunfight. Duplicates between v5 and v6 (same recording rendered twice under two names) keep one
copy. The retired renders are deleted from the pack; their sources stay in rec/, and every
retired name can be rebuilt from gen_v3 .. gen_v6 if it is wanted again.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

KEEP_01 = {'ハンドガン_単発', 'ライフル_単発', 'アサルトライフル_単発', 'アサルトライフル_3連射', 'アサルトライフル_フルオート',
           '機関銃_フルオート', 'ミニガン_掃射', 'ロケットランチャー_発射', 'ロケットランチャー_着弾', '重機関砲_掃射', '榴弾砲_発射',
           'リロード_拳銃', 'リロード_ライフル', '弾切れ_カチッ', '薬莢_落下', '遠くの銃撃戦'}

RETIRE = {
    '02_被弾・着弾': ['着弾_鋼板1', '着弾_鋼板2', '着弾_鋼板3', '被弾_肉_湿った音', '被弾_肉塊', '被弾_鈍い打撃'],
    '03_爆発': ['ミサイル発射'],
    '05_ハッキング': ['ICE検知_警告', 'アクセス拒否', 'アクセス許可', 'クイックハック送信', 'システム異常_グリッチ', 'ジャックイン',
                  'スキャン', 'フラットライン', '警報_施設ロックダウン', '電子ロック解除',
                  '放電_35kV', '短絡_130kV', 'ヤコブの梯子', 'ネオン管_点灯', '蛍光灯_点灯', '溶接アーク',
                  # 2026-11-03: the 56k modem was replaced by gen_future.py's ネット接続
                  'ネット接続_ダイヤル'],
    '06_機械・乗り物': ['パトカーサイレン通過', 'ジェット機_通過', 'ヘリ_頭上通過', '電気自動車_通過', '自販機_缶', '蒸気_安全弁'],
    '07_環境音ループ': ['裏路地_雨樋'],
}


def main():
    gone = []
    d = os.path.join(ROOT, '01_銃')
    for f in sorted(os.listdir(d)):
        base = f.rsplit('.', 1)[0]
        if base not in KEEP_01:
            os.remove(os.path.join(d, f))
            gone.append(f'01_銃/{f}')
    for cat, names in RETIRE.items():
        d = os.path.join(ROOT, cat)
        for f in sorted(os.listdir(d)):
            if f.rsplit('.', 1)[0] in names:
                os.remove(os.path.join(d, f))
                gone.append(f'{cat}/{f}')
    print('\n'.join(gone))
    print(len(gone), 'files retired')


if __name__ == '__main__':
    main()
