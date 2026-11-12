"""Comments are written in Markdown, with code blocks, and rendered to HTML that is
cleaned (with nh3) of everything but a few harmless tags, since anyone may write
them. Links are marked nofollow and ugc (user-generated content), which tells
search engines not to credit them, so spam links gain nothing."""

import markdown
import nh3

TAGS = {"p", "br", "pre", "code", "em", "strong", "a", "ul", "ol", "li", "blockquote"}


def render(text):
    html = markdown.markdown(text, extensions=["fenced_code", "sane_lists"])
    return nh3.clean(
        html,
        tags=TAGS,
        attributes={"a": {"href"}, "code": {"class"}},
        url_schemes={"http", "https", "mailto"},
        link_rel="nofollow ugc noopener",
    )


def link_count(html):
    return html.count("<a ")
