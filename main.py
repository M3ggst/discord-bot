import os
import logging
from bot import run_bot

# ログ設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 環境変数からトークンを取得
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logging.error("DISCORD_TOKENが設定されていません")
    exit(1)

# ボットの起動
logging.info("Discordボットを起動しています...")
run_bot(TOKEN)