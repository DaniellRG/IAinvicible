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


def split_blocks(text: str):
    """Divide el texto en bloques: ("text", contenido) o ("code", lang, contenido).

    Los bloques de codigo van aparte del texto de explicacion.
    Un par de ``` sin cerrar (respuesta en streaming) se convierte en
    un bloque de codigo incompleto, en lugar de texto literal.
    """
    if not text:
        return []
    out = []
    pos = 0
    for m in re.finditer(r"```(\w*)\s*\n(.*?)```", text, flags=re.S):
        if m.start() > pos:
            _append_text(out, text[pos:m.start()])
        lang = (m.group(1) or "").strip()
        code = m.group(2)
        if not out or out[-1][0] != "code" or out[-1][1] != lang:
            out.append(("code", lang, code))
        else:
            out[-1] = ("code", lang, out[-1][2] + "\n" + code)
        pos = m.end()
    tail = text[pos:]
    if tail.strip():
        openm = re.search(r"([\s\S]*?)```(\w*)\s*\n([\s\S]*)\Z", tail)
        if openm:
            _append_text(out, openm.group(1))
            out.append(("code", (openm.group(2) or "").strip(), openm.group(3)))
        else:
            _append_text(out, tail)
    return out


def _append_text(out, seg):
    seg = seg.strip("\n")
    if not seg.strip():
        return
    if out and out[-1][0] == "text":
        out[-1] = ("text", out[-1][1] + seg)
    else:
        out.append(("text", seg))


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
    fragments = []
    list_buffer = []
    list_type = None
    para_buffer = []
    BLANK = "\x00BLANK\x00"
    BR1 = "\x00BR1\x00"
    BR2 = "\x00BR2\x00"

    def flush_list():
        nonlocal list_type
        if list_buffer:
            tag = "ol" if list_type == "ol" else "ul"
            items_html = "".join(
                f"<li style='margin:1px 0;'>{item}</li>" for item in list_buffer
            )
            fragments.append(
                f"<{tag} style='margin:3px 0 2px 16px; padding:0; line-height:1.4;'>"
                f"{items_html}</{tag}>"
            )
            list_buffer.clear()
            list_type = None

    def flush_para():
        if para_buffer:
            fragments.append(f"<span>{'<br/>'.join(para_buffer)}</span>")
            para_buffer.clear()

    for raw in lines:
        line = raw.strip() or "&nbsp;"

        if line == "&nbsp;":
            flush_para()
            flush_list()
            fragments.append(BLANK)
            continue

        hdr = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hdr:
            flush_para()
            flush_list()
            fragments.append(
                f"<b style='font-size:13px; color:#f0f6ff; margin:5px 0 1px 0;'>"
                f"{_render_inline(hdr.group(2))}</b>"
            )
            continue

        if re.match(r"^&nbsp;?\s*(-{3,}|\*{3,})\s*$", line):
            flush_para()
            flush_list()
            fragments.append(
                "<hr style='border:none; border-top:1px solid #1e2a3a; "
                "margin:4px 0;'/>"
            )
            continue

        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if bullet or numbered:
            flush_para()
            if list_type != ("ol" if numbered else "ul"):
                flush_list()
                list_type = "ol" if numbered else "ul"
            list_buffer.append(
                _render_inline((numbered.group(1) if numbered else bullet.group(1)).strip())
            )
            continue

        flush_list()
        para_buffer.append(line)

    flush_para()
    flush_list()

    parts = []
    for frag in fragments:
        if frag == BLANK:
            if parts and parts[-1] not in (BR1, BR2):
                parts.append(BR2)
        else:
            if parts and parts[-1] in (BR1, BR2):
                parts.append(frag)
            else:
                if parts:
                    parts.append(BR1)
                parts.append(frag)

    result = "".join(p.replace(BR1, "<br/>").replace(BR2, "<br/><br/>") for p in parts)
    return _restore(result, placeholders)