import discord
from discord import app_commands
import logging
import re
import psutil
import time

# ログ設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# クライアントの設定（インテントを有効化）
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class LinkReplacerBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.start_time = time.time()

        # 置換対象の正規表現パターン
        self.target_pattern = re.compile(r'(?<!fixup)(?:twitter|x)\.com/', re.IGNORECASE)
        self.url_patterns = [
            (re.compile(r'https?://(?:www\.)?(?<!fixup)x\.com/'), 'https://fixupx.com/'),
            (re.compile(r'https?://(?:www\.)?(?<!fixup)twitter\.com/'), 'https://fixupx.com/'),
            (re.compile(r'(?<!fixup)x\.com/'), 'fixupx.com/'),
            (re.compile(r'(?<!fixup)twitter\.com/'), 'fixupx.com/')
        ]

    async def setup_hook(self):
        """ボット起動時の初期化処理"""
        logger.info("ボットの初期化を開始...")
        # スラッシュコマンドを同期（グローバル）
        await self.tree.sync()
        logger.info("スラッシュコマンドを同期しました")

    async def on_ready(self):
        """ボットが準備完了した時に実行"""
        logger.info(f'ボットがログインしました: {self.user.name} (ID: {self.user.id})')
        logger.info(f'接続中のサーバー数: {len(self.guilds)}')
        # ステータスを設定
        try:
            activity = discord.Activity(type=discord.ActivityType.watching,
                                        name="Twitterリンクをfixupxに変換中...")
            await self.change_presence(activity=activity)
            logger.info("ボットのステータスを設定しました")
        except Exception as e:
            logger.error(f"ステータス設定でエラー: {e}")

    async def on_guild_join(self, guild):
        """新しいサーバーに追加された時"""
        logger.info(f"新しいサーバーに参加しました: {guild.name} (ID: {guild.id})")

    async def on_guild_remove(self, guild):
        """サーバーから削除された時"""
        logger.info(f"サーバーから削除されました: {guild.name} (ID: {guild.id})")

    def replace_links(self, content: str) -> tuple[str, bool]:
        """メッセージ内のTwitter/X.comリンクをfixupx.comに置換"""
        logger.info(f"置換前のメッセージ: {content}")
        if 'fixupx.com' in content:
            logger.info("既にfixupx.comが含まれているため、置換をスキップ")
            return content, False

        modified = False
        new_content = content
        for pattern, replacement in self.url_patterns:
            if pattern.search(new_content):
                old_content = new_content
                new_content = pattern.sub(replacement, new_content)
                logger.info(f"パターン '{pattern.pattern}' で置換: '{old_content}' → '{new_content}'")
                modified = True

        logger.info(f"最終的な置換結果: {new_content}")
        return new_content, modified

    async def on_message(self, message):
        """メッセージを受信した時の処理"""
        try:
            # ボットのメッセージやDMは無視
            if message.author.bot or not message.guild:
                return

            # メッセージ内容に置換対象の単語が含まれているかチェック
            if not self.target_pattern.search(message.content):
                return

            # リンク置換
            new_content, was_modified = self.replace_links(message.content)
            if was_modified:
                # 権限チェック
                if not message.channel.permissions_for(message.guild.me).manage_messages:
                    logger.warning(f"メッセージ削除権限がありません: {message.guild.name}")
                    return
                if not message.channel.permissions_for(message.guild.me).send_messages:
                    logger.warning(f"メッセージ送信権限がありません: {message.guild.name}")
                    return

                try:
                    await message.delete()
                    logger.info(f"リンクを置換したメッセージを削除: {message.author.name} in {message.guild.name}")
                    formatted_message = f"{new_content} (by {message.author.display_name})"
                    await message.channel.send(formatted_message)
                    logger.info(f"置換後のメッセージを投稿: {message.author.name}")
                except discord.NotFound:
                    logger.warning("メッセージが既に削除されています")
                except discord.Forbidden:
                    logger.error("メッセージの削除/送信権限がありません")
                except Exception as e:
                    logger.error(f"メッセージ処理でエラー: {e}")
        except Exception as e:
            logger.error(f"on_messageでエラー: {e}")

# クライアントのインスタンス作成
client = LinkReplacerBot()

# スラッシュコマンド: /ping
@client.tree.command(name="ping", description="ボットの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"応答速度: {latency}ms", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

# スラッシュコマンド: /info
@client.tree.command(name="info", description="ボットの情報を表示します")
async def info(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 ボット情報", color=0x1DA1F2)
    embed.add_field(name="名前", value=client.user.name, inline=True)
    embed.add_field(name="ID", value=client.user.id, inline=True)
    embed.add_field(name="サーバー数", value=len(client.guilds), inline=True)
    embed.add_field(name="機能", value="TwitterとX.comのリンクをfixupx.comに自動変換", inline=False)
    embed.set_thumbnail(url=client.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# スラッシュコマンド: /test
@client.tree.command(name="test", description="リンク置換をテストします")
@app_commands.describe(text="テストするテキスト（例：https://x.com/example）")
async def test(interaction: discord.Interaction, text: str):
    if not text:
        await interaction.response.send_message("テストしたいテキストを入力してください。例: `/test https://x.com/example`")
        return

    new_text, was_modified = client.replace_links(text)
    embed = discord.Embed(title="🔧 リンク置換テスト", color=0xffaa00)
    embed.add_field(name="元のテキスト", value=f"```{text}```", inline=False)
    embed.add_field(name="変換後", value=f"```{new_text}```", inline=False)
    embed.add_field(name="変換されたか", value="✅ はい" if was_modified else "❌ いいえ", inline=True)
    await interaction.response.send_message(embed=embed)

# スラッシュコマンド: /restart
@client.tree.command(name="restart", description="ボットを再起動します（管理者専用）")
@app_commands.checks.has_permissions(administrator=True)
async def restart(interaction: discord.Interaction):
    embed = discord.Embed(title="🔄 ボット再起動", description="ボットを再起動しています...", color=0xff6600)
    await interaction.response.send_message(embed=embed)
    logger.info(f"ボット再起動が要求されました by {interaction.user.name}")
    # 少し待ってから再起動
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=2))
    await client.close()

# スラッシュコマンド: /status
@client.tree.command(name="status", description="ボットの詳細ステータスを表示します（管理者専用）")
@app_commands.checks.has_permissions(administrator=True)
async def status(interaction: discord.Interaction):
    process = psutil.Process()
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    cpu_percent = process.cpu_percent()
    embed = discord.Embed(title="📊 ボット詳細ステータス", color=0x00ff00)
    embed.add_field(name="🏓 レイテンシ", value=f"{round(client.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 サーバー数", value=len(client.guilds), inline=True)
    embed.add_field(name="👥 ユーザー数", value=len(client.users), inline=True)
    embed.add_field(name="💾 メモリ使用量", value=f"{memory_usage:.1f} MB", inline=True)
    embed.add_field(name="⚡ CPU使用率", value=f"{cpu_percent:.1f}%", inline=True)
    embed.set_footer(text=f"稼働時間: {time.strftime('%H:%M:%S', time.gmtime(time.time() - process.create_time()))}")
    await interaction.response.send_message(embed=embed)

# スラッシュコマンド: /health
@client.tree.command(name="health", description="システムヘルスチェックを行います（管理者専用）")
@app_commands.checks.has_permissions(administrator=True)
async def health(interaction: discord.Interaction):
    embed = discord.Embed(title="🏥 ヘルスチェック", color=0x00ff00)
    # Discord接続状態
    if client.is_closed():
        embed.add_field(name="🤖 Discord接続", value="❌ 切断", inline=True)
    else:
        embed.add_field(name="🤖 Discord接続", value="✅ 接続中", inline=True)
    # 権限チェック
    permissions = interaction.channel.permissions_for(interaction.guild.me)
    embed.add_field(name="🔒 メッセージ削除権限", value="✅ あり" if permissions.manage_messages else "❌ なし", inline=True)
    embed.add_field(name="📝 メッセージ送信権限", value="✅ あり" if permissions.send_messages else "❌ なし", inline=True)
    await interaction.response.send_message(embed=embed)

def run_bot(token: str):
    """ボットを実行"""
    try:
        client.run(token)
    except discord.LoginFailure:
        logger.error("無効なDiscordトークンです")
    except discord.HTTPException as e:
        logger.error(f"Discord APIエラー: {e}")
    except Exception as e:
        logger.error(f"ボット実行中にエラー: {e}")