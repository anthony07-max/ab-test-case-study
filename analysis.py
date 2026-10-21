"""Cookie Cats A/B test: does moving the first gate from level 30 to 40 change retention?"""
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
rng = np.random.default_rng(42); out = []
def p(*a): s=" ".join(str(x) for x in a); print(s); out.append(s)

df = pd.read_csv("data/cookie_cats.csv")
p("Rows:", len(df), "| duplicate userids:", df.userid.duplicated().sum(), "| missing:", int(df.isna().sum().sum()))
df = df.drop_duplicates("userid")
p("Versions:", sorted(df.version.unique()))
p("Outlier sum_gamerounds max:", df.sum_gamerounds.max())
df = df[df.sum_gamerounds < df.sum_gamerounds.max()]  # drop single extreme outlier
n = df.version.value_counts(); p("Group sizes:", n.to_dict())
srm = stats.chisquare(n.values); p(f"SRM chi-square p = {srm.pvalue:.4f}", "(SRM!)" if srm.pvalue < 0.01 else "(no SRM)")

A, B = df[df.version=="gate_30"], df[df.version=="gate_40"]
for m in ["retention_1", "retention_7"]:
    xa, xb, na, nb = A[m].sum(), B[m].sum(), len(A), len(B)
    ra, rb = xa/na, xb/nb
    z, pv = proportions_ztest([xb, xa], [nb, na])
    lo, hi = confint_proportions_2indep(xb, nb, xa, na, method="wald")
    boot = [rng.choice(B[m].values, nb).mean() - rng.choice(A[m].values, na).mean() for _ in range(2000)]
    bl, bh = np.percentile(boot, [2.5, 97.5])
    pa = rng.beta(1+xa, 1+na-xa, 100000); pb = rng.beta(1+xb, 1+nb-xb, 100000)
    mde = NormalIndPower().solve_power(nobs1=na, alpha=0.05, power=0.8, ratio=nb/na)
    # convert Cohen's h MDE to absolute pp around ra
    mde_abs = np.sin(np.arcsin(np.sqrt(ra)) - mde/2)**2 - ra
    pw = NormalIndPower().power(abs(proportion_effectsize(rb, ra)), nobs1=na, alpha=0.05, ratio=nb/na)
    p(f"\n{m}: gate_30 {ra:.4%} (n={na}) | gate_40 {rb:.4%} (n={nb})")
    p(f"  diff (40-30) = {(rb-ra)*100:.3f} pp, relative {(rb/ra-1):.2%}")
    p(f"  z = {z:.3f}, p = {pv:.4f}, 95% CI [{lo*100:.3f}, {hi*100:.3f}] pp")
    p(f"  bootstrap 95% CI [{bl*100:.3f}, {bh*100:.3f}] pp")
    p(f"  Bayesian P(gate_30 > gate_40) = {(pa>pb).mean():.4f}")
    p(f"  MDE at 80% power, alpha .05: ~{abs(mde_abs)*100:.2f} pp | power to detect observed diff: {pw:.2%}")
    globals()[m] = (ra, rb, lo, hi, boot)

df["engage"] = pd.cut(df.sum_gamerounds, [-1, 0, 29, 39, 1e9], labels=["0 rounds", "1-29", "30-39", "40+"])
seg = df.groupby(["engage", "version"], observed=True).retention_7.agg(["mean", "size"]).unstack()
p("\nSegment: 7-day retention by rounds played\n" + seg.round(4).to_string())

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for i, m in enumerate(["retention_1", "retention_7"]):
    ra, rb, *_ = globals()[m]
    ax[i].bar(["gate_30", "gate_40"], [ra*100, rb*100], color=["#4C72B0", "#DD8452"])
    for j, v in enumerate([ra, rb]): ax[i].text(j, v*100+0.3, f"{v:.2%}", ha="center")
    ax[i].set_title(m.replace("_", "-") + " day retention"); ax[i].set_ylabel("%")
plt.tight_layout(); plt.savefig("charts/retention_by_group.png", dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(7, 4))
for m, c in [("retention_1", "#4C72B0"), ("retention_7", "#DD8452")]:
    ax.hist(np.array(globals()[m][4])*100, bins=50, alpha=.6, color=c, label=m)
ax.axvline(0, color="k", ls="--"); ax.set_xlabel("gate_40 minus gate_30 (pp)"); ax.legend()
ax.set_title("Bootstrap distribution of retention difference"); plt.tight_layout()
plt.savefig("charts/bootstrap_diff.png", dpi=150); plt.close()

(seg["mean"]*100).plot.bar(figsize=(7, 4), rot=0, color=["#4C72B0", "#DD8452"])
plt.ylabel("7-day retention %"); plt.title("7-day retention by rounds played (segment)")
plt.tight_layout(); plt.savefig("charts/segment_retention7.png", dpi=150)
open("results.txt", "w").write("\n".join(out))
