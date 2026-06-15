#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "用法：./publish.sh \"本次更新说明\""
  exit 1
fi

MESSAGE="$*"

cd "$(dirname "$0")"

find . -name "*.swp" -o -name "*.swo" -o -name ".DS_Store" | while read -r temp_file; do
  rm -f "$temp_file"
done

if [ -f "shared-templates/team_skill_register.xlsx" ]; then
  python3 scripts/excel_to_team_skill_json.py shared-templates/team_skill_register.xlsx data/team_skill_register.json
fi

git add .

if git diff --cached --quiet; then
  echo "没有需要提交的更新。"
  exit 0
fi

git commit -m "$MESSAGE"
git push

echo "已推送到 GitHub。Pages 通常几十秒到几分钟后刷新。"
