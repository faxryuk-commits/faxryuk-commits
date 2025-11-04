#!/bin/bash
# Быстрый push после создания репозитория

echo "📤 Отправка в GitHub..."
echo ""

# Проверка remote
if git remote | grep -q origin; then
    echo "Remote настроен:"
    git remote -v
    echo ""
else
    echo "⚠️  Remote не настроен. Настраиваю..."
    git remote add origin https://github.com/faxryuk-commits/faxryuk-commits.git
fi

# Push
echo "Отправляю код..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Успешно отправлено!"
    echo "Репозиторий: https://github.com/faxryuk-commits/faxryuk-commits"
else
    echo ""
    echo "❌ Ошибка. Убедитесь, что:"
    echo "  1. Репозиторий создан на GitHub.com"
    echo "  2. У вас есть права доступа"
    echo "  3. Правильное название: faxryuk-commits/faxryuk-commits"
fi
