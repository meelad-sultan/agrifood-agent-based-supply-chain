##### Tuned settings per condition (each regime is tuned separately, on calibration worlds with separate seeds)

| condition | regime | cover (weeks) | safety factor z | early-warning weight theta | calibration cost/week |
|---|---|---|---|---|---|
| scale=1.0 | none | 1.0 | 1.28 | nan | 86.0 |
| scale=1.0 | pos | 1.0 | 1.28 | nan | 85.0 |
| scale=1.0 | vmi | 1.0 | 1.28 | nan | 85.8 |
| scale=1.0 | full | 1.0 | 1.28 | 0.0 | 85.8 |
| scale=1.0 | central | nan | 1.28 | nan | 76.7 |
| scale=0.0 | none | 1.0 | 1.28 | nan | 85.7 |
| scale=0.0 | pos | 1.0 | 1.28 | nan | 84.7 |
| scale=0.0 | vmi | 1.0 | 1.28 | nan | 85.5 |
| scale=0.0 | full | 1.0 | 1.28 | 0.0 | 85.5 |
| scale=0.0 | central | nan | 1.28 | nan | 76.6 |
| scale=2.0 | none | 1.0 | 1.28 | nan | 88.5 |
| scale=2.0 | pos | 1.0 | 1.28 | nan | 87.4 |
| scale=2.0 | vmi | 1.0 | 1.28 | nan | 88.2 |
| scale=2.0 | full | 1.0 | 1.28 | 0.0 | 88.2 |
| scale=2.0 | central | nan | 1.28 | nan | 77.7 |
| scale=3.0 | none | 1.0 | 1.28 | nan | 98.6 |
| scale=3.0 | pos | 1.0 | 1.28 | nan | 97.9 |
| scale=3.0 | vmi | 1.0 | 1.28 | nan | 98.6 |
| scale=3.0 | full | 1.0 | 1.28 | 0.0 | 98.6 |
| scale=3.0 | central | nan | 1.28 | nan | 88.5 |
| scale=3.0|noise=0.0 | full | 1.0 | 1.28 | 0.0 | 98.6 |
| scale=3.0|noise=0.0 | central | nan | 1.28 | nan | 88.5 |
| scale=3.0|noise=0.5 | full | 1.0 | 1.28 | 0.0 | 98.6 |
| scale=3.0|noise=0.5 | central | nan | 1.65 | nan | 93.6 |
| scale=3.0|noise=1.0 | full | 1.0 | 1.28 | 0.0 | 98.6 |
| scale=3.0|noise=1.0 | central | nan | 1.0 | nan | 106.3 |

##### E1: information regimes at their tuned settings (median [IQR] over worlds)

| regime | fill rate | bullwhip retail | bullwhip processor | cost / week | stockout weeks |
|---|---|---|---|---|---|
| none | 0.972 [0.965, 0.978] | 1.57 [1.50, 1.63] | 1.66 [1.48, 1.79] | 94.4 [84.7, 100.3] | 0.42 [0.39, 0.47] |
| pos | 0.972 [0.965, 0.977] | 1.63 [1.54, 1.70] | 1.40 [1.28, 1.51] | 93.5 [83.8, 98.3] | 0.43 [0.39, 0.46] |
| vmi | 0.972 [0.965, 0.976] | 1.35 [1.30, 1.44] | 1.34 [1.24, 1.46] | 94.0 [85.1, 99.4] | 0.42 [0.39, 0.46] |
| full | 0.972 [0.965, 0.976] | 1.35 [1.30, 1.44] | 1.34 [1.24, 1.46] | 94.0 [85.1, 99.4] | 0.42 [0.39, 0.46] |
| central | 0.977 [0.973, 0.984] | 0.61 [0.54, 0.66] | 0.39 [0.35, 0.47] | 81.3 [73.5, 88.1] | 0.42 [0.36, 0.47] |

##### Paired differences against `none` (mean [95 % bootstrap interval] over worlds)

| regime | fill rate | bullwhip retail | bullwhip processor | cost / week |
|---|---|---|---|---|
| pos | -0.000 [-0.001, -0.000] | +0.05 [+0.04, +0.06] | -0.25 [-0.28, -0.22] | -1.3 [-1.7, -0.9] |
| vmi | -0.000 [-0.001, -0.000] | -0.20 [-0.22, -0.19] | -0.31 [-0.34, -0.28] | -0.7 [-1.1, -0.2] |
| full | -0.000 [-0.001, -0.000] | -0.20 [-0.22, -0.19] | -0.31 [-0.34, -0.28] | -0.7 [-1.1, -0.2] |
| central | +0.007 [+0.006, +0.008] | -0.97 [-1.03, -0.92] | -1.25 [-1.32, -1.18] | -12.4 [-14.3, -10.3] |

##### Price of decentralisation: cost per week relative to the centralised planner (mean excess in %, 95 % interval)

| regime | excess cost (%) |
|---|---|
| none | +15.2 [+12.9, +17.4] |
| pos | +13.6 [+11.5, +15.8] |
| vmi | +14.4 [+12.2, +16.6] |
| full | +14.4 [+12.2, +16.6] |

##### Cost components per week (tuned, mean)

| regime | hold | short | spoil | waste |
|---|---|---|---|---|
| none | 30.5 | 47.1 | 3.8 | 13.3 |
| pos | 28.6 | 47.8 | 3.6 | 13.3 |
| vmi | 29.3 | 47.7 | 3.7 | 13.3 |
| full | 29.3 | 47.7 | 3.7 | 13.3 |
| central | 30.7 | 36.1 | 3.8 | 11.7 |

##### Same regimes with the untuned default settings (cover 2 weeks, z 1.28; mean), to show how much tuning matters

| regime | fill_rate | bullwhip_retail | bullwhip_proc | cost_per_week |
|---|---|---|---|---|
| none | 0.976 | 8.545 | 2.468 | 255.151 |
| pos | 0.975 | 8.762 | 2.53 | 246.535 |
| vmi | 0.975 | 8.036 | 2.385 | 247.319 |
| full | 0.974 | 8.029 | 2.663 | 249.796 |
| central | 0.977 | 0.606 | 0.407 | 82.318 |

##### E2: climate-shock severity (mean over worlds): fill rate / cost per week

| shock_scale | none | pos | vmi | full | central |
|---|---|---|---|---|---|
| 0.0 | 0.971 / 93.4 | 0.971 / 92.1 | 0.970 / 93.0 | 0.970 / 93.0 | 0.978 / 80.4 |
| 1.0 | 0.970 / 94.8 | 0.969 / 93.5 | 0.969 / 94.4 | 0.969 / 94.4 | 0.977 / 81.9 |
| 2.0 | 0.965 / 100.5 | 0.965 / 99.3 | 0.965 / 100.1 | 0.965 / 100.1 | 0.973 / 87.9 |
| 3.0 | 0.959 / 109.9 | 0.959 / 108.9 | 0.958 / 109.8 | 0.958 / 109.8 | 0.967 / 97.6 |

##### E3: processor bullwhip by retailer forecast reactivity (rows) and order smoothing beta (columns), mean over worlds

Regime **none**

| alpha_retailer | 0.25 | 0.5 | 1.0 |
|---|---|---|---|
| 0.1 | 0.44 | 0.67 | 1.32 |
| 0.3 | 0.69 | 0.97 | 1.65 |
| 0.5 | 0.76 | 1.09 | 1.85 |
| 0.8 | 0.81 | 1.19 | 2.09 |

Regime **vmi**

| alpha_retailer | 0.25 | 0.5 | 1.0 |
|---|---|---|---|
| 0.1 | 0.65 | 0.85 | 1.34 |
| 0.3 | 0.65 | 0.85 | 1.34 |
| 0.5 | 0.65 | 0.85 | 1.34 |
| 0.8 | 0.65 | 0.85 | 1.34 |

##### E4: shortage gaming (order inflation after a rationed shipment), strong climate stress: retail bullwhip / fill rate (mean)

| gaming | none | pos | vmi |
|---|---|---|---|
| 0.0 | 1.55 / 0.960 | 1.59 / 0.959 | 1.35 / 0.959 |
| 0.25 | 1.99 / 0.960 | 2.10 / 0.959 | 1.35 / 0.959 |
| 0.5 | 2.74 / 0.960 | 3.03 / 0.959 | 1.35 / 0.959 |
| 1.0 | 5.61 / 0.960 | 7.29 / 0.959 | 1.35 / 0.959 |

##### E5: quality of the shared supply forecast (noise as a fraction of expected supply), strong climate stress: cost per week / fill rate (mean)

| forecast_noise | central | full |
|---|---|---|
| 0.0 | 93.6 / 0.968 | 104.3 / 0.962 |
| 0.5 | 102.9 / 0.967 | 104.3 / 0.962 |
| 1.0 | 119.9 / 0.963 | 104.3 / 0.962 |
