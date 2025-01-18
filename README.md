<!-- markdownlint-disable MD031 MD033 MD036 MD041 MD045 -->

<div align="center">

<a href="https://v2.nonebot.dev/store">
  <img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo">
</a>

<p>
  <img src="https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/template/plugin.svg" alt="NoneBotPluginText">
</p>

# YetAnotherPicSearch

_✨ 基于 [NoneBot2](https://github.com/nonebot/nonebot2) 与 [PicImageSearch](https://github.com/kitUIN/PicImageSearch) 的另一个 NoneBot 搜图插件 ✨_

<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
<a href="https://pdm.fming.dev">
  <img src="https://img.shields.io/badge/pdm-managed-blueviolet" alt="pdm-managed">
</a>

<br />

<a href="https://pydantic.dev">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/template/pyd-v1-or-v2.json" alt="Pydantic Version 1 Or 2" >
</a>
<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/lgc-NB2Dev/YetAnotherPicSearch.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/YetAnotherPicSearch">
  <img src="https://img.shields.io/pypi/v/YetAnotherPicSearch.svg" alt="pypi">
</a>
<a href="https://pypi.python.org/pypi/YetAnotherPicSearch">
  <img src="https://img.shields.io/pypi/dm/YetAnotherPicSearch" alt="pypi download">
</a>

<br />

<a href="https://registry.nonebot.dev/plugin/yetanotherpicsearch:YetAnotherPicSearch">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fnbbdg.lgc2333.top%2Fplugin%2FYetAnotherPicSearch" alt="NoneBot Registry">
</a>
<a href="https://registry.nonebot.dev/plugin/yetanotherpicsearch:YetAnotherPicSearch">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fnbbdg.lgc2333.top%2Fplugin-adapters%2FYetAnotherPicSearch" alt="Supported Adapters">
</a>

</div>

## 📖 介绍

主要受到 [cq-picsearcher-bot](https://github.com/Tsuk1ko/cq-picsearcher-bot) 的启发。我只需要基础的搜图功能，于是忍不住自己也写了一个，用来搜图、搜番、搜本子。

目前支持的搜图服务：  
[Ascii2D](https://ascii2d.net/) | [Baidu](https://graph.baidu.com/) | [E-Hentai](https://e-hentai.org/) | [ExHentai](https://exhentai.org/) | [Google](https://www.google.com/imghp) | [Iqdb](https://iqdb.org/) | [SauceNAO](https://saucenao.com/) | [TraceMoe](https://trace.moe/) | [Yandex](https://yandex.com/images/search)

## 💿 安装

以下提到的方法 任选**其一** 即可

<details open>
<summary>[推荐] 使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

```bash
nb plugin install YetAnotherPicSearch
```

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

```bash
pip install YetAnotherPicSearch
```

</details>
<details>
<summary>pdm</summary>

```bash
pdm add YetAnotherPicSearch
```

</details>
<details>
<summary>poetry</summary>

```bash
poetry add YetAnotherPicSearch
```

</details>
<details>
<summary>conda</summary>

```bash
conda install YetAnotherPicSearch
```

</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分的 `plugins` 项里追加写入

```toml
[tool.nonebot]
plugins = [
    # ...
    "YetAnotherPicSearch"
]
```

</details>

## ⚙️ 配置

|             配置项             |             必填             |        默认值         |                                                                                                                 说明                                                                                                                  |
| :----------------------------: | :--------------------------: | :-------------------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|          **通用配置**          |                              |                       |                                                                                                                                                                                                                                       |
|            `PROXY`             |              否              |        `None`         |                                                               大部分请求所使用的代理地址，如需要 socks 协议支持请额外执行 `pip install YetAnotherPicSearch[socks]` 安装                                                               |
|         **数据源配置**         |                              |                       |                                                                                                                                                                                                                                       |
|       `SAUCENAO_API_KEY`       | $${\textsf{\color{red}是}}$$ |          无           | SauceNAO 的 API KEY，在 [这里](https://saucenao.com/user.php) 注册后到 [这里](https://saucenao.com/user.php?page=search-api) 获取<br />如果 SauceNAO 的 API 使用触发当日上限，请同时换新的 API Key 和代理节点，仅换其中一个没有意义。 |
|       `ASCII2D_BASE_URL`       |              否              | `https://ascii2d.net` |                                                                       Ascii2D Base URL \([#139](https://github.com/lgc-NB2Dev/YetAnotherPicSearch/issues/139)\)                                                                       |
|       `EXHENTAI_COOKIES`       |              否              |        `None`         |             ExHentai 的 Cookies，没有的情况下自动改用 E-Hentai 搜图，获取方式参考 请参考 [PicImageSearch 文档](https://pic-image-search.kituin.fun/wiki/picimagesearch/E-hentai/DataStructure/#cookies%E8%8E%B7%E5%8F%96)             |
|      `NHENTAI_USERAGENT`       |              否              |        `None`         |     用来绕过 NHentai Cloudflare 拦截的 User Agent，配置后在 E-Hentai 标题搜索无结果时会自动调用 NHentai 标题搜索<br />先用配置的 `PROXY` 做代理，使用浏览器访问 NHentai 通过 CloudFlare 检测后，获取 UA 和 Cookies 填到对应配置项     |
|       `NHENTAI_COOKIES`        |              否              |        `None`         |                                                                                           用来绕过 NHentai Cloudflare 拦截的 Cookies，同上                                                                                            |
|          **行为配置**          |                              |                       |                                                                                                                                                                                                                                       |
|       `SAUCENAO_LOW_ACC`       |              否              |         `60`          |                                                                                           SauceNAO 相似度低于这个百分比将被认定为相似度过低                                                                                           |
|       `AUTO_USE_ASCII2D`       |              否              |        `True`         |                                                                            是否在 SauceNAO 或 IQDB 相似度过低时 / E-Hentai 无结果时 自动使用 Ascii2D 搜索                                                                             |
|          **交互配置**          |                              |                       |                                                                                                                                                                                                                                       |
|        `SEARCH_KEYWORD`        |              否              |        `搜图`         |                                                                                          触发插件功能的指令名，使用时记得带上你配置的指令头                                                                                           |
|     `SEARCH_KEYWORD_ONLY`      |              否              |        `False`        |                                                                        是否只响应指令消息（优先级高于 `SEARCH_IN_GROUP_ONLY_KEYWORD` 与 `SEARCH_IMMEDIATELY`）                                                                        |
| `SEARCH_IN_GROUP_ONLY_KEYWORD` |              否              |        `True`         |                                                                                      是否在群聊中只响应指令消息，否则可以通过 @Bot 触发搜图模式                                                                                       |
|      `SEARCH_IMMEDIATELY`      |              否              |        `True`         |                                                                                            私聊发送图片是否直接触发搜图，否则需要使用命令                                                                                             |
|    `WAIT_FOR_IMAGE_TIMEOUT`    |              否              |         `180`         |                                                                                         当用户未提供图片时，提示用户提供图片的等待时间（秒）                                                                                          |
|          **消息配置**          |                              |                       |                                                                                                                                                                                                                                       |
|           `HIDE_IMG`           |              否              |        `False`        |                                                                                                       隐藏所有搜索结果的缩略图                                                                                                        |
|    `HIDE_IMG_WHEN_LOW_ACC`     |              否              |        `True`         |                                                                                           SauceNAO / IQDB 得到低相似度结果时隐藏结果缩略图                                                                                            |
| `HIDE_IMG_WHEN_WHATANIME_R18`  |              否              |        `True`         |                                                                                                WhatAnime 得到 R18 结果时隐藏结果缩略图                                                                                                |
|   `SAUCENAO_NSFW_HIDE_LEVEL`   |              否              |          `2`          |                           对 SauceNAO 的搜索结果进行 NSFW 判断的严格程度（依次递增），启用后自动隐藏相应的 NSFW 结果的缩略图<br />`0`：不判断， `1`：只判断明确的， `2`：包括可疑的， `3`：非明确为 SFW 的                            |
|    `FORWARD_SEARCH_RESULT`     |              否              |        `True`         |                                                                              若结果消息有多条，是否采用合并转发方式发送搜图结果（平台不支持会自动回退）                                                                               |
|       `TO_CONFUSE_URLS`        |              否              |          ...          |                                                                   要破坏处理的网址列表，减少风控概率（发出来的消息包含这些网址会在网址的 `://` 与 `.` 后加上空格）                                                                    |
|          **杂项配置**          |                              |                       |                                                                                                                                                                                                                                       |
|         `CACHE_EXPIRE`         |              否              |          `3`          |                                                                                                         消息缓存过期时间 (天)                                                                                                         |

## 🎉 使用

使用你配置的指令（默认为 `搜图`）即可开始使用，附带或回复图片可直接触发搜图，可以一次性带多张图  
更详细的使用方法请参考 [这里](https://github.com/lgc-NB2Dev/YetAnotherPicSearch/tree/main/docs/usage.md)

### 效果图

<p float="left">
    <img src="docs/images/image01.jpg" width="32%" />
    <img src="docs/images/image02.jpg" width="32%" />
    <img src="docs/images/image03.jpg" width="32%" />
</p>

## 📞 联系

<!--
### NekoAria

暂无
-->

### LgCookie

QQ：3076823485  
Telegram：[@lgc2333](https://t.me/lgc2333)  
吹水群：[1105946125](https://jq.qq.com/?_wv=1027&k=Z3n1MpEp)  
邮箱：<lgc2333@126.com>

## 💡 鸣谢

- [cq-picsearcher-bot](https://github.com/Tsuk1ko/cq-picsearcher-bot)
- [PicImageSearch](https://github.com/kitUIN/PicImageSearch)
- [NoneBot2](https://github.com/nonebot/nonebot2)
- [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)

## 💰 赞助

**[赞助我](https://blog.lgc2333.top/donate)**

感谢大家的赞助！你们的赞助将是我继续创作的动力！

## ⭐ Star History

[![Star History](https://starchart.cc/lgc-NB2Dev/YetAnotherPicSearch.svg)](https://starchart.cc/lgc-NB2Dev/YetAnotherPicSearch)

## 📝 更新日志

### 2.0.4

- 兼容 HTTPX 0.28

### 2.0.3

- 移除重复搜索结果并添加数量提示

### 2.0.2

- 添加配置项用于自定义 Ascii2D 的 Base URL

### 2.0.1

- 修复 [#137](https://github.com/lgc-NB2Dev/YetAnotherPicSearch/issues/137)
  - 修复文本重复的问题
  - 修复 ExHentai 始终显示无法使用的问题
- 修复缓存消息显示问题
- 添加缺失依赖

### 2.0.0

项目重构：

- 使用 alconna 支持多平台，重构消息缓存
- 将之前的 `搜图关键词` 改为指令；同时由于不方便判断是否回复的是 Bot 自身消息，所以阉掉了这个
- 其他细节更改
- 配置变动：
  - 新增 `SEARCH_IN_GROUP_ONLY_KEYWORD`
  - 新增 `WAIT_FOR_IMAGE_TIMEOUT`

以前的更新日志请在 Releases 中查看
