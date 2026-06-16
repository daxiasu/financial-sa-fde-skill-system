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

find . -name ".~*" -o -name "~$*" | while read -r temp_file; do
  rm -f "$temp_file"
done

if [ -f "shared-templates/team_skill_register.xlsx" ]; then
  if ! python3 scripts/excel_to_team_skill_json.py shared-templates/team_skill_register.xlsx data/team_skill_register.json; then
    echo "提示：Excel 转 JSON 失败，继续使用现有 data/team_skill_register.json。"
  fi
fi

python3 scripts/build_skill_packages.py

git add .gitignore index.html README.md publish.sh data scripts shared-templates/team_skill_register.xlsx presales-skill-matrix

if git diff --cached --quiet; then
  echo "没有需要提交的更新。"
  exit 0
fi

git commit -m "$MESSAGE"
git push

echo "已推送到 GitHub。Pages 通常几十秒到几分钟后刷新。"
