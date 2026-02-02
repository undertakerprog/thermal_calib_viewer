# Параметры и константы

## Детекция качества
- `start_temp = 50°C` — с этой температуры ищется устойчивое ухудшение.
- `streak = 3` — требование “подряд несколько кадров” для подтверждения.
- `threshold_normal = median + 3.5 * MAD`
- `threshold_defect = median + 8.0 * MAD`
- веса в score: `std=0.5`, `stripe=1.0`, `vignette=1.0`

## Генерация
- `step = 1.25°C` — шаг сетки температур (как в референсной программе).
- `end_temp = 70°C` — верхняя граница генерации.
- `degree = 3` — степень полинома (устойчивость > точность).

## StdCalib / LHE
- `shift = 15` — fixed‑point Q15 при интерполяции.
- `hist_size ≈ 1.5 * int16_max`
- `clipLo = 100`, `clipHi = 100`, `clipLimit = 100`
- `rangeScaleKeyPoint = 175`
