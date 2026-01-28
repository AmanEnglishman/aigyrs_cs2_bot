.PHONY: build up down logs restart shell help

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образ
	docker compose build

up: ## Запустить контейнер
	docker compose up -d

down: ## Остановить контейнер
	docker compose down

logs: ## Просмотр логов
	docker compose logs -f faceit-bot

restart: ## Перезапустить контейнер
	docker compose restart faceit-bot

shell: ## Войти в контейнер
	docker compose exec faceit-bot /bin/bash

ps: ## Показать статус контейнеров
	docker compose ps

clean: ## Удалить контейнеры и образы
	docker compose down -v --rmi local

