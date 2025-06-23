import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# 指定した項目のデータを抽出する関数
def extract_data(df, item_name, context=None, period=None):
    query = f'項目名 == "{item_name}"'
    if context:
        query += f' & コンテキストID.str.contains("{context}")'
    if period:
        query += f' & 期間・時点 == "{period}"'

    return df.query(query)


def safe_get_value(df, item_name, context=None, period=None):
    result = extract_data(df, item_name, context, period)
    if not result.empty:
        return result["値"].iloc[0]
    else:
        return 0  # または None, np.nan など適切なデフォルト値


# 財務指標を計算する関数
def calculate_financial_metrics(df):
    # 必要なデータを抽出
    # 総資産
    total_assets_current = safe_get_value(
        df, "総資産額、経営指標等", "CurrentQuarterInstant"
    )
    total_assets_prior = safe_get_value(df, "総資産額、経営指標等", "Prior1YearInstant")
    total_assets_prior_quarter = safe_get_value(
        df, "総資産額、経営指標等", "Prior1QuarterInstant"
    )

    # 純資産
    net_assets_current = safe_get_value(
        df, "純資産額、経営指標等", "CurrentQuarterInstant"
    )
    net_assets_prior = safe_get_value(df, "純資産額、経営指標等", "Prior1YearInstant")
    net_assets_prior_quarter = safe_get_value(
        df, "純資産額、経営指標等", "Prior1QuarterInstant"
    )

    # 当期純利益
    net_income_current = safe_get_value(
        df,
        "親会社株主に帰属する当期純利益又は親会社株主に帰属する当期純損失（△）、経営指標等",
        "CurrentYTDDuration",
    )
    net_income_prior_ytd = safe_get_value(
        df,
        "親会社株主に帰属する当期純利益又は親会社株主に帰属する当期純損失（△）、経営指標等",
        "Prior1YTDDuration",
    )
    net_income_prior_year = safe_get_value(
        df,
        "親会社株主に帰属する当期純利益又は親会社株主に帰属する当期純損失（△）、経営指標等",
        "Prior1YearDuration",
    )

    # 売上（営業収益）
    revenue_current = safe_get_value(df, "営業収益、経営指標等", "CurrentYTDDuration")
    revenue_prior_ytd = safe_get_value(df, "営業収益、経営指標等", "Prior1YTDDuration")
    revenue_prior_year = safe_get_value(
        df, "営業収益、経営指標等", "Prior1YearDuration"
    )

    # 経常利益
    ordinary_income_current = safe_get_value(
        df, "経常利益又は経常損失（△）、経営指標等", "CurrentYTDDuration"
    )
    ordinary_income_prior_ytd = safe_get_value(
        df, "経常利益又は経常損失（△）、経営指標等", "Prior1YTDDuration"
    )
    ordinary_income_prior_year = safe_get_value(
        df, "経常利益又は経常損失（△）、経営指標等", "Prior1YearDuration"
    )

    # 自己資本比率
    equity_ratio_current = safe_get_value(
        df, "自己資本比率、経営指標等", "CurrentQuarterInstant"
    )
    equity_ratio_prior = safe_get_value(
        df, "自己資本比率、経営指標等", "Prior1YearInstant"
    )
    equity_ratio_prior_quarter = safe_get_value(
        df, "自己資本比率、経営指標等", "Prior1QuarterInstant"
    )

    # 文字列を数値に変換（マイナス値対応）
    def parse_value(value):
        # マイナス値を処理
        if isinstance(value, str) and value.strip() == "－":
            return 0
        return float(value)

    # 数値に変換
    total_assets_current = parse_value(total_assets_current)
    total_assets_prior = parse_value(total_assets_prior)
    total_assets_prior_quarter = parse_value(total_assets_prior_quarter)

    net_assets_current = parse_value(net_assets_current)
    net_assets_prior = parse_value(net_assets_prior)
    net_assets_prior_quarter = parse_value(net_assets_prior_quarter)

    net_income_current = parse_value(net_income_current)
    net_income_prior_ytd = parse_value(net_income_prior_ytd)
    net_income_prior_year = parse_value(net_income_prior_year)

    revenue_current = parse_value(revenue_current)
    revenue_prior_ytd = parse_value(revenue_prior_ytd)
    revenue_prior_year = parse_value(revenue_prior_year)

    ordinary_income_current = parse_value(ordinary_income_current)
    ordinary_income_prior_ytd = parse_value(ordinary_income_prior_ytd)
    ordinary_income_prior_year = parse_value(ordinary_income_prior_year)

    equity_ratio_current = parse_value(equity_ratio_current)
    equity_ratio_prior = parse_value(equity_ratio_prior)
    equity_ratio_prior_quarter = parse_value(equity_ratio_prior_quarter)

    # 財務指標の計算
    # 1. 収益性分析
    # ROE (Return on Equity) = 当期純利益 ÷ 自己資本 × 100
    roe_current = (net_income_current / net_assets_current) * 100
    roe_prior_ytd = (
        net_income_prior_ytd / net_assets_prior_quarter * 100
        if net_assets_prior_quarter != 0
        else 0
    )

    # ROA (Return on Assets) = 当期純利益 ÷ 総資産 × 100
    roa_current = (net_income_current / total_assets_current) * 100
    roa_prior_ytd = (
        net_income_prior_ytd / total_assets_prior_quarter * 100
        if total_assets_prior_quarter != 0
        else 0
    )

    # 売上高純利益率 = 当期純利益 ÷ 売上高 × 100
    net_profit_margin_current = (
        net_income_current / revenue_current * 100 if revenue_current != 0 else 0
    )
    net_profit_margin_prior_ytd = (
        net_income_prior_ytd / revenue_prior_ytd * 100 if revenue_prior_ytd != 0 else 0
    )
    net_profit_margin_prior_year = (
        net_income_prior_year / revenue_prior_year * 100
        if revenue_prior_year != 0
        else 0
    )

    # 売上高経常利益率 = 経常利益 ÷ 売上高 × 100
    ordinary_income_margin_current = (
        ordinary_income_current / revenue_current * 100 if revenue_current != 0 else 0
    )
    ordinary_income_margin_prior_ytd = (
        ordinary_income_prior_ytd / revenue_prior_ytd * 100
        if revenue_prior_ytd != 0
        else 0
    )
    ordinary_income_margin_prior_year = (
        ordinary_income_prior_year / revenue_prior_year * 100
        if revenue_prior_year != 0
        else 0
    )

    # 2. 安定性分析
    # 自己資本比率 = 自己資本 ÷ 総資産 × 100
    # 既にデータとして取得済み

    # 負債比率 = (総資産 - 自己資本) ÷ 自己資本 × 100
    debt_to_equity_current = (
        (total_assets_current - net_assets_current) / net_assets_current * 100
        if net_assets_current != 0
        else 0
    )
    debt_to_equity_prior = (
        (total_assets_prior - net_assets_prior) / net_assets_prior * 100
        if net_assets_prior != 0
        else 0
    )
    debt_to_equity_prior_quarter = (
        (total_assets_prior_quarter - net_assets_prior_quarter)
        / net_assets_prior_quarter
        * 100
        if net_assets_prior_quarter != 0
        else 0
    )

    # 3. 成長性分析
    # 売上高成長率 (前年同期比)
    revenue_growth_ytd = (
        (revenue_current - revenue_prior_ytd) / revenue_prior_ytd * 100
        if revenue_prior_ytd != 0
        else 0
    )

    # 当期純利益成長率 (前年同期比)
    net_income_growth_ytd = (
        (net_income_current - net_income_prior_ytd) / abs(net_income_prior_ytd) * 100
        if net_income_prior_ytd != 0
        else 0
    )

    # 経常利益成長率 (前年同期比)
    ordinary_income_growth_ytd = (
        (ordinary_income_current - ordinary_income_prior_ytd)
        / abs(ordinary_income_prior_ytd)
        * 100
        if ordinary_income_prior_ytd != 0
        else 0
    )

    # 総資産成長率 (前期末比)
    total_assets_growth = (
        (total_assets_current - total_assets_prior) / total_assets_prior * 100
        if total_assets_prior != 0
        else 0
    )

    # 純資産成長率 (前期末比)
    net_assets_growth = (
        ((net_assets_current - net_assets_prior) / net_assets_prior) * 100
        if net_assets_prior != 0
        else 0
    )

    # 結果を辞書として返す
    results = {
        # 収益性指標
        "ROE（自己資本利益率）": {
            "当四半期累計期間": roe_current,
            "前年度同四半期累計期間": roe_prior_ytd,
            "変化": roe_current - roe_prior_ytd,
        },
        "ROA（総資産利益率）": {
            "当四半期累計期間": roa_current,
            "前年度同四半期累計期間": roa_prior_ytd,
            "変化": roa_current - roa_prior_ytd,
        },
        "売上高純利益率": {
            "当四半期累計期間": net_profit_margin_current,
            "前年度同四半期累計期間": net_profit_margin_prior_ytd,
            "前期": net_profit_margin_prior_year,
            "変化（前年同期比）": net_profit_margin_current
            - net_profit_margin_prior_ytd,
        },
        "売上高経常利益率": {
            "当四半期累計期間": ordinary_income_margin_current,
            "前年度同四半期累計期間": ordinary_income_margin_prior_ytd,
            "前期": ordinary_income_margin_prior_year,
            "変化（前年同期比）": ordinary_income_margin_current
            - ordinary_income_margin_prior_ytd,
        },
        # 安定性指標
        "自己資本比率": {
            "当四半期会計期間末": equity_ratio_current * 100,  # パーセンテージに変換
            "前期末": equity_ratio_prior * 100,
            "前年度同四半期会計期間末": equity_ratio_prior_quarter * 100,
            "変化（前期末比）": (equity_ratio_current - equity_ratio_prior) * 100,
            "変化（前年同期比）": (equity_ratio_current - equity_ratio_prior_quarter)
            * 100,
        },
        "負債比率": {
            "当四半期会計期間末": debt_to_equity_current,
            "前期末": debt_to_equity_prior,
            "前年度同四半期会計期間末": debt_to_equity_prior_quarter,
            "変化（前期末比）": debt_to_equity_current - debt_to_equity_prior,
            "変化（前年同期比）": debt_to_equity_current - debt_to_equity_prior_quarter,
        },
        # 成長性指標
        "売上高成長率（前年同期比）": revenue_growth_ytd,
        "当期純利益成長率（前年同期比）": net_income_growth_ytd,
        "経常利益成長率（前年同期比）": ordinary_income_growth_ytd,
        "総資産成長率（前期末比）": total_assets_growth,
        "純資産成長率（前期末比）": net_assets_growth,
        # 基礎データ（単位：百万円）
        "基礎データ（百万円）": {
            "売上高（当四半期累計）": revenue_current / 1000000,
            "売上高（前年同四半期累計）": revenue_prior_ytd / 1000000,
            "当期純利益（当四半期累計）": net_income_current / 1000000,
            "当期純利益（前年同四半期累計）": net_income_prior_ytd / 1000000,
            "経常利益（当四半期累計）": ordinary_income_current / 1000000,
            "経常利益（前年同四半期累計）": ordinary_income_prior_ytd / 1000000,
            "総資産（当四半期末）": total_assets_current / 1000000,
            "総資産（前期末）": total_assets_prior / 1000000,
            "純資産（当四半期末）": net_assets_current / 1000000,
            "純資産（前期末）": net_assets_prior / 1000000,
        },
    }

    return results


# 財務指標の結果を表示する関数
def display_financial_metrics(results):
    print("=" * 80)
    print("財務指標分析結果")
    print("=" * 80)

    # 1. 収益性分析
    print("\n【1. 収益性分析】")
    print("-" * 80)

    # ROE
    print("ROE（自己資本利益率）:")
    print(
        f"  当四半期累計期間: {results['ROE（自己資本利益率）']['当四半期累計期間']:.2f}%"
    )
    print(
        f"  前年度同四半期累計期間: {results['ROE（自己資本利益率）']['前年度同四半期累計期間']:.2f}%"
    )
    print(f"  変化: {results['ROE（自己資本利益率）']['変化']:.2f}%ポイント")

    # ROA
    print("\nROA（総資産利益率）:")
    print(
        f"  当四半期累計期間: {results['ROA（総資産利益率）']['当四半期累計期間']:.2f}%"
    )
    print(
        f"  前年度同四半期累計期間: {results['ROA（総資産利益率）']['前年度同四半期累計期間']:.2f}%"
    )
    print(f"  変化: {results['ROA（総資産利益率）']['変化']:.2f}%ポイント")

    # 売上高純利益率
    print("\n売上高純利益率:")
    print(f"  当四半期累計期間: {results['売上高純利益率']['当四半期累計期間']:.2f}%")
    print(
        f"  前年度同四半期累計期間: {results['売上高純利益率']['前年度同四半期累計期間']:.2f}%"
    )
    print(f"  前期: {results['売上高純利益率']['前期']:.2f}%")
    print(
        f"  変化（前年同期比）: {results['売上高純利益率']['変化（前年同期比）']:.2f}%ポイント"
    )

    # 売上高経常利益率
    print("\n売上高経常利益率:")
    print(f"  当四半期累計期間: {results['売上高経常利益率']['当四半期累計期間']:.2f}%")
    print(
        f"  前年度同四半期累計期間: {results['売上高経常利益率']['前年度同四半期累計期間']:.2f}%"
    )
    print(f"  前期: {results['売上高経常利益率']['前期']:.2f}%")
    print(
        f"  変化（前年同期比）: {results['売上高経常利益率']['変化（前年同期比）']:.2f}%ポイント"
    )

    # 2. 安定性分析
    print("\n【2. 安定性分析】")
    print("-" * 80)

    # 自己資本比率
    print("自己資本比率:")
    print(f"  当四半期会計期間末: {results['自己資本比率']['当四半期会計期間末']:.2f}%")
    print(f"  前期末: {results['自己資本比率']['前期末']:.2f}%")
    print(
        f"  前年度同四半期会計期間末: {results['自己資本比率']['前年度同四半期会計期間末']:.2f}%"
    )
    print(
        f"  変化（前期末比）: {results['自己資本比率']['変化（前期末比）']:.2f}%ポイント"
    )
    print(
        f"  変化（前年同期比）: {results['自己資本比率']['変化（前年同期比）']:.2f}%ポイント"
    )

    # 負債比率
    print("\n負債比率:")
    print(f"  当四半期会計期間末: {results['負債比率']['当四半期会計期間末']:.2f}%")
    print(f"  前期末: {results['負債比率']['前期末']:.2f}%")
    print(
        f"  前年度同四半期会計期間末: {results['負債比率']['前年度同四半期会計期間末']:.2f}%"
    )
    print(f"  変化（前期末比）: {results['負債比率']['変化（前期末比）']:.2f}%ポイント")
    print(
        f"  変化（前年同期比）: {results['負債比率']['変化（前年同期比）']:.2f}%ポイント"
    )

    # 3. 成長性分析
    print("\n【3. 成長性分析】")
    print("-" * 80)

    print(f"売上高成長率（前年同期比）: {results['売上高成長率（前年同期比）']:.2f}%")
    print(
        f"当期純利益成長率（前年同期比）: {results['当期純利益成長率（前年同期比）']:.2f}%"
    )
    print(
        f"経常利益成長率（前年同期比）: {results['経常利益成長率（前年同期比）']:.2f}%"
    )
    print(f"総資産成長率（前期末比）: {results['総資産成長率（前期末比）']:.2f}%")
    print(f"純資産成長率（前期末比）: {results['純資産成長率（前期末比）']:.2f}%")

    # 基礎データ
    print("\n【4. 基礎データ（単位：百万円）】")
    print("-" * 80)

    for key, value in results["基礎データ（百万円）"].items():
        print(f"{key}: {value:,.2f}")


# グラフを生成する関数
def create_visualizations(results):
    # フォントの設定
    plt.rcParams["font.size"] = 12

    # 1. 収益性指標の比較グラフ
    plt.figure(figsize=(12, 8))

    # 収益性指標の比較データ
    metrics = ["ROE", "ROA", "売上高純利益率", "売上高経常利益率"]
    current_values = [
        results["ROE（自己資本利益率）"]["当四半期累計期間"],
        results["ROA（総資産利益率）"]["当四半期累計期間"],
        results["売上高純利益率"]["当四半期累計期間"],
        results["売上高経常利益率"]["当四半期累計期間"],
    ]
    prior_values = [
        results["ROE（自己資本利益率）"]["前年度同四半期累計期間"],
        results["ROA（総資産利益率）"]["前年度同四半期累計期間"],
        results["売上高純利益率"]["前年度同四半期累計期間"],
        results["売上高経常利益率"]["前年度同四半期累計期間"],
    ]

    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 8))
    rects1 = ax.bar(x - width / 2, current_values, width, label="当四半期累計期間")
    rects2 = ax.bar(x + width / 2, prior_values, width, label="前年度同四半期累計期間")

    ax.set_title("収益性指標の比較")
    ax.set_ylabel("割合（％）")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()

    # 値を表示
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(
                f"{height:.2f}%",
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
            )

    autolabel(rects1)
    autolabel(rects2)

    plt.tight_layout()
    plt.savefig("収益性指標.png")

    # 2. 安定性指標の推移グラフ
    plt.figure(figsize=(12, 8))

    # 安定性指標のデータ
    periods = ["前年度同四半期末", "前期末", "当四半期末"]
    equity_ratio_values = [
        results["自己資本比率"]["前年度同四半期会計期間末"],
        results["自己資本比率"]["前期末"],
        results["自己資本比率"]["当四半期会計期間末"],
    ]
    debt_ratio_values = [
        results["負債比率"]["前年度同四半期会計期間末"],
        results["負債比率"]["前期末"],
        results["負債比率"]["当四半期会計期間末"],
    ]

    fig, ax1 = plt.subplots(figsize=(12, 8))

    color = "tab:blue"
    ax1.set_xlabel("期間")
    ax1.set_ylabel("自己資本比率（％）", color=color)
    ax1.plot(periods, equity_ratio_values, "o-", color=color, label="自己資本比率")
    ax1.tick_params(axis="y", labelcolor=color)

    # 値を表示
    for i, v in enumerate(equity_ratio_values):
        ax1.text(i, v + 1, f"{v:.2f}%", color=color, ha="center")

    ax2 = ax1.twinx()
    color = "tab:red"
    ax2.set_ylabel("負債比率（％）", color=color)
    ax2.plot(periods, debt_ratio_values, "o-", color=color, label="負債比率")
    ax2.tick_params(axis="y", labelcolor=color)

    # 値を表示
    for i, v in enumerate(debt_ratio_values):
        ax2.text(i, v + 5, f"{v:.2f}%", color=color, ha="center")

    plt.title("安定性指標の推移")

    # 両方の凡例を追加
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    plt.tight_layout()
    plt.savefig("安定性指標.png")

    # 3. 成長率の比較グラフ
    plt.figure(figsize=(12, 8))

    growth_metrics = [
        "売上高成長率\n（前年同期比）",
        "当期純利益成長率\n（前年同期比）",
        "経常利益成長率\n（前年同期比）",
        "総資産成長率\n（前期末比）",
        "純資産成長率\n（前期末比）",
    ]

    growth_values = [
        results["売上高成長率（前年同期比）"],
        results["当期純利益成長率（前年同期比）"],
        results["経常利益成長率（前年同期比）"],
        results["総資産成長率（前期末比）"],
        results["純資産成長率（前期末比）"],
    ]

    plt.bar(
        growth_metrics,
        growth_values,
        color=["skyblue", "lightgreen", "salmon", "lightblue", "lightpink"],
    )
    plt.title("成長率の比較")
    plt.ylabel("成長率（％）")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # 値を表示
    for i, v in enumerate(growth_values):
        plt.text(i, v + (5 if v >= 0 else -15), f"{v:.2f}%", ha="center")

    plt.tight_layout()
    plt.savefig("成長率.png")
    return plt


# 財務データの要約レポートを生成する関数
def generate_summary_report(results):
    summary = {
        "title": f"財務分析サマリーレポート {name}",
        "date": datetime.now().strftime("%Y年%m月%d日"),
        "content": {},
    }

    # 収益性の要約
    if (
        results["ROE（自己資本利益率）"]["当四半期累計期間"]
        > results["ROE（自己資本利益率）"]["前年度同四半期累計期間"]
    ):
        roe_trend = "向上"
    else:
        roe_trend = "低下"

    # 収益性の評価 (ROE 10%以上を良好とする一般的基準)
    if results["ROE（自己資本利益率）"]["当四半期累計期間"] > 10:
        roe_evaluation = "良好"
    elif results["ROE（自己資本利益率）"]["当四半期累計期間"] > 5:
        roe_evaluation = "普通"
    else:
        roe_evaluation = "低調"

    summary["content"]["収益性"] = (
        f"当四半期の収益性は前年同期比で{roe_trend}しています。"
        f"ROE（自己資本利益率）は{results['ROE（自己資本利益率）']['当四半期累計期間']:.2f}%で、"
        f"{roe_evaluation}な水準です。"
        f"売上高純利益率は{results['売上高純利益率']['当四半期累計期間']:.2f}"
    )

    return summary