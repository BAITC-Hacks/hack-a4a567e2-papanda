# hack-a4a567e2-papanda
Hackathon team repository for papanda

**Временный тренировочный репозиторий.** Основной `hack-5273bcd8-papanda`
не участвует в репетиции и очистке. См. [TRAINING.md](TRAINING.md).

## Запуск (Python 3.12, проверено на Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Заполните GROQ_API_KEY, GROQ_MODEL и GROQ_BASE_URL в локальном .env.
.\.venv\Scripts\python -m rehearsal --provider groq --env-file .env
```

Для OpenAI задайте `OPENAI_API_KEY`, `OPENAI_MODEL` и используйте `--provider openai`.
Модель выбирается явно. Реальные обращения отправляются выбранному провайдеру.
Ключи не включаются в репозиторий и логи. Для тестов установите
`requirements-dev.txt`, затем запустите `python -m pytest -q` в окружении.

## Что реализовано

Один общий агент на **OpenAI Agents SDK** читает пять строк `messages.txt` и
печатает категорию и черновик ответа на русском. «Справка» трактуется как
информационный вопрос, «жалоба» — недовольство/неисправность, «другое» — остальные
намерения. JSON проверяется локально; при ошибке нет подставного ответа.

Результаты, входы, промпты, токены, время и ошибки сохраняются локально в
`runs/<run-id>/`. Эти файлы исключены из Git. Журнал разработки: [WORK_LOG.md](WORK_LOG.md).
Базовый агент проверяется реальными вызовами Groq; отчёт — [docs/VERIFICATION.md](docs/VERIFICATION.md).

Две будущие проверки поверх одного базового результата — через DialecticAI и с
нуля — **ещё не реализованы**. Подготовлены интерфейс, механизм сравнения и
[анализ адаптации фреймворка](docs/FRAMEWORK_ADAPTER_PLAN.md).
Содержательную цепочку разрабатываем с пользователем; каркас не доказывает её
диалектическую корректность. Исходные материалы: тексты задания пользователя,
OpenAI Agents SDK и собственный код. DialecticAI пока только изучен, не скопирован.
