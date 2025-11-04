#!/bin/bash
# Скрипт для push в GitHub

echo "📤 Push в GitHub..."

# Проверка наличия remote
if ! git remote | grep -q origin; then
    echo "❌ Remote 'origin' не найден!"
    echo ""
    echo "Сначала запустите:"
    echo "  ./setup_github.sh"
    echo ""
    echo "Или создайте репозиторий на GitHub.com и выполните:"
    echo "  git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    exit 1
fi

# Проверка изменений
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Есть незакоммиченные изменения. Добавить и закоммитить? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        git add .
        git commit -m "Update: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
fi

# Push
echo ""
echo "Отправляю изменения..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Успешно отправлено в GitHub!"
    echo ""
    REMOTE_URL=$(git remote get-url origin)
    echo "Репозиторий: $REMOTE_URL"
else
    echo ""
    echo "❌ Ошибка при отправке. Проверьте настройки remote:"
    echo "  git remote -v"
fi
