#!/bin/bash
# Скрипт для подключения к GitHub репозиторию

echo "🚀 Настройка GitHub репозитория"
echo ""
echo "Убедитесь, что вы уже создали репозиторий на GitHub.com"
echo ""

read -p "Введите ваш GitHub username: " GITHUB_USER
read -p "Введите название репозитория: " REPO_NAME

REMOTE_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo ""
echo "Добавляю remote origin: $REMOTE_URL"
git remote add origin $REMOTE_URL

echo ""
echo "✅ Remote добавлен!"
echo ""
echo "Теперь можно запушить код:"
echo "  git push -u origin main"
echo ""
echo "Или запустите:"
echo "  ./push_to_github.sh"
