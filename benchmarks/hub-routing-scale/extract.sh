#!/usr/bin/env bash
# Clone one registry corpus exactly as `xerj hub build-pack` does (`xerj corpus
# add <slug> --from <manifest>`: shallow fetch of the pinned sha), extract its
# sketch terms with the pack builder's own code, then delete the clone.
#   extract.sh <slug>     (env: XERJ, HUB_SCALE, REG, RUN, WORKER)
set -u
slug=$1
home="$RUN/code/w${WORKER:-0}"
mkdir -p "$home" "$RUN/terms" "$RUN/logs"
[ -s "$RUN/terms/$slug.stats" ] && exit 0
start=$(date +%s)
if XERJ_CODE_HOME="$home" timeout 1800 "$XERJ" corpus add "$slug" --from "$REG/$slug.json" \
     > "$RUN/logs/$slug.add.log" 2>&1; then
  "$HUB_SCALE" extract "$home" "$REG" "$slug" "$RUN/terms" > "$RUN/logs/$slug.extract.log" 2>&1 \
    || echo "$slug extract-failed" >> "$RUN/failed.txt"
else
  echo "$slug add-failed" >> "$RUN/failed.txt"
fi
du -sb "$home/corpora/$slug" 2>/dev/null | awk -v s="$slug" '{print s, $1}' >> "$RUN/clone_bytes.txt"
rm -rf "$home/corpora/$slug"
echo "$slug $(( $(date +%s) - start ))s $(cat "$RUN/terms/$slug.stats" 2>/dev/null)"
