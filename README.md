## Extreme Dashboard

### Refresh the Mean Reversion backtest page

After running RevMurphy, generate the public page from its compact CSV outputs:

```powershell
python generate_mean_reversion_page.py --source ../RevMurphy/output_long_short
```

This writes `mean-reversion.html`. The page clearly identifies the results as a
simulated backtest and does not import the large `all_signals.csv` file.

### Refresh the Dual Momentum backtest page

After running `DualMom/momo5.py`, generate the public page from its outputs:

```powershell
python generate_momentum_page.py --source ../DualMom/output_momo5
```

This replaces the old placeholder `momentum.html` with the Dual Momentum
backtest, SPY comparison, return tables, and monthly allocation history.
