import streamlit as st
import requests
import pandas as pd
import io

# Steam APIからレビューを取得する関数 (プレースホルダー)
def get_all_reviews(appid: int):
    """
    指定されたappidのSteamレビューをすべて取得する関数。
    ページネーションを処理して全レビューを結合する。
    """
    reviews = []
    cursor = "*"  # 最初のカーソル
    base_url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": "1",
        "filter": "recent",  # 有用性順で取得 (デフォルト)
        "language": "all",
        "day_range": "365", # 過去365日間のレビューを対象 (filter=all の場合)
        "num_per_page": "100", # 一度に取得する最大レビュー数
        "review_type": "all",
        "purchase_type": "all",
        # cursorはループ内で設定するので、ここでは設定しない
    }

    st.write("レビュー取得中...") # 進捗表示
    progress_bar = st.progress(0)
    page_count = 0
    total_reviews_estimated = None # 推定総レビュー数
    previous_cursors = set()  # 過去に使用したカーソルを記録

    while True:
        page_count += 1
        st.write(f"{page_count}ページ目を取得中... (cursor: {cursor[:10]}...)") # ページ取得状況
        
        # カーソル値をそのまま設定（requests.getが自動的にエンコードする）
        params["cursor"] = cursor
        
        # デバッグ用：カーソル値を表示
        print(f"設定するカーソル値: {cursor}")

        try:
            # リクエスト実行
            response = requests.get(base_url, params=params, timeout=10)
            # 実際のリクエストURLを出力
            print(f"リクエストURL: {response.url}")  # デバッグ用
            response.raise_for_status() # HTTPエラーチェック
            data = response.json()
            # APIレスポンスをコンソールに表示する
            print(data)  # デバッグ用


            if data.get("success") != 1:
                st.error(f"APIリクエスト失敗: {data}")
                return None

            # 初回リクエストで推定総レビュー数を取得
            if total_reviews_estimated is None and "query_summary" in data:
                 # query_summary が存在し、かつ total_reviews が数値の場合のみ取得
                if isinstance(data["query_summary"].get("total_reviews"), (int, float)):
                    total_reviews_estimated = data["query_summary"]["total_reviews"]
                    st.write(f"推定総レビュー数: {total_reviews_estimated}")


            current_reviews = data.get("reviews", [])
            reviews.extend(current_reviews)

            # 進捗バーの更新 (推定総数がある場合)
            if total_reviews_estimated and total_reviews_estimated > 0:
                progress = min(len(reviews) / total_reviews_estimated, 1.0)
                progress_bar.progress(progress)
            else:
                # 推定総数がない場合は、取得ページ数で簡易的に進捗を表示
                 progress_bar.progress(min(page_count / 50.0, 1.0)) # 仮に50ページを最大とする

            # レビューが空か、取得数がnum_per_page未満なら終了
            # num_per_page は文字列なので比較のためにintに変換
            num_per_page_int = int(params.get("num_per_page", 100))
            if not current_reviews or len(current_reviews) < num_per_page_int:
                 st.write("全レビューを取得しました。")
                 progress_bar.progress(1.0) # 完了時に100%にする
                 break

            # 新しいカーソル値を取得
            cursor = data.get("cursor")
            print(f"APIから返された新しいカーソル値: {cursor}")
            if not cursor:
                st.warning("次のカーソルが見つかりませんでした。取得を終了します。")
                progress_bar.progress(1.0) # 完了時に100%にする
                break
                
            # 同じカーソルが再度出現したら無限ループを防ぐために終了
            if cursor in previous_cursors:
                st.warning(f"同じカーソル値が再度出現しました。ページネーションを終了します。")
                progress_bar.progress(1.0) # 完了時に100%にする
                break
            
            # 使用したカーソルを記録
            previous_cursors.add(cursor)
            
            # 最大ページ数の制限 (安全対策)
            if page_count >= 100:  # 最大50ページまで
                st.warning("最大ページ数に達しました。取得を終了します。")
                progress_bar.progress(1.0)
                break

        except requests.exceptions.RequestException as e:
            st.error(f"リクエストエラー: {e}")
            return None
        except Exception as e:
            st.error(f"予期せぬエラー: {e}")
            return None

    st.success(f"合計 {len(reviews)} 件のレビューを取得しました。")
    return reviews

# レビューデータをCSVに変換する関数
def convert_reviews_to_csv(reviews):
    """レビューデータのリストをCSV形式のバイトデータに変換する"""
    if not reviews:
        return None

    # ネストされた 'author' 情報をフラット化
    flat_reviews = []
    for review in reviews:
        flat_review = review.copy()
        author_info = flat_review.pop('author', {})
        flat_review.update({f'author_{key}': value for key, value in author_info.items()})
        flat_reviews.append(flat_review)

    df = pd.DataFrame(flat_reviews)
    # 必要に応じてカラムを選択・順序変更
    # df = df[['recommendationid', 'author_steamid', 'review', ...]]
    csv_buffer = io.BytesIO()
    # BOM付きUTF-8でエンコードしてExcelでの文字化けを防ぐ
    csv_buffer.write(b'\xef\xbb\xbf')
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

# --- Streamlit UI ---
st.title("Steam レビューダウンローダー")

# App IDの入力
appid_input = st.text_input("Steam App ID を入力してください:", placeholder="例: 688130")

if appid_input:
    try:
        appid = int(appid_input)
        st.write(f"App ID: {appid} のレビューを取得します。")

        # レビュー取得ボタン (レビュー取得処理をボタンクリック時に実行)
        if st.button("レビュー取得 & CSVダウンロード準備"):
            # セッションステートにレビューデータを保存
            st.session_state.reviews = get_all_reviews(appid)
            st.session_state.appid_processed = appid # 処理したappidも保存

    except ValueError:
        st.error("有効な数字の App ID を入力してください。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# レビューデータが取得済みで、かつ現在のappidと一致する場合にダウンロードボタンを表示
if 'reviews' in st.session_state and st.session_state.reviews is not None and 'appid_processed' in st.session_state and st.session_state.appid_processed == int(appid_input):
    st.write("レビューデータの準備ができました。")
    csv_data = convert_reviews_to_csv(st.session_state.reviews)
    if csv_data:
        st.download_button(
            label="CSVファイルをダウンロード",
            data=csv_data,
            file_name=f"steam_reviews_{st.session_state.appid_processed}.csv",
            mime="text/csv",
        )
    else:
        st.warning("ダウンロードするレビューデータがありません。")
elif 'reviews' in st.session_state and st.session_state.reviews is None and 'appid_processed' in st.session_state and st.session_state.appid_processed == int(appid_input):
     st.warning("レビューの取得に失敗したか、レビューが存在しませんでした。")

# セッションステートの初期化（デバッグ用、必要に応じて）
# if st.button("クリア"):
#     st.session_state.clear()
#     st.rerun()