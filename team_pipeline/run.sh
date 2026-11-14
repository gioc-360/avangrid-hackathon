# Ingest AMI zips into a customer x hour matrix (kwh.npy).
# Per Avangrid guidance, customers 10,001 to 20,000 are out of scope.
# The zip named Data_10001_20000 duplicates customers 1 to 10,000, so it is skipped.
cd $HOME/work; D="$HOME/mnt/00_Hackathon Materials/Data"; i=0
for z in "$D"/2026*.zip; do
  case "$z" in *Data_10001_20000*) echo "skipping $z (out of scope)"; continue;; esac
  i=$((i+1)); python3 ingest.py "$z" z$i 150 &
done; wait; wc -l done.txt
