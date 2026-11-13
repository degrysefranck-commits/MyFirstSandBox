(function () {
    const config = window.OAUTH_CONFIG || {};
    const TOKEN_KEY = "oauth_access_token";
    const EXPIRES_KEY = "oauth_expires_at";
    const STATE_KEY = "oauth_state";
    const VERIFIER_KEY = "oauth_code_verifier";

    function base64UrlEncode(buffer) {
        const bytes = new Uint8Array(buffer);
        let str = "";
        bytes.forEach((b) => { str += String.fromCharCode(b); });
        return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    }

    function randomBytes(length) {
        const bytes = new Uint8Array(length);
        crypto.getRandomValues(bytes);
        return bytes;
    }

    async function createPkce() {
        const verifier = base64UrlEncode(randomBytes(32));
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
        return { verifier: verifier, challenge: base64UrlEncode(digest) };
    }

    function redirectUri() {
        if (config.redirectUri) return config.redirectUri;
        return new URL("secure.html", window.location.href).href;
    }

    function isConfigured() {
        return Boolean(config.clientId) &&
            config.clientId !== "VOTRE_CLIENT_ID" &&
            Boolean(config.authorizationEndpoint) &&
            Boolean(config.tokenEndpoint);
    }

    async function login() {
        const pkce = await createPkce();
        const state = base64UrlEncode(randomBytes(16));
        sessionStorage.setItem(VERIFIER_KEY, pkce.verifier);
        sessionStorage.setItem(STATE_KEY, state);
        const params = new URLSearchParams({
            response_type: "code",
            client_id: config.clientId,
            redirect_uri: redirectUri(),
            scope: config.scopes || "openid profile",
            state: state,
            code_challenge: pkce.challenge,
            code_challenge_method: "S256"
        });
        window.location.href = config.authorizationEndpoint + "?" + params.toString();
    }

    function getAccessToken() {
        const token = sessionStorage.getItem(TOKEN_KEY);
        const expiresAt = Number(sessionStorage.getItem(EXPIRES_KEY) || 0);
        if (!token || !expiresAt || Date.now() >= expiresAt - 30000) return null;
        return token;
    }

    async function handleCallback() {
        const params = new URLSearchParams(window.location.search);
        const error = params.get("error");
        if (error) {
            sessionStorage.removeItem(STATE_KEY);
            sessionStorage.removeItem(VERIFIER_KEY);
            return { error: params.get("error_description") || error };
        }
        const code = params.get("code");
        if (!code) return null;
        const state = params.get("state");
        const savedState = sessionStorage.getItem(STATE_KEY);
        const verifier = sessionStorage.getItem(VERIFIER_KEY);
        sessionStorage.removeItem(STATE_KEY);
        sessionStorage.removeItem(VERIFIER_KEY);
        if (!savedState || !verifier || state !== savedState) {
            return { error: "état OAuth invalide, veuillez réessayer" };
        }
        const body = new URLSearchParams({
            grant_type: "authorization_code",
            client_id: config.clientId,
            code: code,
            redirect_uri: redirectUri(),
            code_verifier: verifier
        });
        const response = await fetch(config.tokenEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json" },
            body: body.toString()
        });
        if (!response.ok) {
            return { error: "échec de l'échange du code contre un jeton" };
        }
        const data = await response.json();
        if (!data.access_token) return { error: "réponse du fournisseur invalide" };
        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        sessionStorage.setItem(EXPIRES_KEY, String(Date.now() + (data.expires_in || 3600) * 1000));
        const cleanUrl = new URL(window.location.href);
        cleanUrl.search = "";
        window.history.replaceState({}, document.title, cleanUrl.href);
        return { token: data.access_token };
    }

    function logout() {
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(EXPIRES_KEY);
        sessionStorage.removeItem(STATE_KEY);
        sessionStorage.removeItem(VERIFIER_KEY);
    }

    async function fetchProfile(token) {
        if (!config.userinfoEndpoint) return null;
        try {
            const response = await fetch(config.userinfoEndpoint, {
                headers: { "Authorization": "Bearer " + token, "Accept": "application/json" }
            });
            if (!response.ok) return null;
            return await response.json();
        } catch (e) {
            return null;
        }
    }

    window.Auth = {
        isConfigured: isConfigured,
        login: login,
        getAccessToken: getAccessToken,
        handleCallback: handleCallback,
        logout: logout,
        fetchProfile: fetchProfile
    };
})();
