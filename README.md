# 🐄 Cow Cash

A small, cozy browser idle/clicker game. Tap the cow, collect milk, sell it for coins, and grow your farm.

> **Virtual coins only.** Cow Cash is just for fun. There's no real money, no payments, no withdrawals, no ads, and no trackers.

**▶ Play it live:** https://offerpk.github.io/cow-cash/

## How to play

- **Tap the cow** to get milk.
- **Sell milk** for coins with the *Sell* button, or turn on **Auto-sell** to sell milk as it's produced during active play.
- **Shop upgrades.** Repeatable upgrades cost about 1.15× more each time you buy them:
  - 🐄 **Extra Cow**: +1 milk per second (passive income)
  - ⚙️ **Milking Machine**: raises your tap multiplier
  - 🌾 **Better Feed**: +50% milk from taps and cows
  - 🏠 **Bigger Barn**: doubles milk storage and adds +10% to the sell price
  - 🏭 **Dairy Factory**: one-time 25,000-coin upgrade that triples the sell price
- 🐮 **Baby Cow**: one-time 15,000-coin upgrade for +15% global milk production. After 12 elapsed hours online or offline, it becomes a **Golden/Trophy Cow** with a permanent +15 milk/sec and a badge.
- Progress **auto-saves** to your browser (localStorage) every 10 seconds, and whenever you leave the page.
- When you come back, your cows' **offline earnings** are paid directly as coins (capped at 2 hours), regardless of Auto-sell; your milk is unchanged.
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
