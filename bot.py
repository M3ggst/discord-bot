import discord
from discord.ext import commands
import logging
import re
import asyncio
from typing import Optional

# ログ設定
logger = logging.getLogger(__name__)

class LinkReplacerBot(commands.Bot):
    """TwitterとX.comのリンクをfixupx.comに置換するDiscordボット"""

    def __init__(self):
        # 必要なインテントを設定
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        super().__init__(command_prefix='!',
                         intents=intents,
                         help_command=commands.DefaultHelpCommand())

        # 置換対象の単語をチェックするための正規表現パターン（簡略化）
        self.target_pattern = re.compile(r'(?<!fixup)(?:twitter|x)\.com/', re.IGNORECASE)

        # URL置換パターン（より具体的なパターンを先に、既に置換済みのURLは除外）
        self.url_patterns = [
            (re.compile(r'https?://(?:www\.)?(?<!fixup)x\.com/'), 'https://fixupx.com/'),
            (re.compile(r'https?://(?:www\.)?(?<!fixup)twitter\.com/'), 'https://fixupx.com/'),
            (re.compile(r'(?<!fixup)x\.com/'), 'fixupx.com/'),
            (re.compile(r'(?<!fixup)twitter\.com/'), 'fixupx.com/')
        ]

    async def setup_hook(self):
        """ボット起動時の初期化処理"""
        logger.info("ボットの初期化を開始...")

    async def on_ready(self):
        """ボットが準備完了した時に実行"""
        logger.info(f'ボットがログインしました: {self.user.name} (ID: {self.user.id})')
        logger.info(f'接続中のサーバー数: {len(self.guilds)}')

        # ボットのステータスを設定
        try:
            activity = discord.Activity(type=discord.ActivityType.watching,
                                        name="Twitterリンクをfixupxに変換中...")
            await self.change_presence(activity=activity,
                                       status=discord.Status.online)
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
        """
        メッセージ内のTwitter/X.comリンクをfixupx.comに置換

        Args:
            content: 元のメッセージ内容

        Returns:
            tuple: (置換後の内容, 置換が行われたかどうか)
        """
        logger.info(f"置換前のメッセージ: {content}")

        # 既にfixupx.comが含まれている場合は何もしない
        if 'fixupx.com' in content:
            logger.info("既にfixupx.comが含まれているため、置換をスキップ")
            return content, False

        modified = False
        new_content = content

        for pattern, replacement in self.url_patterns:
            if pattern.search(new_content):
                old_content = new_content
                new_content = pattern.sub(replacement, new_content)
                logger.info(
                    f"パターン '{pattern.pattern}' で置換: '{old_content}' → '{new_content}'")
                modified = True

        logger.info(f"最終的な置換結果: {new_content}")
        return new_content, modified

    async def on_message(self, message):
        """メッセージを受信した時の処理"""
        try:
            # ボット自身のメッセージは無視
            if message.author == self.user:
                return

            # システムメッセージは無視
            if message.type != discord.MessageType.default:
                return

            # メッセージ内容に置換対象の単語が含まれているかチェック
            if not self.target_pattern.search(message.content):
                return  # 対象単語がない場合は即座にスキップ

            # メッセージ内容をチェックして置換
            new_content, was_modified = self.replace_links(message.content)

            if was_modified:
                # 権限チェック
                if not message.channel.permissions_for(
                        message.guild.me).manage_messages:
                    logger.warning(f"メッセージ削除権限がありません: {message.guild.name}")
                    return

                if not message.channel.permissions_for(
                        message.guild.me).send_messages:
                    logger.warning(f"メッセージ送信権限がありません: {message.guild.name}")
                    return

                try:
                    # 元のメッセージを削除
                    await message.delete()
                    logger.info(
                        f"リンクを置換したメッセージを削除: {message.author.name} in {message.guild.name}"
                    )

                    # 新しいメッセージを通常のテキストとして投稿（投稿者名を付ける）
                    formatted_message = f"{new_content} (by {message.author.display_name})"

                    await message.channel.send(formatted_message)
                    logger.info(f"置換後のメッセージを投稿: {message.author.name}")

                except discord.NotFound:
                    logger.warning("メッセージが既に削除されています")
                except discord.Forbidden:
                    logger.error("メッセージの削除/送信権限がありません")
                except Exception as e:
                    logger.error(f"メッセージ処理でエラー: {e}")

            # コマンドも処理
            await self.process_commands(message)

        except Exception as e:
            logger.error(f"on_messageでエラー: {e}")

    async def on_error(self, event, *args, **kwargs):
        """エラーハンドリング"""
        logger.error(f"イベント '{event}' でエラーが発生しました", exc_info=True)

# コマンド定義
@commands.command(name='ping')
async def ping(ctx):
    """ボットの応答速度をテスト"""
    latency = round(ctx.bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!",
                          description=f"応答速度: {latency}ms",
                          color=0x00ff00)
    await ctx.send(embed=embed)

@commands.command(name='info')
async def info(ctx):
    """ボットの情報を表示"""
    bot = ctx.bot
    embed = discord.Embed(title="🤖 ボット情報", color=0x1DA1F2)
    embed.add_field(name="名前", value=bot.user.name, inline=True)
    embed.add_field(name="ID", value=bot.user.id, inline=True)
    embed.add_field(name="サーバー数", value=len(bot.guilds), inline=True)
    embed.add_field(name="機能",
                    value="TwitterとX.comのリンクをfixupx.comに自動変換",
                    inline=False)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@commands.command(name='test')
async def test_replacement(ctx, *, text: str = None):
    """リンク置換のテスト"""
    if not text:
        await ctx.send("テストしたいテキストを入力してください。例: `!test https://x.com/example`")
        return

    bot = ctx.bot
    new_text, was_modified = bot.replace_links(text)

    embed = discord.Embed(title="🔧 リンク置換テスト", color=0xffaa00)
    embed.add_field(name="元のテキスト", value=f"```{text}```", inline=False)
    embed.add_field(name="変換後", value=f"```{new_text}```", inline=False)
    embed.add_field(name="変換されたか",
                    value="✅ はい" if was_modified else "❌ いいえ",
                    inline=True)

    await ctx.send(embed=embed)

@commands.command(name='restart')
@commands.has_permissions(administrator=True)
async def restart_bot(ctx):
    """ボットを再起動（管理者専用）"""
    embed = discord.Embed(title="🔄 ボット再起動",
                          description="ボットを再起動しています...",
                          color=0xff6600)
    await ctx.send(embed=embed)

    logger.info(f"ボット再起動が要求されました by {ctx.author.name}")

    # 少し待ってから再起動
    await asyncio.sleep(2)
    await ctx.bot.close()

@commands.command(name='status')
@commands.has_permissions(administrator=True)
async def bot_status(ctx):
    """ボットの詳細ステータス（管理者専用）"""
    import psutil
    import time

    bot = ctx.bot

    # システム情報
    process = psutil.Process()
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    cpu_percent = process.cpu_percent()

    embed = discord.Embed(title="📊 ボット詳細ステータス", color=0x00ff00)
    embed.add_field(name="🏓 レイテンシ",
                    value=f"{round(bot.latency * 1000)}ms",
                    inline=True)
    embed.add_field(name="🏠 サーバー数", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 ユーザー数", value=len(bot.users), inline=True)
    embed.add_field(name="💾 メモリ使用量",
                    value=f"{memory_usage:.1f} MB",
                    inline=True)
    embed.add_field(name="⚡ CPU使用率", value=f"{cpu_percent:.1f}%", inline=True)
    embed.set_footer(
        text=
        f"稼働時間: {time.strftime('%H:%M:%S', time.gmtime(time.time() - process.create_time()))}"
    )

    await ctx.send(embed=embed)

@commands.command(name='health')
@commands.has_permissions(administrator=True)
async def health_check(ctx):
    """システムヘルスチェック（管理者専用）"""
    embed = discord.Embed(title="🏥 ヘルスチェック", color=0x00ff00)

    # Discord接続状態
    if ctx.bot.is_closed():
        embed.add_field(name="🤖 Discord接続", value="❌ 切断", inline=True)
    else:
        embed.add_field(name="🤖 Discord接続", value="✅ 接続中", inline=True)

    # 権限チェック
    permissions = ctx.channel.permissions_for(ctx.guild.me)
    embed.add_field(name="🔒 メッセージ削除権限",
                    value="✅ あり" if permissions.manage_messages else "❌ なし",
                    inline=True)
    embed.add_field(name="📝 メッセージ送信権限",
                    value="✅ あり" if permissions.send_messages else "❌ なし",
                    inline=True)

    await ctx.send(embed=embed)

def run_bot(token: str):
    """ボットを実行"""
    bot = LinkReplacerBot()

    # コマンドを追加
    bot.add_command(ping)
    bot.add_command(info)
    bot.add_command(test_replacement)
    bot.add_command(restart_bot)
    bot.add_command(bot_status)
    bot.add_command(health_check)

    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("無効なDiscordトークンです")
    except discord.HTTPException as e:
        logger.error(f"Discord APIエラー: {e}")
    except Exception as e:
        logger.error(f"ボット実行中にエラー: {e}")