# 使用教程

## 日常使用

- 私聊：
  - 发送指令及参数进入搜图模式，详见下方的 [搜图模式](#搜图模式)
  - 发送指令及参数时附带或回复图片
  - 直接发送图片 (如果禁用了 `SEARCH_IMMEDIATELY` 则无效)
- 群聊：
  - 发送指令及参数进入搜图模式，详见下方的 [搜图模式](#搜图模式)
  - 发送指令及参数时附带或回复图片
  - `@机器人` 并发送或回复图片（如果禁用 `SEARCH_IN_GROUP_ONLY_KEYWORD` 则无效）
- 可以在同一条消息中包含多张图片，会自动批量搜索
- 搜索图片时可以在消息内包含以下参数：
  - `--purge` - 无视缓存进行搜图，并更新缓存
  - 指定搜索范围（以下参数仅可选一个）：
    - `--all` - 全库搜索 (默认)
    - `--pixiv` - 从 Pixiv 中搜索
    - `--danbooru` - 从 Danbooru 中搜索
    - `--doujin` - 搜索本子
    - `--anime` - 搜索番剧
    - `--a2d` - 使用 Ascii2D 进行搜索 (优势搜索局部图能力较强)
    - `--baidu` - 使用 Baidu 进行搜索
    - `--ex` - 使用 ExHentai (E-Hentai) 进行搜索
    - `--google` - 使用 Google 进行搜索
    - `--iqdb` - 使用 Iqdb 进行搜索
    - `--yandex` - 使用 Yandex 进行搜索
- 对于 SauceNAO：
  - 如果得到的结果相似度低于 60% (可配置)，会自动使用 Ascii2D 进行搜索 (可配置)
  - 如果额度耗尽，会自动使用 Ascii2D 进行搜索
  - 如果搜索到本子，会自动在 ExHentai (E-Hentai) 中搜索并返回链接 (如果有汉化本会优先返回汉化本链接)
  - 如果搜到番剧，会自动使用 WhatAnime 搜索番剧详细信息：
    - AnimeDB 与 WhatAnime 的结果可能会不一致，是正常现象，毕竟这是两个不同的搜索引擎
    - 同时展示这两个搜索的目的是为了尽力得到你可能想要的识别结果
- 对于 ExHentai：
  - 如果没有配置 `EXHENTAI_COOKIES` ，会自动回退到 `E-Hentai` 搜索
  - 不支持单色图片的搜索，例如黑白漫画，只推荐用于搜索 CG 、画集、图集、彩色漫画、彩色封面等
  - 如果没有配置 `SUPERUSERS` ，不会显示搜索结果的收藏状态
- 关于消息发送失败的情况：  
  在某些国内平台如 QQ 上，这可能是因为消息中包含的链接被列入黑名单，成了所谓的 `红链`。  
  需确定哪个网站的域名被封禁了，然后配置 `TO_CONFUSE_URLS` 配置项来规避。

## 搜图模式

搜图模式存在的意义是方便用户在转发图片等不方便在消息中夹带 @ 或搜图参数的情况下指定搜索范围或者使用某项功能：

- 发送指令并附上搜索范围或者功能参数，如果没有指定，会使用默认设置 (即 `--all`)
- 此时你发出来的下一条消息中的图 (也就是一次性的) 会使用指定搜索范围或者使用某项功能