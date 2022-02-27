from .buy_and_sell import BuyAndSell
from .earn_money import EarnMoney
from .trade_items import TradeItems
from .use_items import UseItems
from .wallet_management import WalletManagement


class Economy(BuyAndSell, EarnMoney, TradeItems, UseItems, WalletManagement):
    """ 🪙 Economy commands! This is a work in progress.
    **To get started run the `%PRE%eco start` command**
    See more useful commands in the `%PRE%help eco` command. """

    select_emoji = "\U0001fa99"
    select_brief = "WORK IN PROGRESS economy commands."


def setup(bot):
    bot.add_cog(Economy(bot))
