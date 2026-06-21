/** Shared team context for collaboration capability components (localStorage + events). */
window.QATeamContext = (function () {
    const STORAGE_KEY = 'qa_active_team_id';

    function readTeamId() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            const n = parseInt(raw, 10);
            return Number.isFinite(n) ? n : null;
        } catch (_e) {
            return null;
        }
    }

    function writeTeamId(teamId) {
        try {
            if (teamId == null) {
                localStorage.removeItem(STORAGE_KEY);
            } else {
                localStorage.setItem(STORAGE_KEY, String(teamId));
            }
        } catch (_e) {
            /* ignore */
        }
        window.dispatchEvent(
            new CustomEvent('team-context-changed', { detail: { teamId: teamId } })
        );
    }

    function fetchTenantContext() {
        return fetch('/api/v1/user/tenant-context', { credentials: 'same-origin' })
            .then((r) => r.json())
            .then((res) => res.data || res);
    }

    return { STORAGE_KEY, readTeamId, writeTeamId, fetchTenantContext };
})();
