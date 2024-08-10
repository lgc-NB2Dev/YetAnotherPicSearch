# ruff: noqa: E402

import nonebot

nonebot.init(driver="~none")

from nonebot.plugin import require

require("nonebot_plugin_htmlrender")
