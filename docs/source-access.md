# Доступ к источникам: Reddit и TikTok

> **Дата проверки:** 30.10.2026. Вопрос: можно ли собрать поисковые запросы и тренды Reddit и TikTok за последние 7 дней.
>
> Это результат проверки доступа, а не реализованная интеграция. Пометки уровня доказательности:
> - `observed fact` — проверено живым запросом 30.10.2026;
> - `documented` — прочитано в официальной документации или официальном посте платформы;
> - `press report` — сообщения прессы, первоисточник не прочитан;
> - `provider claim` — заявление стороннего поставщика, не проверено.

## Короткий вывод

- Данные за 7 дней собрать можно, но **поисковых запросов с объёмами за 7 дней официально нет ни у одного источника**.
- **Reddit** не раскрывает, что ищут пользователи. Можно собирать посты и комментарии, которые соответствуют нашему запросу или теме, но публичный доступ к данным Reddit в 2026–2027 годах закрывается.
- **TikTok** официально отдаёт поисковые запросы без чисел (только «сейчас»), объёмы поиска — помесячно, а хештеги — с окном 7 дней. Объёмы поиска ровно за 7 дней заявляет только неофициальный поставщик TokConnect.

## Reddit

### Сроки закрытия публичного API (`documented`)

Из официального поста в r/redditdev от 30.09.2026 (u/boat-botany, «Moving Data API Apps to the Developer Platform: migration dates and next steps»):

| Дата | Что происходит |
| --- | --- |
| 31.10.2026 | Новые заявки на доступ к публичному API больше не принимаются |
| 30.11.2026 | Закрывается регистрация в программе миграции |
| 12.01.2027 | Начинается отключение приложений, которые не зарегистрировались и не ответили Reddit |
| Март 2027 | Публичный API закрывается для всех оставшихся приложений и пользователей |

Дополнительно:
- Самостоятельное получение OAuth-доступа закрыто с ноября 2025 года. Новые приложения одобряются вручную по Responsible Builder Policy. Коммерческое использование данных требует письменного разрешения (`press report` по сторонним обзорам; текст политики не перечитывался).
- Сторонним приложениям предлагают переходить на Developer Platform (Devvit). Он рассчитан на приложения внутри Reddit; подходит ли он для выгрузки данных во внешнее исследование, не проверялось.

### Варианты получения данных

| Путь | Окно 7 дней | Статус и ограничения |
| --- | --- | --- |
| Официальный OAuth Data API | Да: `t=week` и фильтр по `created_utc` | Работает только при уже одобренном приложении и только до марта 2027. Лимит около 100 запросов в минуту на client ID (`press report`) |
| Публичный `*.json` без авторизации | — | `observed fact`: `www.reddit.com/search.json` и `/r/<sub>/new.json` возвращают 403; `old.reddit.com/search.json` перенаправляет на логин |
| RSS (`/search.rss`) | Частично | `observed fact`: отвечает 200, но после одного запроса `x-ratelimit-remaining: 0`, не больше 100 записей, нет score и числа комментариев. По запросу `horoscope` с `sort=new` 97 записей покрыли примерно 10 часов. По сообщениям прессы RSS отключают 13.11.2026 (`press report`) |
| Arctic Shift (`arctic-shift.photon-reddit.com/api/posts/search`) | Да, любой диапазон через `after`/`before` | `observed fact`: `subreddit=astrology`, 23–30.10.2026 вернул 100 постов (24.10–29.10). Параметр `query` без `subreddit` или `author` возвращает ошибку 400, поиска по всему Reddit нет. `score`/`num_comments` — снимок на момент архивации (в выборке 1 и 0). Сторонний проект, условия использования не проверены, вероятно зависит от API Reddit |
| Reddit Pro Trends | — | Объём обсуждений по ключевому слову примерно за 3 месяца, только в интерфейсе, API не найден (`press report`). Возможен только ручной импорт |
| Платные скрейперы (Apify и подобные) | — | Не рассматриваются: обходят правила платформы, что запрещено в `AGENTS.md` |

## TikTok

### Официальный TikTok API for Business v1.3 (`documented`)

| Эндпоинт | Что возвращает | Окно и фильтры |
| --- | --- | --- |
| `GET /open_api/v1.3/discovery/trending/search/` | `search_keywords`: 20 строк трендовых запросов, без чисел | Только текущий снимок; нет региона, категории и дат. Есть `is_personalized` |
| `GET /open_api/v1.3/discovery/trending/search/keyword/?query=` | 20 рекомендованных запросов для темы, без чисел | Только текущий снимок; `query` до 255 символов |
| `GET /open_api/v1.3/tool/search_keyword/keyword_idea/` (Search Ads) | `avg_monthly_searches_lower/upper`, `three_month_change`, `year_over_year_change`, `competition`, `estimated_cpc_lower/upper`, `total_search_volume_lower/upper` | **Месяц**, не 7 дней. До 10 исходных ключевых слов, только английский; `country_codes` по умолчанию `US`, другие страны — по allowlist |
| `GET /open_api/v1.3/discovery/trending_list/` (хештеги) | Топ-200: `rank_position`, `rank_change`, `views`, `posts` за окно, `top_country_list`, `trending_history` по дням (`rank_position_daily`, `views_daily`) до 30 дней | `date_range`: `1DAY`, `7DAY`, `30DAY`, `120DAY`; `country_code`; `category_name` (например, `PRODUCTIVITY_AND_EFFICIENCY`). `views_daily` = `null`, если меньше 1000 просмотров в день |

Требования к доступу:
- Для двух эндпоинтов `discovery/trending/search*` нужны токен TikTok-аккаунта со scope `discovery.search.words` и аккаунт с Advanced Access или Verified Business Account (проверяется через `/business/get/`, поле `has_advanced_access`).
- Для `keyword_idea` и `trending_list` нужен `advertiser_id`, то есть рекламный аккаунт.
- По справке TikTok, Advanced Access выдаётся при привязке аккаунта к TikTok for Business или к неверифицированному Business Center.
- Нужно одобренное developer-приложение в TikTok API for Business. Конкретные требования ревью для Discovery API не найдены.

Официальный **TikTok for Business MCP Server** содержит около 400 инструментов, в том числе `tool_search_keyword_idea_get`. Инструментов Discovery в его списке не найдено.

### Что не подходит

- **Research API** (`documented`): только академические институты и некоммерческие организации, независимые от коммерческих интересов. Окно запроса видео — не больше 30 дней (`end_date` не позже чем через 30 дней после `start_date`).
- **Creator Search Insights**: показывает популярные поисковые темы и content gaps, но только в приложении; публичного API не найдено.
- **Creative Center**: переехал в TikTok One Creative Suite. Без логина показывает только топ-3 хештега (`observed fact`); это сигнал о контенте, а не о поиске.

### TokConnect (`provider claim`)

- Заявляет доступ к данным Creator Search Insights: `searchVolume` (поиски за последние 7 дней, по миру), `trend7d` (7 дневных значений), `popularity` (индекс 0–100), `videoCount`, категории.
- Сам указывает, что не связан с TikTok и не одобрен им; способ получения данных не раскрыт.
- Результаты смешивают реальные запросы с тематическими группами, которые TikTok формирует сам; их нужно разделять (`typed_search` и `topic_group`).
- Есть бесплатный тариф, платные — от $34.99 в месяц при оплате за год; доступ через MCP `https://mcp.tokconnect.com/mcp`.
- Перед использованием нужна проверка по требованиям `AGENTS.md`: живой тест на 5–10 запросах, сверка с CSI в приложении, единицы измерения, свежесть, условия хранения.

## Что это значит для скилла

- **«7 дней» значит своё для каждого типа сигнала.** В отчёте нужна таблица покрытия по сигналам, например: посты Reddit — 7 дней; хештеги TikTok — 7 дней; поисковые объёмы TikTok — последний месяц; трендовые запросы TikTok — снимок на момент сбора.
- **Произвольное окно, например 14 дней:**
  - Arctic Shift покрывает любой диапазон.
  - У хештегов TikTok нет значения `14DAY`; 14 дней можно собрать из `trending_history`, но только для хештегов из топ-200 и с пропусками там, где `views_daily` = `null`.
  - Поисковые объёмы TikTok остаются месячными; это нужно явно указать в отчёте.
- **Тематика (например, «гороскопы»):**
  - Reddit: подборка сабреддитов по теме плюс запрос (Arctic Shift не ищет по всему Reddit).
  - TikTok: `category_name` для хештегов, `query` для рекомендованных запросов, исходные ключевые слова для `keyword_idea`.
- **Названия сигналов:** официальные данные TikTok без чисел называть `keyword_recommendations`, хештеги — `content_trends`, месячные объёмы — `search_volume_range`, а не `search_volume_trends` за 7 дней.

### Рекомендуемый набор для первой версии

- Reddit: официальный API, если есть одобренное приложение, плюс Arctic Shift по подобранным сабреддитам со статусом качества данных стороннего источника.
- TikTok: официальные хештеги за 7 дней, рекомендованные запросы и `keyword_idea`.
- TokConnect — необязательный источник со статусом `provider_claim_unverified`.

## Открытые вопросы

1. Есть ли у пользователя одобренное Reddit OAuth-приложение? Новые заявки принимаются только до 31.10.2026, а доступ в любом случае закроется в марте 2027.
2. Есть ли доступ к TikTok for Business, рекламному аккаунту и developer-приложению (у пользователя или у партнёров Wowmaking)?
3. Тестировать ли TokConnect на бесплатном тарифе?
4. Какие условия использования у Arctic Shift и как долго он проработает после закрытия API Reddit?

## Источники

- [r/redditdev: Moving Data API Apps to the Developer Platform](https://www.reddit.com/r/redditdev/comments/1wubcvf/moving_data_api_apps_to_the_developer_platform/) — прочитан через RSS 30.10.2026
- [Social Media Today: Reddit ends support for RSS feeds](https://www.socialmediatoday.com/news/reddit-ends-support-for-rss-feeds/831844/)
- [heise: Reddit to shut down RSS feeds and public API](https://www.heise.de/en/news/Reddit-to-shut-down-RSS-feeds-and-public-API-11473400.html)
- [redditapis: Reddit's Data API Migration to the Developer Platform (2026)](https://www.redditapis.com/blogs/reddit-developer-platform-migration-2026) — сторонний обзор
- [Practical Ecommerce: SEO wins from Reddit Pro](https://www.practicalecommerce.com/seo-wins-from-reddit-pro)
- [TikTok: Get trending search keywords](https://business-api.tiktok.com/portal/docs/get-trending-search-keywords/v1.3)
- [TikTok: Get recommended search keywords](https://business-api.tiktok.com/portal/docs/get-recommended-search-keywords/v1.3)
- [TikTok: Discover new keywords](https://business-api.tiktok.com/portal/docs/discover-new-keywords/v1.3)
- [TikTok: Get popular hashtags](https://business-api.tiktok.com/portal/docs/get-popular-hashtags/v1.3)
- [TikTok: Available tools in TikTok for Business MCP Server](https://business-api.tiktok.com/portal/docs/available-tools-in-tiktok-for-business-mcp-server/v1.3)
- [TikTok: About TikTok account entitlements](https://ads.tiktok.com/help/article/about-tiktok-account-entitlements)
- [TikTok: Research API](https://developers.tiktok.com/products/research-api/)
- [TikTok: Research API — Query Videos](https://developers.tiktok.com/doc/research-api-specs-query-videos)
- [TokConnect: Creator Search Insights API](https://tokconnect.com/guides/creator-search-insights-api/)
