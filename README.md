# SteamレビューをCSVでダウンロードする君

## install
```shell
# 仮想環境を作成 (例: .venv)
python -m venv .venv

# macOS/Linux 
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# 実行
streamlit run app.py
```

## usage
1. Steam上のゲームのAppIDを入力
2. データを取得
3. CSVファイルをダウンロード