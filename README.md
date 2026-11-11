# MyFirstSandBox

Mon premier site web — une simple page Hello World en HTML/CSS.

## Lancer le site en local

Ouvre simplement `index.html` dans ton navigateur, ou lance un serveur local :

```bash
python3 -m http.server 8000
```

Puis va sur [http://localhost:8000](http://localhost:8000).

## Actualités mondiales quotidiennes

La page affiche les 3 infos mondiales du jour (flux RSS BBC World News).
Un workflow GitHub Actions (`.github/workflows/update-news.yml`) tourne chaque
jour à 6h00 UTC : il régénère `news.json` via `scripts/update_news.py` et commit
le résultat sur `main`, ce qui redéploie automatiquement le site via GitHub Pages.

Pour mettre à jour manuellement : `python3 scripts/update_news.py`.

Le site est publié sur [https://degrysefranck-commits.github.io/MyFirstSandBox/](https://degrysefranck-commits.github.io/MyFirstSandBox/).
