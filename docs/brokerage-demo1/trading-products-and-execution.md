# Trading Products and Order Execution

## Overview

- This document covers the financial products available for trading and how orders are placed and executed on the platform.
- For customers who want to understand what they can trade and how the trading process works.
- Understanding products and order types helps you make informed decisions and avoid common mistakes.

## Key Concepts

- **Stock**: A share of ownership in a publicly traded company. When you buy a stock, you own a small piece of that company.
- **Forex (FX)**: The foreign exchange market where currencies are traded in pairs (e.g., EUR/USD). You profit when the exchange rate moves in your favor.
- **CFD (Contract for Difference)**: A derivative product that lets you speculate on price movements without owning the underlying asset. CFDs use leverage and carry significant risk.
- **Options**: Contracts giving you the right (but not obligation) to buy or sell an asset at a specific price before a specific date.
- **Cryptocurrency**: Digital assets like Bitcoin and Ethereum that can be traded 24/7. Highly volatile.
- **Market Order**: An order to buy or sell immediately at the best available price. Execution is fast but the exact price is not guaranteed.
- **Limit Order**: An order to buy or sell only at a specific price or better. The price is guaranteed but execution is not.
- **Stop-Loss Order**: An order that automatically sells your position if the price drops to a specified level. Used to limit losses.
- **Take-Profit Order**: An order that automatically closes your position once a target profit level is reached.
- **Spread**: The difference between the buy (ask) price and the sell (bid) price. This is an implicit cost of trading.
- **Slippage**: The difference between the expected price and the actual execution price, usually during fast-moving markets.

## How It Works

### Placing a Trade

1. Log in to your verified and funded account.
2. Search for the instrument you want to trade using the search bar or browse by category (Stocks, Forex, CFDs, Options, Crypto).
3. Select the instrument to open its trading panel.
4. Choose your order type: Market, Limit, or Stop.
5. Enter the quantity or trade size.
6. Optionally set a **Stop-Loss** and/or **Take-Profit** level.
7. Review the order summary, including estimated cost and fees.
8. Click **Confirm** to submit the order.
9. Market orders execute immediately. Limit and stop orders remain pending until the target price is reached or you cancel them.

### Trading Hours

- **Stocks**: Monday to Friday, 9:30 AM - 4:00 PM ET (US markets). Pre-market and after-hours sessions available with limit orders only.
- **Forex**: 24 hours, Sunday 5:00 PM ET to Friday 5:00 PM ET.
- **CFDs**: Follow the underlying market hours.
- **Cryptocurrency**: 24 hours, 7 days a week.
- **Options**: Monday to Friday, 9:30 AM - 4:00 PM ET.

## Common Questions

- **Q: What is the minimum trade size?**
  A: Stocks can be traded in fractional shares (minimum $1). Forex minimum lot size is 0.01 (micro lot). CFD and crypto minimums vary by instrument and are shown on the trading panel.

- **Q: Why was my order not filled?**
  A: Limit orders only execute when the market reaches your specified price. If the price never reaches that level, the order stays pending. You can cancel it at any time.

- **Q: What is the difference between a market order and a limit order?**
  A: A market order fills immediately at the current best price. A limit order only fills at your chosen price or better, but may never fill if the market does not reach that price.

- **Q: Can I trade outside of market hours?**
  A: Pre-market and after-hours trading is available for US stocks using limit orders only. Forex and crypto trade around the clock.

- **Q: What happens if I hold a CFD overnight?**
  A: You will be charged an overnight financing fee (also called a swap fee). The rate depends on the instrument and your position direction. Fees are shown in the instrument details page.

- **Q: How do I close an open position?**
  A: Go to **Portfolio > Open Positions**, select the position, and click **Close**. You can close the full position or a partial amount.

- **Q: What does "pending order" mean?**
  A: A pending order (limit or stop) has been submitted but not yet executed. It will remain active until the target price is hit, the order expires, or you cancel it manually.

- **Q: Can I set both a stop-loss and take-profit on the same trade?**
  A: Yes. You can attach both when placing the order or add them afterward from the open positions view.

- **Q: Why is the price I got different from the price I saw?**
  A: This is called slippage. It happens when the market moves between the time you submit the order and when it executes, most commonly during high volatility or with market orders.

## Common Issues and Resolutions

- **Issue:** Order rejected with "insufficient funds" error
  - **Possible Causes:** Account balance is too low for the trade size; existing open positions are using available margin; pending deposits have not cleared.
  - **Resolution Steps:** 1) Check your available balance under **Portfolio > Account Summary**. 2) Reduce the trade size or close existing positions to free up funds. 3) If you recently deposited, check if the deposit has been confirmed under **Funds > History**.
  - **When to Escalate:** If the balance shown appears incorrect or does not match recent deposits.

- **Issue:** Trade executed at an unexpected price
  - **Possible Causes:** Slippage during volatile market conditions; using a market order during news events; wide spread on illiquid instruments.
  - **Resolution Steps:** 1) Review the execution details under **Portfolio > Trade History**. 2) Use limit orders to control the execution price in the future. 3) Avoid market orders during major economic announcements.
  - **When to Escalate:** If the execution price is significantly outside the displayed spread at the time of the order.

- **Issue:** Cannot find an instrument on the platform
  - **Possible Causes:** Instrument may not be offered; search term may be misspelled; instrument may be temporarily unavailable due to a corporate action or market halt.
  - **Resolution Steps:** 1) Try searching by ticker symbol and by full company name. 2) Check the **Instrument List** page filtered by category. 3) Review platform announcements for any temporary suspensions.
  - **When to Escalate:** If the customer is searching for an instrument that should be available based on the platform's advertised product list.

- **Issue:** Stop-loss did not trigger at the exact price set
  - **Possible Causes:** Market gapped past the stop-loss level (common during overnight sessions or after news); stop-loss orders become market orders when triggered and may execute at the next available price.
  - **Resolution Steps:** 1) Explain that stop-loss orders guarantee execution, not price. 2) Review the execution price under **Trade History**. 3) Suggest using guaranteed stop-loss orders (if available on the platform) for exact price protection, noting the additional fee.
  - **When to Escalate:** If the execution price is unreasonably far from the stop level and no market gap is evident.

- **Issue:** Open position shows "liquidation warning"
  - **Possible Causes:** Account equity has dropped near the maintenance margin level due to adverse price movement.
  - **Resolution Steps:** 1) Deposit additional funds immediately. 2) Close some positions to reduce exposure. 3) Review the [Risk Management and Margin](risk-and-margin.md) document for details on margin levels.
  - **When to Escalate:** If the customer has already been liquidated and disputes the liquidation price or timing.

## Escalation and Support Routing

- **Do not handle:** Disputes over execution prices, requests for trade reversals, suspected platform errors during execution, or questions about specific investment advice.
- **Route to Trading Desk:** Execution disputes, order fill issues, suspected price feed errors, corporate action adjustments.
- **Route to Product Team:** Requests for new instruments, feedback on platform features.
- **Information to collect before escalation:** Order ID or trade reference number, instrument traded, date and time of the trade, expected vs. actual price, screenshots if available.

## Related Topics

- [Accounts and Onboarding](accounts-and-onboarding.md)
- [Deposits, Withdrawals, and Fees](deposits-withdrawals-fees.md)
- [Risk Management and Margin](risk-and-margin.md)
