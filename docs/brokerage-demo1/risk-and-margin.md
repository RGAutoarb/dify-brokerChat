# Risk Management and Margin

## Overview

- This document covers leverage, margin requirements, margin calls, and liquidation processes on the brokerage platform.
- For customers who trade on margin, use leveraged products (CFDs, forex), or want to understand how risk is managed.
- Understanding margin and risk controls is essential to protecting your capital and avoiding forced position closures.

## Key Concepts

- **Leverage**: The ability to control a larger position with a smaller amount of your own money. Expressed as a ratio (e.g., 10:1 means $1,000 controls $10,000). Leverage amplifies both profits and losses.
- **Margin**: The amount of your own funds required to open and maintain a leveraged position. Think of it as a security deposit.
- **Initial Margin**: The minimum amount required to open a new position. For example, at 10:1 leverage, the initial margin for a $10,000 position is $1,000.
- **Maintenance Margin**: The minimum equity you must keep in your account to hold open positions. If your equity falls below this level, a margin call is triggered.
- **Equity**: Your account balance plus or minus the unrealized profit or loss on all open positions. This changes in real time as the market moves.
- **Margin Level**: Calculated as (Equity / Used Margin) x 100%. This percentage determines your risk status.
- **Free Margin**: The amount of equity not being used as margin. This is what you have available to open new positions or withdraw.
- **Margin Call**: A warning that your equity has fallen close to the maintenance margin requirement. You must deposit funds or close positions to restore your margin level.
- **Liquidation (Stop-Out)**: The automatic forced closure of your positions when your margin level drops to a critical threshold. This protects you from owing more than your account balance.
- **Negative Balance Protection**: A safeguard that ensures you cannot lose more than the total funds in your account. Your balance will never go below zero.

## How It Works

### Margin Levels and Risk Stages

| Margin Level | Status | What Happens |
|---|---|---|
| Above 150% | Healthy | Full trading functionality. You can open new positions and withdraw free margin. |
| 100% - 150% | Warning | You can still trade but should monitor positions closely. No new leveraged positions recommended. |
| 80% - 100% | Margin Call | You receive a margin call notification by email and on-platform alert. Deposit funds or close positions to increase your margin level. You cannot open new positions. |
| Below 50% | Liquidation (Stop-Out) | The platform automatically closes your largest losing position. If margin level remains below 50%, positions continue to be closed one by one until the level recovers above 50%. |

### How Leverage Works in Practice

**Example:** You have $1,000 in your account and use 10:1 leverage to buy $10,000 worth of EUR/USD.

- If EUR/USD rises 2%, your position gains $200 (a 20% return on your $1,000).
- If EUR/USD falls 2%, your position loses $200 (a 20% loss on your $1,000).
- If EUR/USD falls 5%, your position loses $500 (a 50% loss), and you would be near margin call territory.

### Available Leverage by Product

| Product | Maximum Leverage | Initial Margin Required |
|---|---|---|
| Major Forex Pairs | 30:1 | 3.33% |
| Minor Forex Pairs | 20:1 | 5% |
| Major Stock Indices (CFD) | 20:1 | 5% |
| Individual Stocks (CFD) | 5:1 | 20% |
| Commodities (Gold, Oil) | 10:1 | 10% |
| Cryptocurrency | 2:1 | 50% |

### What Happens During a Margin Call

1. Your margin level drops to 100% or below.
2. You receive an immediate email and in-app notification.
3. You are blocked from opening new leveraged positions.
4. You have the option to deposit more funds or close positions voluntarily.
5. If your margin level drops to 50% (stop-out level), automatic liquidation begins.

### What Happens During Liquidation

1. The platform identifies your largest losing position.
2. That position is automatically closed at the current market price.
3. Your margin level is recalculated.
4. If the margin level is still below 50%, the next largest losing position is closed.
5. This continues until the margin level rises above 50% or all positions are closed.
6. Negative balance protection applies: your account balance cannot go below zero.

## Common Questions

- **Q: What is leverage and should I use it?**
  A: Leverage lets you trade with more money than you have in your account. While it can increase your profits, it equally increases your losses. If you are new to trading, start with low leverage or no leverage at all.

- **Q: What is a margin call?**
  A: A margin call is a warning that your account equity is too low relative to your open positions. You need to either add funds or close some positions to avoid automatic liquidation.

- **Q: At what point are my positions automatically closed?**
  A: Automatic liquidation begins when your margin level drops to 50%. The platform closes your largest losing position first and continues until the level recovers above 50%.

- **Q: Can I lose more money than I deposited?**
  A: No. Negative balance protection ensures your account balance never goes below zero. In extreme market conditions, any negative balance is reset to zero.

- **Q: How do I check my current margin level?**
  A: Go to **Portfolio > Account Summary**. Your margin level, equity, used margin, and free margin are displayed in real time.

- **Q: Can I change my leverage?**
  A: Yes. Go to **Settings > Trading Preferences > Leverage**. Note that reducing leverage requires sufficient margin for existing positions. Changes apply to new positions only.

- **Q: Why can't I open a new position?**
  A: Your free margin may be insufficient, or you may be in a margin call state. Check your margin level under **Portfolio > Account Summary**.

- **Q: What is the difference between balance and equity?**
  A: Balance is your deposited funds plus realized (closed) profits and losses. Equity is your balance plus unrealized (open) profits and losses. Equity fluctuates with the market in real time.

- **Q: Do margin requirements change?**
  A: Yes. During periods of high volatility or before major economic events, margin requirements may be temporarily increased. You will be notified in advance via email and platform notification.

- **Q: How can I reduce my risk?**
  A: Use lower leverage, set stop-loss orders on every position, diversify across different instruments, never risk more than 1-2% of your account on a single trade, and monitor your margin level regularly.

## Common Issues and Resolutions

- **Issue:** Received a margin call notification
  - **Possible Causes:** Open positions moved against you; market gapped overnight; margin requirements were increased.
  - **Resolution Steps:** 1) Log in immediately and check **Portfolio > Account Summary**. 2) Close some losing positions to free up margin. 3) Deposit additional funds via the fastest available method (card or wallet for instant credit). 4) Set stop-loss orders on remaining positions to prevent further losses.
  - **When to Escalate:** If the margin call appears to be triggered incorrectly, or if the margin level displayed does not match the customer's own calculations.

- **Issue:** Position was liquidated unexpectedly
  - **Possible Causes:** Market moved rapidly (especially during news events or overnight gaps); customer was not monitoring margin level; margin requirements were temporarily increased.
  - **Resolution Steps:** 1) Review the liquidation details under **Portfolio > Trade History**, including the exact time and price. 2) Explain the liquidation mechanism (positions closed at stop-out level of 50%). 3) Suggest setting stop-loss orders to close positions before reaching liquidation levels in the future.
  - **When to Escalate:** If the customer believes the liquidation price was incorrect, the stop-out occurred at the wrong margin level, or the platform experienced a technical issue during the event.

- **Issue:** Cannot reduce leverage on existing positions
  - **Possible Causes:** Reducing leverage increases the margin required for existing positions, and the account may not have sufficient free margin to support the change.
  - **Resolution Steps:** 1) Close some positions to free up margin before changing leverage. 2) Deposit additional funds. 3) Note that leverage changes apply to new positions; existing positions retain their original leverage.
  - **When to Escalate:** If the platform does not allow a leverage change even after sufficient funds are available.

- **Issue:** Free margin shows zero but no positions are open
  - **Possible Causes:** Pending withdrawal reserving funds; pending orders holding margin; platform display delay.
  - **Resolution Steps:** 1) Check for pending orders under **Portfolio > Pending Orders** and cancel any that are no longer needed. 2) Check for pending withdrawals under **Funds > History**. 3) Refresh the platform or log out and back in.
  - **When to Escalate:** If no pending orders or withdrawals exist and the free margin still displays incorrectly.

- **Issue:** Margin requirements changed without notice
  - **Possible Causes:** Regulatory update; scheduled increase ahead of a major economic event; product-specific risk adjustment.
  - **Resolution Steps:** 1) Check email and in-app notifications for margin change announcements. 2) Review the updated margin schedule under **Settings > Trading Preferences**. 3) Adjust positions or add funds to meet the new requirements.
  - **When to Escalate:** If no notification was sent and the customer was adversely affected by the unannounced change.

## Escalation and Support Routing

- **Do not handle:** Liquidation disputes, suspected platform errors during margin events, requests for margin call extensions or exceptions, or any request for trading advice.
- **Route to Trading Desk:** Liquidation disputes, margin level discrepancies, execution issues during stop-out events.
- **Route to Risk Team:** Requests for custom leverage or margin arrangements, account-level risk reviews, margin requirement change queries.
- **Information to collect before escalation:** Account email, margin level at the time of the event, position details (instrument, size, direction), timestamps, and any screenshots of the account summary or error messages.

## Related Topics

- [Accounts and Onboarding](accounts-and-onboarding.md)
- [Trading Products and Order Execution](trading-products-and-execution.md)
- [Deposits, Withdrawals, and Fees](deposits-withdrawals-fees.md)
