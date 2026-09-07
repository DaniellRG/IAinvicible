import html
import re


def _extract_code_blocks(text: str):
    placeholders = {}
    counter = [0]

    def repl(m):
        lang = (m.group(1) or "").strip()
        code = m.group(2)
        key = "\x00CB%d\x00" % counter[0]
        counter[0] += 1
        lang_attr = f' class="code-lang-{html.escape(lang)}"' if lang else ""
        placeholders[key] = (
            "<pre style='background-color:#161d2a; color:#c5cdd8;"
            " border:1px solid #1e2a3a; border-radius:8px; padding:10px;"
            " margin:6px 0; font-family:Consolas,Consolas,'JetBrains Mono',monospace;"
            " font-size:12px; white-space:pre-wrap;'>"
            f"<code{lang_attr}>{html.escape(code)}</code></pre>"
        )
        return key

    work = re.sub(r"```(\w*)\s*\n(.*?)```", repl, text, flags=re.S)
    return work, placeholders


def _restore(work: str, placeholders: dict) -> str:
    for key, value in placeholders.items():
        work = work.replace(key, value)
    return work


def _render_inline(escaped: str) -> str:
    escaped = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", escaped)
    return escaped


def md_to_html(text: str) -> str:
    if not text:
        return ""

    work, placeholders = _extract_code_blocks(text)
    work = html.escape(work)
    work = _render_inline(work)

    lines = work.split("\n")
    out = []
    list_buffer = []
    list_type = None

    def flush_list():
        nonlocal list_buffer, list_type
        if list_buffer:
            tag = "ol" if list_type == "ol" else "ul"
            out.append(f"<{tag} style='margin:4px 0 4px 18px; padding:0;'>")
            out.extend(f"<li style='margin:2px 0;'>{_render_inline(item)}</li>" for item in list_buffer)
            out.append(f"</{tag}>")
            list_buffer = []
            list_type = None

    for raw in lines:
        line = raw
        hdr = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hdr:
            flush_list()
            out.append(f"<b style='font-size:13px; color:#f0f6ff;'>{_render_inline(hdr.group(2))}</b>")
            continue
        if re.match(r"^\s*(---+|\*\*\*+)\s*$", line):
            flush_list()
            out.append("<hr style='border:none; border-top:1px solid #1e2a3a; margin:6px 0;'/>")
            continue
        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if bullet or numbered:
            if list_type != ("ol" if numbered else "ul"):
                flush_list()
                list_type = "ol" if numbered else "ul"
            list_buffer.append((numbered.group(1) if numbered else bullet.group(1)).strip())
            continue
        flush_list()
        if line.strip():
            out.append(f"<span>{line}</span>")
        else:
            out.append("<br/>")

    flush_list()
    return _restore("<br/>".join(out), placeholders)