# Discovery Findings: Flight Price Poller & Baggage Pricing

## 1. Baggage Impact on Pricing
- **Baseline Fare (0 bags):** Porter ($591 USD) and WestJet ($656 USD) appear cheapest on Basic Economy fares.
- **1 Carry-on Added:** WestJet jumps to $850 USD, Air Canada is $853 USD. Porter drops out because basic fare disallows carry-on bags.
- **1 Carry-on + 1 Checked Bag Added:** Air Canada becomes cheapest at $917 USD; WestJet is $962 USD.
- **Conclusion:** Without baggage filtering during polling, tracked prices would be wildly inaccurate and misleading for users traveling with luggage.

## 2. Playwright Headless vs. Headed Execution
- **Headed Vivaldi (`actions/browser_control.py`):** Great for interactive user commands, but disruptive for background polling at 8:30 AM or 6:30 PM because the browser window pops up and steals focus.
- **Headless Chromium (`async_playwright(headless=True)`):** Takes ~5 seconds to run the complete two-leg round-trip scrape with bag filters applied, producing 0 window popups or desktop focus interruptions.
