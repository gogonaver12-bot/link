#!/bin/sh
# 모든 파일을 하나의 HTML(쉬운공부방.html)로 합칩니다. 과목 추가 후 다시 실행하세요.
cd "$(dirname "$0")"
OUT=쉬운공부방.html
{
  sed -n '1,/<link rel="stylesheet"/p' index.html | grep -v 'rel="stylesheet"'
  echo '<style>'; cat style.css; echo '</style>'
  sed -n '/<\/head>/,/<!-- 과목 파일/p' index.html | grep -v '<!-- 과목 파일'
  for f in $(grep -o 'src="[^"]*"' index.html | cut -d'"' -f2); do echo '<script>'; cat "$f"; echo '</script>'; done
  echo '</body>'; echo '</html>'
} > "$OUT"
echo "만들어짐: $OUT"
