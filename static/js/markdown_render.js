(function (global) {
    "use strict";

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function inlineMarkdown(text) {
        var out = escapeHtml(text);
        out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
        out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        out = out.replace(/__([^_]+)__/g, "<strong>$1</strong>");
        out = out.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
        out = out.replace(/(^|[^_])_([^_\n]+)_/g, "$1<em>$2</em>");
        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_, label, url) {
            return '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">' + label + "</a>";
        });
        return out;
    }

    function flushParagraph(parts, html) {
        if (!parts.length) return;
        html.push("<p>" + inlineMarkdown(parts.join(" ")) + "</p>");
        parts.length = 0;
    }

    function renderMarkdown(markdown) {
        var source = String(markdown == null ? "" : markdown).replace(/\r\n?/g, "\n");
        if (!source.trim()) return "";

        var lines = source.split("\n");
        var html = [];
        var paragraph = [];
        var inCode = false;
        var codeLang = "";
        var codeLines = [];
        var listType = null;

        function closeList() {
            if (!listType) return;
            html.push("</" + listType + ">");
            listType = null;
        }

        function openList(type) {
            if (listType === type) return;
            closeList();
            flushParagraph(paragraph, html);
            html.push("<" + type + ">");
            listType = type;
        }

        function isTableSeparator(value) {
            return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(value || "");
        }

        function splitTableRow(value) {
            var text = String(value || "").trim();
            if (text.charAt(0) === "|") text = text.slice(1);
            if (text.charAt(text.length - 1) === "|") text = text.slice(0, -1);
            return text.split("|").map(function (cell) { return cell.trim(); });
        }

        for (var i = 0; i < lines.length; i += 1) {
            var raw = lines[i];
            var line = raw.trim();

            if (/^```/.test(line)) {
                if (inCode) {
                    html.push(
                        '<pre><code class="' +
                        escapeHtml(codeLang ? "language-" + codeLang : "") +
                        '">' +
                        escapeHtml(codeLines.join("\n")) +
                        "</code></pre>"
                    );
                    inCode = false;
                    codeLang = "";
                    codeLines = [];
                } else {
                    flushParagraph(paragraph, html);
                    closeList();
                    inCode = true;
                    codeLang = line.replace(/^```/, "").trim().split(/\s+/)[0] || "";
                }
                continue;
            }

            if (inCode) {
                codeLines.push(raw);
                continue;
            }

            if (!line) {
                flushParagraph(paragraph, html);
                closeList();
                continue;
            }

            if (line.indexOf("|") >= 0 && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
                flushParagraph(paragraph, html);
                closeList();
                var headers = splitTableRow(line);
                html.push('<div class="markdown-table-wrap"><table><thead><tr>');
                headers.forEach(function (cell) {
                    html.push("<th>" + inlineMarkdown(cell) + "</th>");
                });
                html.push("</tr></thead><tbody>");
                i += 2;
                while (i < lines.length && lines[i].trim() && lines[i].trim().indexOf("|") >= 0) {
                    html.push("<tr>");
                    splitTableRow(lines[i]).forEach(function (cell) {
                        html.push("<td>" + inlineMarkdown(cell) + "</td>");
                    });
                    html.push("</tr>");
                    i += 1;
                }
                i -= 1;
                html.push("</tbody></table></div>");
                continue;
            }

            var heading = /^(#{1,6})\s+(.+)$/.exec(line);
            if (heading) {
                flushParagraph(paragraph, html);
                closeList();
                var level = Math.min(6, heading[1].length);
                html.push("<h" + level + ">" + inlineMarkdown(heading[2]) + "</h" + level + ">");
                continue;
            }

            if (/^>\s?/.test(line)) {
                flushParagraph(paragraph, html);
                closeList();
                html.push("<blockquote>" + inlineMarkdown(line.replace(/^>\s?/, "")) + "</blockquote>");
                continue;
            }

            if (/^[-*_]{3,}$/.test(line)) {
                flushParagraph(paragraph, html);
                closeList();
                html.push("<hr>");
                continue;
            }

            var ordered = /^\d+[.)]\s+(.+)$/.exec(line);
            if (ordered) {
                openList("ol");
                html.push("<li>" + inlineMarkdown(ordered[1]) + "</li>");
                continue;
            }

            var unordered = /^[-*+]\s+(.+)$/.exec(line);
            if (unordered) {
                openList("ul");
                html.push("<li>" + inlineMarkdown(unordered[1]) + "</li>");
                continue;
            }

            closeList();
            paragraph.push(line);
        }

        if (inCode) {
            html.push("<pre><code>" + escapeHtml(codeLines.join("\n")) + "</code></pre>");
        }
        flushParagraph(paragraph, html);
        closeList();

        return html.join("");
    }

    global.qcEscapeHtml = global.qcEscapeHtml || escapeHtml;
    global.qcRenderMarkdown = renderMarkdown;
    global.qcSetMarkdown = function (target, markdown) {
        var el = typeof target === "string" ? document.querySelector(target) : target;
        if (!el) return;
        el.innerHTML = renderMarkdown(markdown);
        el.classList.add("markdown-body");
    };
})(window);
