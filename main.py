from calendar import c
from shutil import move
from colorama import init
from keyboard import send
from pyautogui import moveTo
from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import *
import random

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.score = 0
        self.status = 0 # 0 参与游戏，1 不再加牌，2 已爆牌
        
    def calculate_score(self):
        # 计算牌值
        self.score = 0
        for instance in self.hand:
            self.score += sum(instance.values())
        return self.score
    
    def is_bust(self):
        # 判断是否爆牌
        return self.calculate_score() > 21

# 注册插件
@register(name="BlackJack", description="BlackJack", version="0.1", author="Amethyst")
class BlackJackPlugin(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.init = False   # 房间是否初始化标志位
        self.start = False  # 对局是否进行中标志位
        self.players = []   # 玩家列表
        self.cards = []     # 牌
        self.pointer = 0    # 指针指向当前玩家
                
    def shuffleCards(self):
        # 洗牌
        # 定义花色和数字
        suits = ['♥', '♦', '♣', '♠']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        # 初始化牌
        for suit in suits:
            for rank in ranks:
                # J, Q, K 的值为 10，A 初始设置为 1。
                value = 10 if rank in ['J', 'Q', 'K'] else (1 if rank == 'A' else int(rank))
                card = f'{suit}: {rank}'
                self.cards.append({card: value})
        random.shuffle(self.cards)
    
    def dealCards(self):
        # 初始化牌并给每个玩家发牌
        self.shuffleCards()
        for i in range(len(self.players)):
            for j in range(2):
                self.players[i].hand.append(self.cards.pop())
    
    def getCard(self):
        # 获取一张牌
        card = self.cards.pop()
        self.players[self.pointer].hand.append(card)
        return card
    
    def moveToNextPlayer(self):
        # 切换到下一个玩家
        while self.players[self.pointer].status != 0:
            self.pointer = (self.pointer + 1) % len(self.players)
    
    def isEnd(self):
        # 判断游戏是否结束
        for player in self.players:
            if player.status == 0:
                return False
        return True        

    def chooseWinner(self):
        winner = [{
            "name":None,
            "score":0
        }]
        for player in self.players:
            if player.status == 2:
                continue
            if winner[0].get("score") < player.calculate_score():
                winner = [{"name":player.name, "score":player.calculate_score()}]
            elif winner[0].get("score") == player.calculate_score():
                winner.append({"name":player.name, "score":player.calculate_score()})
        self.init = False   # 重置房间初始化标志位
        self.start = False  # 重置开始标志位
        self.players = []   # 重置玩家
        self.cards = []     # 重置牌
        self.pointer = 0    # 重置指针
        return winner
    
    # 异步初始化
    async def initialize(self):
        pass

    # 当收到群消息时触发
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.text_message
        sender_id = ctx.event.sender_id # 获取发送消息的用户 ID
        # 创建新对局
        if msg == "21点" or msg == "blackjack":  
            if not self.init: # 若未创建则创建新对局
                self.init = True
                self.players.append(Player(sender_id))
                ctx.add_return("reply", ["[BlackJack] {}创建游戏，输入“加入游戏”进入游戏...\n当前玩家：{}".format(sender_id, [instance.name for instance in self.players])])
                ctx.prevent_default()
            else:
                ctx.add_return("reply", ["[BlackJack] 创建失败，游戏已被创建 ( ﾟДﾟ)"])
                ctx.prevent_default()
        # 加入游戏
        elif msg == "加入游戏" and (not any(instance.name == sender_id for instance in self.players)):
            if self.init: # 若已创建对局则加入对局
                self.players.append(Player(sender_id))
                ctx.add_return("reply", ["[BlackJack] {}已加入游戏\n当前玩家：{}".format(sender_id, [instance.name for instance in self.players])])
                ctx.prevent_default()
            else:
                ctx.add_return("reply", ["[BlackJack] 请先创建游戏 ( ﾟДﾟ)"])
                ctx.prevent_default()
        # 开始游戏
        elif msg == "开始游戏" and any(instance.name == sender_id for instance in self.players):
            if (not self.start) and self.init: # 若游戏已被创建且未开始则开始游戏
                if len(self.players) < 2: # 至少有两个玩家
                    ctx.add_return("reply", ["[BlackJack] 开始游戏失败，至少需要两个玩家( ﾟДﾟ)"])
                    ctx.prevent_default()
                else:   # 开始游戏
                    self.start = True
                    await ctx.reply(MessageChain([
                        Plain(f"[BlackJack] 开始游戏！(ゝ∀･)\n玩家：{[instance.name for instance in self.players]}")
                    ]))
                    self.dealCards()     # 发牌
                    for player in self.players:
                        await ctx.reply(MessageChain([Plain(f"[BlackJack] {player.name}手牌为：{self.players[self.players.index(player)].hand}")]))        
                    await ctx.reply(MessageChain([Plain("[BlackJack]"), At(self.players[self.pointer].name), Plain(" 请问是否继续要牌？回复“要牌”或“不要牌”")]))
                    ctx.prevent_default()
        # 游戏过程中
        elif (msg == "要牌" or msg == "不要牌") and self.init and self.start:
            if msg == "要牌" and sender_id == self.players[self.pointer].name:
                if sender_id == self.players[self.pointer].name:
                    card = self.getCard()  # 获取一张牌
                    await ctx.reply(MessageChain([Plain(f"[BlackJack] {sender_id}抽到了 {card}\n手牌为{self.players[self.pointer].hand}\n点数总和为：{self.players[self.pointer].calculate_score()}")]))
                    if self.players[self.pointer].is_bust():
                        await ctx.reply(MessageChain([Plain("[BlackJack] 爆！_(:3 」∠ )_"), At(sender_id)]))
                        self.players[self.pointer].status = 2  # 玩家爆牌
                    if self.isEnd():
                        await ctx.reply(MessageChain([Plain("[BlackJack] 游戏结束！")]))
                        await ctx.reply(MessageChain([Plain(f"[BlackJack]\n胜者(ﾉ>ω<)ﾉ：{self.chooseWinner()}")]))
                        return
                    self.moveToNextPlayer()
                else:
                    ctx.add_return("reply", ["[BlackJack] 你先别急"])
            
            if msg == "不要牌" and sender_id == self.players[self.pointer].name:
                if sender_id == self.players[self.pointer].name:
                    self.players[self.pointer].status = 1  # 玩家不再加牌
                    await ctx.reply(MessageChain([Plain(f"[BlackJack] {self.players[self.pointer].name} 不再加牌！\n手牌为{self.players[self.pointer].hand}\n点数总和为：{self.players[self.pointer].calculate_score()}")]))
                    if self.isEnd():
                        await ctx.reply(MessageChain([Plain("[BlackJack] 游戏结束！")]))
                        await ctx.reply(MessageChain([Plain(f"[BlackJack]\n胜者(ﾉ>ω<)ﾉ：{self.chooseWinner()}")]))
                        return
                    self.moveToNextPlayer()
                else:
                    ctx.add_return("reply", ["[BlackJack] 你先别急"])
                    
            await ctx.reply(MessageChain([Plain("[BlackJack]"), At(self.players[self.pointer].name), Plain(" 请问是否继续要牌？回复“要牌”或“不要牌”")]))
            ctx.prevent_default()
                    
        # 终止游戏      
        elif msg == "结束游戏" and any(instance.name == sender_id for instance in self.players):
            if self.init : 
                self.init = False   # 重置房间初始化标志位
                self.start = False  # 重置开始标志位
                self.players = []   # 重置玩家
                self.cards = {}     # 重置牌
                ctx.add_return("reply", ["[BlackJack] 游戏已终止！Σ(ﾟωﾟ)"])
                ctx.prevent_default()

    # 插件卸载时触发
    def __del__(self):
        pass
