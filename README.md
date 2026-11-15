# MyFirstSandBox

Mon premier site web — une simple page Hello World en HTML/CSS.

## Lancer le site en local

Ouvre simplement `index.html` dans ton navigateur, ou lance un serveur local :

```bash
python3 -m http.server 8000
```

Puis va sur [http://localhost:8000](http://localhost:8000).

## Actualités quotidiennes par thème

La page propose un menu de 9 thèmes, par ordre alphabétique — 🎨 Art, 🚗 Auto, 🎭 Culture,
💻 High-tech, 🤖 IA, 🌍 Monde, 🌿 Nature, 🏥 Santé, ⚽ Sport — et affiche pour chacun les 3 faits marquants du
jour en français, avec une vignette image. **Chaque thème agrège 2 à 3 sources RSS** (ex. High-tech :
Numerama + 01net + Presse Citron) : les articles sont dédupliqués par titre normalisé et classés par
récence pour ne garder que les plus pertinents ; le nombre de sources actives est affiché sous le titre.

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

## Gestion dynamique des thèmes

Le bouton **⚙️** à la fin du menu des thèmes ouvre une modale de gestion :

- **masquer** un thème par défaut (🗑, restaurable via ↺ ou « Réafficher les thèmes par défaut ») ;
- **ajouter un thème personnalisé en un seul mot** (ex. « espace », « cinéma », « bitcoin ») :
  l’application génère automatiquement le flux Google News FR correspondant
  (`news.google.com/rss/search?q=<mot>`), enregistré dans le navigateur (`localStorage`), affiché
  par ordre alphabétique avec les autres, et chargé en direct côté client (via `rss2json`, proxy
  CORS en secours) ;
- **supprimer** un thème personnalisé (🗑).

Les thèmes personnalisés sont locaux à chaque navigateur. Pour un thème visible par tous les
visiteurs, ajoutez-le dans `THEMES` (scripts/update_news.py) : le workflow quotidien l'intégrera
à `news.json` automatiquement.

## Compte (Supabase — backend gratuit)

Le bouton **👤** dans la barre de l'horloge mène à `login.html` : connexion ou création de compte
(e-mail + pseudo + mot de passe) via **Supabase Auth**. Les personnalisations (thème choisi, thèmes
masqués, thèmes ajoutés en un mot) sont enregistrées dans la table `user_prefs` et **synchronisées
sur tous les appareils** du compte (cache local en `localStorage`, synchro serveur différée).

### Configuration

1. `supabase-config.js` : URL du projet + clé `anon` (publique, commitable sans risque) ;
2. Exécuter `supabase/schema.sql` dans l'éditeur SQL du projet (table `user_prefs` + RLS) ;
3. Déployer la Edge Function RSS (appelée côté serveur pour les thèmes personnalisés, donc plus de
   proxy CORS tiers en première intention) :
   ```bash
   supabase functions deploy rss --project-ref <ref-du-projet>
   ```
   (code dans `supabase/functions/rss/index.ts` ; repli client sur `rss2json` puis `allorigins`)

## Archives

Chaque jour, le workflow copie le contenu de `news.json` dans `archives.json` (30 derniers jours
conservés, clé = date UTC). Un bouton **🗄️ Archives** dans la barre de l'horloge ouvre une modale
qui permet de revoir les actualités d'un jour précédent, par thème.

## Publication

Le site est publié sur [https://degrysefranck-commits.github.io/MyFirstSandBox/](https://degrysefranck-commits.github.io/MyFirstSandBox/).
