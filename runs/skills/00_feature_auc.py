"""stat-test step: which existing features separate labeled positives from the rest?
AUC = Mann-Whitney U / (n1*n0). Positive-unlabeled data, so AUC is a lower bound on true separation."""
import pandas as pd, numpy as np
from scipy.stats import mannwhitneyu
F = pd.read_parquet('/Users/giocaballero/avangrid-hackathon/data/processed/features.parquet')
cols = [c for c in F.columns if c not in ('CUSTOMER_NUMBER','lab_ev','lab_hp','lab_pv') and not c.startswith('kwh_m')]
for lab in ['lab_ev','lab_hp','lab_pv']:
    rows=[]
    for c in cols:
        x = F[c].fillna(F[c].median()); p = x[F[lab]==1]; u = x[F[lab]==0]
        U, pv = mannwhitneyu(p, u)
        rows.append((c, U/(len(p)*len(u)), pv))
    r = pd.DataFrame(rows, columns=['feat','auc','p']); r['sep']=(r.auc-0.5).abs()
    print(lab, '\n', r.sort_values('sep', ascending=False).head(10).to_string(index=False))
