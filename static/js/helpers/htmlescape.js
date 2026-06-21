/**
 * htmlescape.js — shared HTML escaping utility
 *
 * Provides window.escHtml(s) to safely escape user-supplied strings
 * before inserting into innerHTML. Prevents XSS via character entity encoding.
 */
window.escHtml = (function() {
    var map = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;'};
    return function(s) { return String(s).replace(/[&<>"']/g, function(c) { return map[c] || c; }); };
})();