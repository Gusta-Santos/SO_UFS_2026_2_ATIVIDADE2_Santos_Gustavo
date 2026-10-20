#!/bin/bash
cd ~/genresearch/src
OUT=../results/c1_c2.csv
for size in 10mb 100mb 500mb; do
  for mode in read mmap; do
    for pat in seq rand; do
      for rep in 1 2 3; do
        sync; sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
        python memtest.py --file ../data/corpus_${size}.txt --mode $mode --pattern $pat --label cold --rep $rep --out $OUT > /dev/null
        python memtest.py --file ../data/corpus_${size}.txt --mode $mode --pattern $pat --label warm --rep $rep --out $OUT > /dev/null
      done
    done
  done
done
echo "pronto: $OUT"
