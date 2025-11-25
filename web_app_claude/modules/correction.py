"""グラフ解析値の非線形補正"""

# 実測データに基づく補正テーブル
# (グラフ測定値, site7実測値/グラフ測定値の比率)
CORRECTION_TABLE = [
    (0, 0.750),      # 推定（0に近い値）
    (636, 0.755),    # 実測: site7=480, グラフ=636
    (2454, 0.905),   # 実測: site7=2220, グラフ=2454
    (3545, 0.942),   # 実測: site7=3340, グラフ=3545
    (8818, 0.971),   # 実測: site7=8560, グラフ=8818
    (9681, 0.962),   # 実測: site7=9310, グラフ=9681
    (14000, 0.969),  # 実測: site7=13560, グラフ=14000
    (15045, 0.964),  # 実測: site7=14500, グラフ=15045
    (25227, 0.977),  # 実測: site7=24650, グラフ=25227
    (30000, 0.990),  # 実測: site7=29700, グラフ=30000
]


def get_correction_factor(graph_value):
    """
    グラフ測定値に応じた補正係数を線形補間で取得

    Args:
        graph_value: グラフから測定された値（玉数）

    Returns:
        補正係数（0～1の範囲）
    """
    if graph_value <= 0:
        return CORRECTION_TABLE[0][1]

    # 線形補間
    for i in range(len(CORRECTION_TABLE) - 1):
        x1, ratio1 = CORRECTION_TABLE[i]
        x2, ratio2 = CORRECTION_TABLE[i + 1]

        if x1 <= graph_value <= x2:
            # 2点間を線形補間
            ratio = ratio1 + (ratio2 - ratio1) * (graph_value - x1) / (x2 - x1)
            return ratio

    # 範囲外の場合
    if graph_value > CORRECTION_TABLE[-1][0]:
        return CORRECTION_TABLE[-1][1]
    else:
        return CORRECTION_TABLE[0][1]


def apply_correction(graph_value):
    """
    グラフ測定値に補正を適用

    Args:
        graph_value: グラフから測定された値（玉数）

    Returns:
        補正後の値（玉数）
    """
    if graph_value is None or graph_value == 0:
        return graph_value

    # 負の値の場合、絶対値に対して補正を適用
    is_negative = graph_value < 0
    abs_value = abs(graph_value)

    correction_factor = get_correction_factor(abs_value)
    corrected_value = abs_value * correction_factor

    # 元の符号を戻す
    return -corrected_value if is_negative else corrected_value


def apply_correction_to_result(result):
    """
    解析結果の辞書に補正を適用

    Args:
        result: グラフ解析結果の辞書

    Returns:
        補正後の解析結果
    """
    corrected_result = result.copy()

    # 最大値を補正
    if 'max_val' in result and result['max_val'] is not None:
        original_max = result['max_val']
        corrected_max = apply_correction(original_max)
        corrected_result['max_val'] = int(round(corrected_max))

        # デバッグ情報を追加
        corrected_result['max_val_original'] = original_max
        corrected_result['max_val_correction_factor'] = get_correction_factor(abs(original_max))

    # 現在値を補正
    if 'current_val' in result and result['current_val'] is not None:
        corrected_result['current_val'] = int(round(apply_correction(result['current_val'])))

    # 最小値を補正
    if 'min_val' in result and result['min_val'] is not None:
        corrected_result['min_val'] = int(round(apply_correction(result['min_val'])))

    # 初当たり値を補正
    if 'first_hit_val' in result and result['first_hit_val'] is not None:
        corrected_result['first_hit_val'] = int(round(apply_correction(result['first_hit_val'])))

    return corrected_result
