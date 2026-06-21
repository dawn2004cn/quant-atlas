/**
 * Sanitized Markdown → HTML for AI-rendered content (XSS hardening).
 * Requires marked + DOMPurify loaded before this script.
 */
(function (global) {
    function renderMarkdownSafe(markdown, fallbackHtml) {
        var source = markdown != null && String(markdown).length ? String(markdown) : (fallbackHtml || "");
        if (typeof global.marked === "undefined") {
            return source;
        }
        var parsed = global.marked.parse(source);
        if (typeof global.DOMPurify !== "undefined") {
            return global.DOMPurify.sanitize(parsed);
        }
        return parsed;
    }
    global.renderMarkdownSafe = renderMarkdownSafe;
})(window);
