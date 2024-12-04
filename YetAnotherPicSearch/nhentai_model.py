from typing import cast

from lxml.html import HTMLParser, fromstring
from pyquery import PyQuery


class NHentaiItem:
    def __init__(self, data: PyQuery):
        self.origin: PyQuery = data  # 原始数据
        self.title: str = cast("str", data.find(".caption").text())
        cover = data.find(".cover")
        self.url: str = f'https://nhentai.net{cover.attr("href")}'
        self.thumbnail: str = cast("str", cover.find("img").attr("data-src"))
        self.type: str = ""
        self.date: str = ""
        self.tags: list[str] = []


class NHentaiResponse:
    def __init__(self, resp_text: str, resp_url: str):
        self.origin: str = resp_text  # 原始数据
        uft8_parser = HTMLParser(encoding="utf-8")
        data = PyQuery(fromstring(self.origin, parser=uft8_parser))
        self.raw: list[NHentaiItem] = [NHentaiItem(i) for i in data.find(".gallery").items()]
        self.url: str = resp_url
