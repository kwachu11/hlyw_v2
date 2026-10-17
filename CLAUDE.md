# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

hlyw.pl — a Polish-language Flask community site for a group of friends: news with reactions, photo albums, event calendar (incl. FIFA tournaments), browser mini-games with rankings, Hall of Fame, quiz, reports, chat, Twitch/camera page. All UI text, comments, flash messages and commit messages are in Polish — keep it that way.

## Running

```bash
venv\Scripts\activate            # Windows venv lives in ./venv
pip install -r requirements.txt  # note: file is UTF-16 encoded
python run.py                    # dev server on 0.0.0.0:5000, debug on
```

Production runs under gunicorn (127.0.0.1:8000) behind nginx (`hlyw` file = nginx config, git-ignored). There are no tests, linter or build step.

A `.env` file is **required** — `_load_env()` in `app/__init__.py` looks for `.env` / `.env.bak` in `app/` and the project root and raises if `SECRET_KEY` is missing. Other vars: `DATABASE_URI` (default `sqlite:///<root>/baza.db`; the local `app/.env` points it at **`instance/baza.db`** — that is the live dev DB, the root `baza.db` is an old copy), `SECURITY_PASSWORD_SALT`, `MAIL_*`, `LOGIN_MESSAGE*`, `SPOTIPY_*`. `config.py` is mostly vestigial (only applied in `run.py` after app creation).

## Architecture

Practically the whole app is the single `create_app()` factory in `app/__init__.py` (~1800 lines): config, `db = SQLAlchemy()`, **all models defined as local classes inside the function**, `db.create_all()`, template filters, and every `@app.route`. There are no blueprints and no migrations framework.
- Models are not importable at module level. Standalone scripts get them via `create_app()` + the SQLAlchemy registry (see `hash_passwords.py`: `next(m.class_ for m in db.Model.registry.mappers if ...)`).
- `app/views.py` is dead legacy code (imports a non-existent `app.models`) — don't edit/extend it.
- `app/forms.py` holds the Flask-WTF forms.
- Schema changes: `db.create_all()` only creates missing tables; it never alters existing ones. New columns on existing tables go in the idempotent `ALTER TABLE` list right after `create_all` (SQLite only; runs at startup, so a deploy needs no manual SQL). `create_all` is retried because several gunicorn workers start concurrently.
- One-off data scripts live in the root (`add_upgrades.py/.sql`, `add_news_gry.sql`, `hash_passwords.py`) and are written to be idempotent (skip rows that already exist). Follow that pattern for new data migrations.

Conventions worth knowing:
- `User.is_admin` is a **string** (`"0"` / non-`"0"`); admin checks are `current_user.is_admin == "0"`.
- Game score tables (`Snake`, `Tetris`, `Dino`, `IceTower`, `KolkoKrzyzyk`, `Formula`) share the shape `points / created_at / created_by`, where `created_by` is a **string** user id (compare with `str(current_user.id)`).
- Each game = `/<game>` page + `/<game>/save_score` JSON POST (`{score, run}` → `{ok, best}`) + `/ranking_<game>`; templates `<game>.html` and `ranking_<game>.html` (using shared `_ranking_table.html`). Rankings go through `game_ranking()` / `render_edition_ranking()`. A new game must be registered in two places: `game_catalog()` (feeds `/profil/<id>` and `/hall_of_fame`, incl. the 10→1 point overall ranking) and the hand-built list in the `/games` route. Icon is expected at `static/images/<slug>.svg`. (The `Statki` game was removed on purpose — don't bring it back.)
- Anti-cheat: every save needs a one-time `GameRun` ticket. The game calls `hlRun.start('<slug>')` (`static/js/game_run.js`) when a round starts and sends the score with `hlRun.send(SAVE_URL, score)`; the route calls `check_game_run()`, which rejects missing/reused tickets and scores above `GAME_SCORE_LIMITS[slug]` (base + points/second × elapsed). A new game needs an entry there too.
- GTA theme: `static/css/gta.css` (loaded after `custom.css`) overrides Bootstrap into a dark theme; Pricedown (`static/css/fonts/pricedown.otf`) for headings/UI, Barlow for body text — long text in Pricedown is unreadable, keep it to short labels. `static/js/gta.js`: `gta.passed()` / `gta.wasted()` banners (games call them on game over), cash counter refresh, SMS-style notifications (`/api/powiadomienia`, polled every 45 s), WebAudio sounds with a footer toggle. 404/500 render `error.html` ("wasted").
- `standings()` (cached 60 s per worker) = Hall of Fame overall ranking → `crown(user_id)` template global (👑 for TOP 3) and cash (`CASH_PER_HOF_POINT`, `CASH_PER_GAME`, shown in the menu via `inject_cash`). `wanted_stars(user_id)` = 1–5 stars from last-7-days activity (`WANTED_*` constants).
- Activity feed: `recent_activity(since, limit, kinds, exclude_user_id)` merges games (grouped per user+game), news, events, chat, photos, reports/comments, Trackmania times, new users and upgrades (grouped per day). Used by the home card „Co się dzieje” (`_activity.html`, refreshed every 60 s from `/aktywnosc/lista`), the `/aktywnosc` page and the SMS notifications (`NOTIFY_KINDS`).
- Trackmania tournament: events with "trackmania" in the title get `_trackmania.html` (models `TmTrack` / `TmTime`, F1-style `TM_POINTS`); event owner or admin manages tracks, participants enter their own times.
- Login accepts username or e-mail; one e-mail may own several accounts, so e-mail login picks the account whose password matches.
- `static/js/upload_resize.js` shrinks images client-side to ≤900 KB before upload (nginx default limit is 1 MB → 413).
- Editions: Snake/Tetris/Dino rankings split by `CURRENT_EDITION_START` / `PREVIOUS_EDITION_END` constants at the top of `app/__init__.py`.
- Datetimes are stored as UTC (`datetime.utcnow`); display via the `when` filter / `to_local()`.
- Passwords are hashed with werkzeug `pbkdf2:sha256` (`hash_password`, `is_password_hash`); email confirmation / password reset use `itsdangerous` tokens.
- Uploads go through `save_upload()` into `app/static/images/<folder>/` with random names; paths stored in DB may contain Windows backslashes — render them with the `media_url` filter.
- Quiz (`/quiz`, admin panel `/quiz/admin`): models `Quiz` / `QuizItem` / `QuizResponse`; players poll `/quiz/state` every 2 s. Old `quiz_question` / `quiz_answer` / `quiz_participant` tables are unused leftovers.
- FIFA tournament (events with "fifa" in the title): 2 groups → `sync_knockout()` fills semis (A1–B2, B1–A2), final and 3rd-place match automatically after each saved score; knockout matches can't end in a draw.
- "Ostatnie Ulepszenia" (`Upgrade` model) is the user-facing changelog; a menu badge appears for entries newer than `UPGRADE_NEW_DAYS`.
- Templates extend `base.html` (Bootstrap 4.5 + jQuery from CDN, `static/css/custom.css`); games are self-contained HTML/JS in their templates.

Git-ignored but present locally: `baza.db`, `instance/`, `.env`, user uploads (`static/images/newsy/`, `profile_pics/`). Don't commit databases.
