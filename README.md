# MyFirstSandBox

Mon premier site web — une simple page Hello World en HTML/CSS.

## Lancer le site en local

Ouvre simplement `index.html` dans ton navigateur, ou lance un serveur local :

```bash
python3 -m http.server 8000
```

Puis va sur [http://localhost:8000](http://localhost:8000).

## Actualités quotidiennes par thème

La page propose un menu de 7 thèmes — 🌍 Monde, 🎨 Art, 🎭 Culture, 💻 High-tech,
🌿 Nature, 🏥 Santé, ⚽ Sport — et affiche pour chacun les 3 faits marquants du
jour en français, avec une vignette image (flux RSS France 24, Beaux Arts,
Le Monde, Futura Sciences, Sciences et Avenir).

Un workflow GitHub Actions (`.github/workflows/update-news.yml`) tourne chaque
jour à 6h00 UTC : il régénère `news.json` via `scripts/update_news.py` (un flux
RSS par thème, anciennes données conservées si un flux est indisponible) et
commit le résultat sur `main`, ce qui redéploie automatiquement le site via
GitHub Pages. Le choix du thème est mémorisé dans le navigateur.

Pour mettre à jour manuellement : `python3 scripts/update_news.py`.

## Tendances de recherche

En bas de page, un nuage de mots affiche les tendances **françaises** de la
veille, consolidées sur 6 sources : Google Trends FR (recherches), Google News
FR, France 24, France Info, Le Monde (à la une) et le top des consultations
Wikipédia FR. `trends.json` est régénéré chaque jour par le même workflow.

Le site est publié sur [https://degrysefranck-commits.github.io/MyFirstSandBox/](https://degrysefranck-commits.github.io/MyFirstSandBox/).

## Espace sécurisé (OAuth 2.0)

Un lien **Espace sécurisé** dans l'en-tête mène à `secure.html`, une page protégée par une
authentification OAuth 2.0. Comme le site est 100 % statique (GitHub Pages, aucun serveur),
l'authentification utilise le flux **Authorization Code + PKCE** (RFC 7636), conçu pour les
clients publics : aucun secret côté client n'est requis ni exposé. Le jeton d'accès est stocké
dans `sessionStorage` (effacé à la fermeture de l'onglet) et un paramètre `state` protège le
retour d'autorisation contre les attaques CSRF.

### Configuration

Renseigner `oauth-config.js` avec les valeurs de votre fournisseur d'identité :

- `clientId` : identifiant client (public) enregistré chez le fournisseur ;
- `authorizationEndpoint`, `tokenEndpoint`, `userinfoEndpoint` : endpoints du fournisseur ;
- `redirectUri` : laisser vide pour utiliser automatiquement l'URL absolue de `secure.html`,
  sinon la fixer explicitement (à enregistrer aussi comme redirect URI chez le fournisseur,
  ex. `https://degrysefranck-commits.github.io/MyFirstSandBox/secure.html`) ;
- `scopes` : ex. `openid profile email`.

Le fournisseur doit accepter le flux Authorization Code + PKCE depuis le navigateur, ce qui
implique que son endpoint de token autorise les requêtes CORS (c'est le cas d'Auth0, Okta,
Keycloak, Azure AD, etc.). **GitHub OAuth Apps n'est pas utilisable ici** : il exige un
`client_secret`, qu'aucun site purement statique ne peut garder confidentiel.

### Limite importante

Le contrôle d'accès est effectué côté client : tout le contenu publié dans ce dépôt reste public.
Pour protéger de vraies données sensibles, il faudrait un backend (API + vérification du jeton
côté serveur).
