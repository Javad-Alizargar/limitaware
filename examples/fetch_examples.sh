#!/bin/sh
# Exact queries used for the evaluation exports. Data are not redistributed;
# re-fetch them and compare the digests printed at the end with the values in
# evaluation/results/*/audit.json and evaluation/README.
set -e
UA="Mozilla/5.0"
BASE="https://www.waterqualitydata.us/data/Result/search"

curl -sL -A "$UA" -o iowa_atrazine_2019-2021.csv \
  "$BASE?statecode=US%3A19&characteristicName=Atrazine&startDateLo=01-01-2019&startDateHi=12-31-2021&mimeType=csv&zip=no"

curl -sL -A "$UA" -o new_york_metolachlor_2021.csv \
  "$BASE?statecode=US%3A36&characteristicName=Metolachlor&startDateLo=01-01-2021&startDateHi=12-31-2021&mimeType=csv&zip=no"

curl -sL -A "$UA" -o ohio_prometon_2021.csv \
  "$BASE?statecode=US%3A39&characteristicName=Prometon&startDateLo=01-01-2021&startDateHi=12-31-2021&mimeType=csv&zip=no"

shasum -a 256 iowa_atrazine_2019-2021.csv new_york_metolachlor_2021.csv ohio_prometon_2021.csv
