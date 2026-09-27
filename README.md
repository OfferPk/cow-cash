# 🐄 Cow Cash

A small, cozy browser idle/clicker game. Tap the cow, collect milk, sell it for coins, and grow your farm.

> **Virtual coins only.** Cow Cash is just for fun. There's no real money, no payments, no withdrawals, no ads, and no trackers.

**▶ Play it live:** https://offerpk.github.io/cow-cash/

## How to play

- **Tap the cow** to get milk.
- **Sell milk** for coins with the *Sell* button, or turn on **Auto-sell**.
- **Shop upgrades.** Each one costs about 1.15× more every time you buy it:
  - 🐄 **Extra Cow**: +1 milk per second (passive income)
  - ⚙️ **Milking Machine**: raises your tap multiplier
  - 🌾 **Better Feed**: +50% milk from taps and cows
  - 🏠 **Bigger Barn**: doubles milk storage and adds +10% to the sell price
- Progress **auto-saves** to your browser (localStorage) every 10 seconds, and whenever you leave the page.
- When you come back, your cows' **offline earnings** are paid out (capped at 2 hours).
- **Reset** (with confirmation) starts a fresh farm.

## Run locally

It's plain HTML, CSS, and JS with no build step.

```bash
git clone https://github.com/OfferPk/cow-cash.git
cd cow-cash
# open index.html directly, or serve it:
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Project structure

```
index.html        # page markup
css/style.css     # styles (responsive, mobile-friendly)
js/game.js        # game logic, save/load, offline earnings
assets/cow.svg    # original cow artwork (MIT, part of this repo)
```

## License

[MIT](LICENSE)
