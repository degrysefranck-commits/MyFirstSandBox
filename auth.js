(function () {
    const ACCOUNTS_KEY = "mfsb_accounts";
    const SESSION_KEY = "mfsb_session";

    function loadAccounts() {
        try { return JSON.parse(localStorage.getItem(ACCOUNTS_KEY)) || {}; } catch (e) { return {}; }
    }

    function saveAccounts(accounts) {
        localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
    }

    function toHex(buffer) {
        return Array.from(new Uint8Array(buffer)).map((b) => b.toString(16).padStart(2, "0")).join("");
    }

    function randomSalt() {
        const bytes = new Uint8Array(16);
        crypto.getRandomValues(bytes);
        return toHex(bytes);
    }

    async function hashPassword(password, salt) {
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(salt + ":" + password));
        return toHex(digest);
    }

    function validUsername(u) {
        return /^[a-zA-Z0-9_-]{3,20}$/.test(u);
    }

    async function register(username, password) {
        username = (username || "").trim();
        if (!validUsername(username)) {
            return { error: "Identifiant invalide (3-20 caractères : lettres, chiffres, tiret ou _)." };
        }
        if (!password || password.length < 6) {
            return { error: "Mot de passe trop court (6 caractères minimum)." };
        }
        const accounts = loadAccounts();
        const key = username.toLowerCase();
        if (accounts[key]) return { error: "Ce compte existe déjà." };
        const salt = randomSalt();
        const hash = await hashPassword(password, salt);
        accounts[key] = {
            username: username,
            salt: salt,
            hash: hash,
            created_at: new Date().toISOString(),
            prefs: {}
        };
        saveAccounts(accounts);
        sessionStorage.setItem(SESSION_KEY, key);
        return { ok: true };
    }

    async function login(username, password) {
        const key = (username || "").trim().toLowerCase();
        const accounts = loadAccounts();
        const acc = accounts[key];
        if (!acc) return { error: "Compte inconnu." };
        const hash = await hashPassword(password || "", acc.salt);
        if (hash !== acc.hash) return { error: "Mot de passe incorrect." };
        sessionStorage.setItem(SESSION_KEY, key);
        return { ok: true };
    }

    function logout() {
        sessionStorage.removeItem(SESSION_KEY);
    }

    function currentUser() {
        return sessionStorage.getItem(SESSION_KEY);
    }

    function loadPrefs(username) {
        const accounts = loadAccounts();
        const acc = accounts[(username || "").toLowerCase()];
        return acc && acc.prefs ? acc.prefs : {};
    }

    function savePrefs(username, prefs) {
        const accounts = loadAccounts();
        const key = (username || "").toLowerCase();
        if (accounts[key]) {
            accounts[key].prefs = prefs;
            saveAccounts(accounts);
        }
    }

    window.Auth = {
        register: register,
        login: login,
        logout: logout,
        currentUser: currentUser,
        loadPrefs: loadPrefs,
        savePrefs: savePrefs
    };
})();
