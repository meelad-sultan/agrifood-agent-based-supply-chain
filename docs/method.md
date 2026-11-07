# Method details

## World
Each year draws a vector of fractional supply changes for the six farms from a Student-t copula with exponential spatial correlation (200 km) and skew-normal marginals (the process of the companion repository), multiplied by `supply.shock_scale`, applied with a trapezoidal profile over weeks 18 to 36. Production is `capacity x (1 + 0.12 sin(...)) x shock multiplier x (1 + 3 % noise)`. Retailer demand is `mean x (1 + 0.15 e)` with `e` mixing a common and an idiosyncratic AR(1) series (coefficient 0.5, common share 0.5) and a 10 % annual cycle. Shock draws are made before scaling, so changing the scale or the regime leaves demand and the underlying shocks untouched (common random numbers).

## Agent rules
* Smoothing: `mu_t = alpha x_t + (1 - alpha) mu_{t-1}`; the squared one-step error is smoothed with `alpha_sigma` to give a variance estimate.
* Order-up-to with smoothing: `target = mu x cover + z sqrt(var x cover)`, `order = max(0, (1 - beta) mu + beta (target - position))`; `beta = 1` is the base-stock rule.
* Gaming: `order x (1 + g (1 - last fill ratio))` for retailers in `none` and `pos`.
* Rationing: scarce supply is shared pro rata to requests (farmers to processors, processors to their retailers).
* `vmi`: a processor forecasts the pooled demand of its retailers, splits it by base-demand shares and applies the order-up-to rule for them.
* `full`: the processor target is raised by `theta x` (expected shortfall of supply against demand over the next 10 weeks), capped at 4 weeks of demand, using a supply forecast with multiplicative noise.

## Centralised planner
Each week a linear programme over six weeks chooses raw intake `x`, shipments `y`, sales `s`, processor stock `PI` and retail stock `RI` on the pooled chain, minimising `shortage x (planned demand - s) + hold_retail x RI + hold_proc x PI + 0.01 x` subject to stock balances with spoilage, `x <= min(expected supply, capacity)` and `s <= min(stock, planned demand)`; planned demand is expected demand plus `z` standard deviations. Only this week's `x` and `y` are applied.

## Tuning and metrics
For every regime and condition the cover and safety factor (for `full` also the early-warning weight; for `central` the planning safety factor) minimise mean weekly cost on calibration worlds with seeds disjoint from the evaluation worlds. `fill_rate = sales / demand`; `bullwhip = var(orders) / var(consumer demand)`; cost = holding + shortage + spoilage + wasted raw milk. Stock-flow identity: units delivered by farmers equal sales plus spoilage plus the change in stock (including shipments in transit).
