(function () {
    const SESSION_KEY = "mfsb_session";
    const SESSION_PSEUDO_KEY = "mfsb_session_pseudo";
    const PREFS_CACHE_PREFIX = "mfsb_prefs_";
    const PLACEHOLDER_KEY = "VOTRE_CLE_ANON";

    function client() {
        const cfg = window.SUPABASE_CONFIG || {};
        if (!window.supabase || !cfg.url || !cfg.anonKey || cfg.anonKey === PLACEHOLDER_KEY) return null;
        if (!window.__sbClient) {
            window.__sbClient = window.supabase.createClient(cfg.url, cfg.anonKey);
        }
        return window.__sbClient;
    }

    function isConfigured() {
        return client() !== null;
    }

    function prefsCacheKey(uid) {
        return PREFS_CACHE_PREFIX + uid;
    }

    async function register(email, password, pseudo) {
        const sb = client();
        if (!sb) return { error: "Backend non configuré : clé anon Supabase manquante." };
        const { data, error } = await sb.auth.signUp({
            email: (email || "").trim(),
            password: password || "",
            options: { data: { pseudo: (pseudo || "").trim() } }
        });
        if (error) return { error: error.message };
        if (data.session && data.user) {
            sessionStorage.setItem(SESSION_KEY, data.user.id);
            sessionStorage.setItem(SESSION_PSEUDO_KEY, (data.user.user_metadata && data.user.user_metadata.pseudo) || "");
        }
        return { ok: true, user: data.user, needsConfirm: !data.session };
    }

    async function login(email, password) {
        const sb = client();
        if (!sb) return { error: "Backend non configuré : clé anon Supabase manquante." };
        const { data, error } = await sb.auth.signInWithPassword({
            email: (email || "").trim(),
            password: password || ""
        });
        if (error) return { error: error.message };
        sessionStorage.setItem(SESSION_KEY, data.user.id);
        sessionStorage.setItem(SESSION_PSEUDO_KEY, (data.user.user_metadata && data.user.user_metadata.pseudo) || "");
        await syncPrefsFromServer(data.user.id);
        return { ok: true, user: data.user };
    }

    function logout() {
        const sb = client();
        if (sb) sb.auth.signOut();
        sessionStorage.removeItem(SESSION_KEY);
        sessionStorage.removeItem(SESSION_PSEUDO_KEY);
    }

    function currentUser() {
        return sessionStorage.getItem(SESSION_KEY);
    }

    function currentPseudo() {
        return sessionStorage.getItem(SESSION_PSEUDO_KEY) || currentUser();
    }

    function loadPrefs(uid) {
        uid = uid || currentUser();
        if (!uid) return {};
        try { return JSON.parse(localStorage.getItem(prefsCacheKey(uid))) || {}; } catch (e) { return {}; }
    }

    let syncTimer = null;

    function savePrefs(uid, prefs) {
        uid = uid || currentUser();
        if (!uid) return;
        localStorage.setItem(prefsCacheKey(uid), JSON.stringify(prefs));
        clearTimeout(syncTimer);
        syncTimer = setTimeout(() => { pushPrefs(uid, prefs); }, 800);
    }

    async function pushPrefs(uid, prefs) {
        const sb = client();
        if (!sb) return;
        await sb.from("user_prefs").upsert(
            { user_id: uid, prefs: prefs, updated_at: new Date().toISOString() },
            { onConflict: "user_id" }
        );
    }

    async function syncPrefsFromServer(uid) {
        const sb = client();
        if (!sb || !uid) return;
        const { data } = await sb.from("user_prefs").select("prefs").eq("user_id", uid).maybeSingle();
        if (data && data.prefs) {
            localStorage.setItem(prefsCacheKey(uid), JSON.stringify(data.prefs));
        }
    }

    async function init() {
        const sb = client();
        if (!sb) return;
        try {
            const { data } = await sb.auth.getSession();
            if (data.session && data.session.user) {
                sessionStorage.setItem(SESSION_KEY, data.session.user.id);
                sessionStorage.setItem(SESSION_PSEUDO_KEY, (data.session.user.user_metadata && data.session.user.user_metadata.pseudo) || "");
                await syncPrefsFromServer(data.session.user.id);
            }
        } catch (e) {}
    }

    window.Auth = {
        isConfigured: isConfigured,
        register: register,
        login: login,
        logout: logout,
        currentUser: currentUser,
        currentPseudo: currentPseudo,
        loadPrefs: loadPrefs,
        savePrefs: savePrefs,
        init: init
    };
})();
