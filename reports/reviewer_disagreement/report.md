# Reviewer disagreement — Lei vs Mattia (ACDC)

Cases where the two reviewers reached different decisions. The **#** column is the patient number shown in the QC Studio, so you can jump straight to it.

## Summary

| Dataset | Disagreements | Lei accepted only | Mattia accepted only | Agreement |
|---|---|---|---|---|
| base (sabotaged, no repair) | 50 | 25 | 25 | 83% |
| rule-based fix | 57 | 4 | 53 | 81% |
| agent (gpt-5.5) | 95 | 13 | 82 | 68% |

Lei applies a stricter bar throughout — her accepted cases are almost a subset of Mattia's, so nearly all disagreements are cases Mattia accepted and Lei did not.


## base (sabotaged, no repair)

50 disagreements out of 300 phases.


### Mattia accepted · Lei rejected — 25 cases

| # | Patient | Phase |
|---|---|---|
| 4 | patient004 | ES |
| 18 | patient018 | ED |
| 26 | patient026 | ED |
| 26 | patient026 | ES |
| 28 | patient028 | ED |
| 31 | patient031 | ED |
| 36 | patient036 | ED |
| 38 | patient038 | ES |
| 42 | patient042 | ED |
| 43 | patient043 | ES |
| 48 | patient048 | ES |
| 49 | patient049 | ED |
| 49 | patient049 | ES |
| 56 | patient056 | ED |
| 57 | patient057 | ED |
| 57 | patient057 | ES |
| 59 | patient059 | ED |
| 72 | patient072 | ES |
| 78 | patient078 | ES |
| 80 | patient080 | ES |
| 96 | patient096 | ED |
| 102 | patient102 | ES |
| 122 | patient122 | ES |
| 135 | patient135 | ED |
| 143 | patient143 | ED |


### Lei accepted · Mattia rejected — 25 cases

| # | Patient | Phase |
|---|---|---|
| 8 | patient008 | ED |
| 32 | patient032 | ED |
| 36 | patient036 | ES |
| 40 | patient040 | ED |
| 44 | patient044 | ED |
| 44 | patient044 | ES |
| 63 | patient063 | ED |
| 64 | patient064 | ES |
| 66 | patient066 | ES |
| 67 | patient067 | ED |
| 68 | patient068 | ES |
| 69 | patient069 | ES |
| 71 | patient071 | ED |
| 75 | patient075 | ES |
| 79 | patient079 | ES |
| 83 | patient083 | ED |
| 100 | patient100 | ES |
| 116 | patient116 | ED |
| 119 | patient119 | ES |
| 124 | patient124 | ED |
| 124 | patient124 | ES |
| 126 | patient126 | ES |
| 140 | patient140 | ES |
| 144 | patient144 | ES |
| 147 | patient147 | ES |


## rule-based fix

57 disagreements out of 300 phases.


### Mattia accepted · Lei rejected — 53 cases

| # | Patient | Phase |
|---|---|---|
| 4 | patient004 | ES |
| 5 | patient005 | ED |
| 5 | patient005 | ES |
| 13 | patient013 | ED |
| 13 | patient013 | ES |
| 16 | patient016 | ED |
| 18 | patient018 | ES |
| 24 | patient024 | ES |
| 28 | patient028 | ED |
| 30 | patient030 | ES |
| 31 | patient031 | ES |
| 32 | patient032 | ED |
| 33 | patient033 | ED |
| 33 | patient033 | ES |
| 34 | patient034 | ED |
| 34 | patient034 | ES |
| 35 | patient035 | ED |
| 42 | patient042 | ED |
| 49 | patient049 | ED |
| 49 | patient049 | ES |
| 50 | patient050 | ES |
| 51 | patient051 | ED |
| 52 | patient052 | ED |
| 52 | patient052 | ES |
| 55 | patient055 | ES |
| 57 | patient057 | ED |
| 59 | patient059 | ED |
| 59 | patient059 | ES |
| 64 | patient064 | ED |
| 77 | patient077 | ES |
| 85 | patient085 | ED |
| 92 | patient092 | ED |
| 96 | patient096 | ED |
| 98 | patient098 | ES |
| 99 | patient099 | ED |
| 102 | patient102 | ED |
| 102 | patient102 | ES |
| 105 | patient105 | ED |
| 106 | patient106 | ED |
| 108 | patient108 | ED |
| 110 | patient110 | ED |
| 112 | patient112 | ED |
| 113 | patient113 | ES |
| 116 | patient116 | ED |
| 117 | patient117 | ED |
| 118 | patient118 | ED |
| 121 | patient121 | ES |
| 128 | patient128 | ED |
| 128 | patient128 | ES |
| 130 | patient130 | ES |
| 135 | patient135 | ED |
| 139 | patient139 | ED |
| 147 | patient147 | ED |


### Lei accepted · Mattia rejected — 4 cases

| # | Patient | Phase |
|---|---|---|
| 29 | patient029 | ES |
| 99 | patient099 | ES |
| 100 | patient100 | ES |
| 139 | patient139 | ES |


## agent (gpt-5.5)

95 disagreements out of 300 phases.


### Mattia accepted · Lei rejected — 82 cases

| # | Patient | Phase |
|---|---|---|
| 6 | patient006 | ES |
| 8 | patient008 | ES |
| 13 | patient013 | ED |
| 13 | patient013 | ES |
| 16 | patient016 | ED |
| 24 | patient024 | ED |
| 24 | patient024 | ES |
| 26 | patient026 | ED |
| 29 | patient029 | ED |
| 31 | patient031 | ED |
| 32 | patient032 | ED |
| 34 | patient034 | ED |
| 35 | patient035 | ED |
| 35 | patient035 | ES |
| 36 | patient036 | ED |
| 37 | patient037 | ED |
| 40 | patient040 | ES |
| 43 | patient043 | ED |
| 52 | patient052 | ED |
| 54 | patient054 | ED |
| 55 | patient055 | ED |
| 55 | patient055 | ES |
| 56 | patient056 | ED |
| 57 | patient057 | ED |
| 58 | patient058 | ES |
| 59 | patient059 | ED |
| 65 | patient065 | ED |
| 65 | patient065 | ES |
| 66 | patient066 | ED |
| 70 | patient070 | ED |
| 70 | patient070 | ES |
| 73 | patient073 | ES |
| 74 | patient074 | ES |
| 75 | patient075 | ES |
| 77 | patient077 | ES |
| 79 | patient079 | ED |
| 79 | patient079 | ES |
| 80 | patient080 | ED |
| 83 | patient083 | ES |
| 86 | patient086 | ES |
| 87 | patient087 | ES |
| 88 | patient088 | ED |
| 89 | patient089 | ES |
| 90 | patient090 | ED |
| 92 | patient092 | ED |
| 92 | patient092 | ES |
| 93 | patient093 | ES |
| 95 | patient095 | ED |
| 100 | patient100 | ED |
| 102 | patient102 | ED |
| 105 | patient105 | ED |
| 106 | patient106 | ED |
| 106 | patient106 | ES |
| 108 | patient108 | ED |
| 110 | patient110 | ED |
| 110 | patient110 | ES |
| 112 | patient112 | ED |
| 113 | patient113 | ED |
| 113 | patient113 | ES |
| 115 | patient115 | ED |
| 117 | patient117 | ED |
| 117 | patient117 | ES |
| 118 | patient118 | ED |
| 120 | patient120 | ED |
| 122 | patient122 | ES |
| 125 | patient125 | ED |
| 128 | patient128 | ES |
| 129 | patient129 | ED |
| 130 | patient130 | ES |
| 135 | patient135 | ED |
| 135 | patient135 | ES |
| 136 | patient136 | ED |
| 136 | patient136 | ES |
| 137 | patient137 | ES |
| 138 | patient138 | ED |
| 139 | patient139 | ES |
| 143 | patient143 | ES |
| 144 | patient144 | ED |
| 146 | patient146 | ED |
| 147 | patient147 | ED |
| 149 | patient149 | ED |
| 150 | patient150 | ED |


### Lei accepted · Mattia rejected — 13 cases

| # | Patient | Phase |
|---|---|---|
| 2 | patient002 | ES |
| 7 | patient007 | ED |
| 17 | patient017 | ED |
| 25 | patient025 | ED |
| 25 | patient025 | ES |
| 27 | patient027 | ES |
| 50 | patient050 | ES |
| 51 | patient051 | ED |
| 75 | patient075 | ED |
| 89 | patient089 | ED |
| 133 | patient133 | ED |
| 141 | patient141 | ES |
| 142 | patient142 | ED |

