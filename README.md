## Extreme Dashboard

### Refresh the Mean Reversion backtest page

After running RevMurphy, generate the public page from its compact CSV outputs:

```powershell
python generate_mean_reversion_page.py --source ../RevMurphy/output_long_short
```

This writes `mean-reversion.html`. The page clearly identifies the results as a
simulated backtest and does not import the large `all_signals.csv` file.
