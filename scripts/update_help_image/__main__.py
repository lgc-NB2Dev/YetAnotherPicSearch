import asyncio
from pathlib import Path
from typing import Literal, Union, cast

import nonebot
from nonebot.drivers.none import Driver as NoneDriver
from nonebot_plugin_htmlrender.data_source import (
    TEMPLATES_PATH,
    env,
    get_new_page,
    markdown,
    read_tpl,
)


async def md_to_pic(
    md: str = "",
    extra_css: str = "",
    type: Literal["jpeg", "png"] = "png",  # noqa: A002
    quality: Union[int, None] = None,
    device_scale_factor: float = 2,
) -> bytes:
    template = env.get_template("markdown.html")
    md = markdown.markdown(
        md,
        extensions=[
            "pymdownx.tasklist",
            "tables",
            "fenced_code",
            "codehilite",
            "mdx_math",
            "pymdownx.tilde",
        ],
        extension_configs={"mdx_math": {"enable_dollar_delimiter": True}},
        tab_length=2,
    )

    extra = ""
    if "math/tex" in md:
        katex_css, katex_js, mathtex_js = await asyncio.gather(
            read_tpl("katex/katex.min.b64_fonts.css"),
            read_tpl("katex/katex.min.js"),
            read_tpl("katex/mathtex-script-type.min.js"),
        )
        extra = (
            f'<style type="text/css">{katex_css}</style>'
            f"<script defer>{katex_js}</script>"
            f"<script defer>{mathtex_js}</script>"
        )

    github_md_css, pygments_css = await asyncio.gather(
        read_tpl("github-markdown-light.css"),
        read_tpl("pygments-default.css"),
    )
    css = f"{github_md_css}\n{pygments_css}\n{extra_css}"

    html = await template.render_async(css=css, md=md, extra=extra)

    async with get_new_page(device_scale_factor) as page:
        await page.goto(f"file://{TEMPLATES_PATH}")
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_load_state("load")
        elem = await page.query_selector("article.markdown-body")
        assert elem
        return await elem.screenshot(type=type, quality=quality)


driver = nonebot.get_driver()


@driver.on_startup
async def _():
    project_root = Path(__file__).parent.parent.parent
    help_md_path = project_root / "docs" / "usage.md"
    help_img_path = project_root / "YetAnotherPicSearch" / "res" / "usage.jpg"
    if not (p := help_img_path.parent).exists():
        p.mkdir(parents=True)

    help_md = help_md_path.read_text("u8")
    help_img = await md_to_pic(help_md, type="jpeg")
    help_img_path.write_bytes(help_img)

    cast(NoneDriver, driver).exit()


nonebot.run()
