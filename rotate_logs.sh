#!/bin/sh
cd /home/r/notsecbot
for i in $(seq 2 7 | sort -r); do
  if [ -f top_secret_logs_$(($i - 1)).txt ]; then
    mv top_secret_logs_$(($i - 1)).txt top_secret_logs_${i}.txt
  fi
done
mv top_secret_logs.txt top_secret_logs_1.txt
