# Undercut: plan

Publiczny serwis dla fanów F1 na prawdziwych danych od 1950 r. Flagowy projekt do CV, niekomercyjny.
Źródło wymagań: pakiet dokumentów `00`–`07` (docx). Ten plan nadpisuje je tam, gdzie się różnią.

## Decyzje

| # | Obszar | Decyzja |
|---|---|---|
| 1 | Architektura | Modularny monolit, event-driven |
| 2 | Zdarzenia | Transactional outbox w Postgresie (model Django `OutboxEvent`) |
| 3 | Worker | Własna pętla `manage.py run_outbox_worker` (`SKIP LOCKED`), bez Celery |
| 4 | Harmonogram | Własny scheduler, który publikuje zdarzenia do outboxa |
| 5 | Moduły | `catalog`, `ingestion`, `standings`, `analytics`, `accounts`, `predictions`, `notifications`, `events`. Moduły nie importują swoich modeli nawzajem (`import-linter` w CI) |
| 6 | Zdarzenia | Cienkie (identyfikatory + wersja), handlery idempotentne, dostarczenie „co najmniej raz”, kolejność per klucz (np. per sesja) |
| 7 | Hosting | DigitalOcean, jeden droplet, Docker Compose, Postgres w kontenerze, backup `pg_dump` do Spaces |
| 8 | Dane czasowe | Zwykłe tabele Postgresa, indeks `(session_id, driver_id, ts)`. Partycjonowanie tylko dla `LocationSample`, jeśli wejdzie |
| 9 | Auth | Sesje Django + CSRF, `django-allauth` headless, 2FA admina (`django-otp`) |
| 10 | Nazwa | Undercut (do zmiany w każdej chwili) |
| 11 | Repo | Nowe repo `undercut`, wszystko od zera. Stare `Motorsport_API` zostaje jako archiwum |
| 12 | Frontend | Next.js (App Router) + TypeScript, TanStack Query, ECharts, Tailwind, `next-intl` |
| 13 | Typy API | `drf-spectacular` → `openapi-typescript` + `openapi-fetch` |
| 14 | Rendering | Strony katalogowe SSR z cache, unieważniane zdarzeniem (tagi rewalidacji Next.js). Wykresy, replay, typowanie i ulubione po stronie klienta |
| 15 | Import historii | Zrzut CSV Jolpica na start, potem API dla różnicy. Oba źródła mapowane na te same DTO |
| 16 | Testy | Postgres wszędzie, `pytest` + `factory_boy`, nagrane fixtures bez sieci w CI, testy podwójnego dostarczenia zdarzeń |
| 17 | Przebudowa | Big bang. Brak działającego serwisu w trakcie, dlatego kolejność poniżej |

Ruch: Caddy kieruje `/api` i `/admin` do Django, resztę do Next.js. Jedna domena, więc bez CORS.

## Etapy

| Etap | Zawartość | Co da się pokazać |
|---|---|---|
| 0. Szkielet | Repo, Compose (Postgres, Django, Next.js, Caddy), CI, moduły + `import-linter`, własny `User`, sesje | `docker compose up` działa, CI zielone |
| 1. Zdarzenia | Outbox, worker, scheduler, testy idempotencji | Zdarzenie testowe przechodzi cały obieg |
| 2. Dane | Model v2, klient Jolpica, import zrzutu CSV + różnica, klasyfikacje, `SyncRun`, panel admina | Cała historia F1 w bazie, sync po weekendzie |
| 3. Katalog i klasyfikacje | Kierowca, konstruktor, tor, sezon, runda, klasyfikacje, pulpit | Wersja nadająca się do portfolio |
| **Wdrożenie na DigitalOcean** | Produkcja, TLS, 2FA admina, backup, monitoring | Publiczny link do CV |
| 4. Analityka | Klient OpenF1, pozycje, okrążenia, opony, pit stopy, head-to-head | Najmocniejszy argument dla analityka |
| 5. Konta i typowanie | Rejestracja, Google, ulubieni, typowanie, ligi, e-maile | Pełna pętla użytkownika |
| 6. Replay | Oś czasu, sterowanie, opcjonalnie mapa toru i live | Efekt „wow” |
| 7. Szlif | Konto demo, SEO, dostępność, README z GIF-em | Wydanie |

Zakres funkcjonalny (FR i NFR) zostaje jak w dokumentach, z poprawkami z tego planu.
Przykładowy łańcuch zdarzeń: `SessionResultsFinalized` → klasyfikacje, punkty typowania, e-maile, rewalidacja cache Next.js.

## Domyślne ustalenia z dokumentów (bez zmian)
- Bez zdjęć kierowców i bez logotypów F1 i zespołów (inicjały na kolorze zespołu).
- Płatny OpenF1 live odłożony, decyzja przed etapem 6.
- Interfejs po angielsku, `next-intl` od początku.
- Dane z Jolpica-F1 i OpenF1 (CC BY-NC-SA 4.0): bez monetyzacji, atrybucja na stronie „Źródła” i w stopce.
- Nazwa i logo bez „F1” w formie sugerującej oficjalność.

## Do zrobienia przed etapem 0
- [x] Repo publiczne.
- [x] Domena: bez zakupu, subdomena `undercut.maciejzielinski.dev` (rekord A na droplet, TLS z Caddy).
- [ ] Zweryfikować w dokumentacji Jolpica, jak wygląda zrzut CSV i czy da się go pobrać bez logowania (przy planowaniu etapu 2). Plan awaryjny: import przez API jako wznawialne zadanie.

## Do przepisania w dokumentach
- `04`: harmonogram synchronizacji (zadania pobierają dane, reszta to handlery), sekcja o Celery.
- `05`: stack (Next.js zamiast React + Vite, bez Celery, sesje), hosting.
- `06`: etapy według tabeli powyżej.
- `02`: FR-504 i FR-505 (zdarzenia), FR-801 (idempotencja).
