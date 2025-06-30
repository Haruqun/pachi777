#!/usr/bin/env python3
"""
バッチ分析ツール
複数の画像を処理して結果をまとめてレポート
"""

import os
import glob
import json
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# 既存のツールをインポート
from graph_data_reader import GraphDataReader
from graph_analyzer_overlay import GraphAnalyzerOverlay

class BatchAnalyzer:
    """バッチ分析クラス"""
    
    def __init__(self, input_dir="graphs/original", output_dir="graphs/batch_analysis"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.report_dir = os.path.join(output_dir, "reports")
        
        # 出力ディレクトリ作成
        for dir_path in [self.output_dir, self.report_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # 日本語フォント設定
        try:
            japanese_fonts = [f for f in font_manager.fontManager.ttflist if 'Hiragino' in f.name]
            if japanese_fonts:
                plt.rcParams['font.family'] = japanese_fonts[0].name
        except:
            pass
        
        # 分析ツールを初期化
        self.reader = GraphDataReader(output_dir=os.path.join(output_dir, "extracted"))
        self.analyzer = GraphAnalyzerOverlay(
            csv_dir=os.path.join(output_dir, "extracted/csv"),
            output_dir=os.path.join(output_dir, "analyzed")
        )
    
    def process_all_images(self):
        """すべての画像を処理"""
        # 切り抜き済み画像ファイルを取得
        cropped_files = glob.glob(os.path.join("graphs/manual_crop/cropped", "*_graph_only.png"))
        cropped_files.sort()
        
        print(f"\nバッチ分析開始")
        print(f"対象画像: {len(cropped_files)}枚")
        print("=" * 60)
        
        all_results = []
        
        # 各画像を処理
        for i, img_path in enumerate(cropped_files):
            print(f"\n[{i+1}/{len(cropped_files)}] 処理中: {os.path.basename(img_path)}")
            
            # 1. グラフデータ読み取り
            read_result = self.reader.process_image(img_path)
            
            if read_result and read_result['colors_detected']:
                # 2. 分析オーバーレイ作成
                analysis_result = self.analyzer.process_image(img_path)
                
                if analysis_result:
                    # 結果を統合
                    combined_result = {
                        'original_image': os.path.basename(img_path),
                        'timestamp': datetime.now().isoformat(),
                        'graph_data': read_result,
                        'analysis': analysis_result['analysis']
                    }
                    all_results.append(combined_result)
            else:
                print(f"  → グラフが検出されませんでした")
        
        # 総合レポート生成
        self.generate_comprehensive_report(all_results)
        
        return all_results
    
    def generate_comprehensive_report(self, results):
        """総合レポートを生成"""
        if not results:
            print("\n分析結果がありません")
            return
        
        print(f"\n総合レポート生成中...")
        
        # 1. サマリー統計
        summary_stats = self.calculate_summary_statistics(results)
        
        # 2. 詳細レポート（JSON）
        detailed_report = {
            'report_timestamp': datetime.now().isoformat(),
            'total_images': len(results),
            'summary_statistics': summary_stats,
            'individual_results': results
        }
        
        report_path = os.path.join(self.report_dir, 
                                 f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, ensure_ascii=False, indent=2)
        
        # 3. CSV形式のサマリー
        self.generate_csv_summary(results)
        
        # 4. 視覚的なレポート
        self.generate_visual_report(results, summary_stats)
        
        # 5. テキストレポート
        self.generate_text_report(results, summary_stats)
        
        print(f"\nレポート生成完了:")
        print(f"  - 詳細レポート: {report_path}")
        print(f"  - CSVサマリー: {os.path.join(self.report_dir, 'summary.csv')}")
        print(f"  - 視覚レポート: {os.path.join(self.report_dir, 'visual_report.png')}")
        print(f"  - テキストレポート: {os.path.join(self.report_dir, 'text_report.txt')}")
    
    def calculate_summary_statistics(self, results):
        """サマリー統計を計算"""
        stats = {
            'total_analyzed': len(results),
            'by_color': {},
            'overall': {
                'max_values': [],
                'min_values': [],
                'final_values': [],
                'ranges': []
            }
        }
        
        # 各結果から統計情報を抽出
        for result in results:
            for color, analysis in result['analysis'].items():
                # 色別統計
                if color not in stats['by_color']:
                    stats['by_color'][color] = {
                        'count': 0,
                        'max_values': [],
                        'min_values': [],
                        'final_values': [],
                        'ranges': []
                    }
                
                stats['by_color'][color]['count'] += 1
                stats['by_color'][color]['max_values'].append(analysis['max']['value'])
                stats['by_color'][color]['min_values'].append(analysis['min']['value'])
                stats['by_color'][color]['final_values'].append(analysis['final']['value'])
                stats['by_color'][color]['ranges'].append(
                    analysis['max']['value'] - analysis['min']['value']
                )
                
                # 全体統計
                stats['overall']['max_values'].append(analysis['max']['value'])
                stats['overall']['min_values'].append(analysis['min']['value'])
                stats['overall']['final_values'].append(analysis['final']['value'])
                stats['overall']['ranges'].append(
                    analysis['max']['value'] - analysis['min']['value']
                )
        
        # 平均値などを計算
        for color_stats in stats['by_color'].values():
            if color_stats['max_values']:
                color_stats['avg_max'] = np.mean(color_stats['max_values'])
                color_stats['avg_min'] = np.mean(color_stats['min_values'])
                color_stats['avg_final'] = np.mean(color_stats['final_values'])
                color_stats['avg_range'] = np.mean(color_stats['ranges'])
        
        if stats['overall']['max_values']:
            stats['overall']['avg_max'] = np.mean(stats['overall']['max_values'])
            stats['overall']['avg_min'] = np.mean(stats['overall']['min_values'])
            stats['overall']['avg_final'] = np.mean(stats['overall']['final_values'])
            stats['overall']['avg_range'] = np.mean(stats['overall']['ranges'])
        
        return stats
    
    def generate_csv_summary(self, results):
        """CSV形式のサマリーを生成"""
        rows = []
        
        for result in results:
            for color, analysis in result['analysis'].items():
                row = {
                    '画像': result['original_image'],
                    '色': color,
                    '最大値': analysis['max']['value'],
                    '最大値位置': analysis['max']['x'],
                    '最小値': analysis['min']['value'],
                    '最小値位置': analysis['min']['x'],
                    '最終値': analysis['final']['value'],
                    '変動幅': analysis['max']['value'] - analysis['min']['value'],
                    '最終収支': analysis['final']['value']
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        csv_path = os.path.join(self.report_dir, 'summary.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        return df
    
    def generate_visual_report(self, results, summary_stats):
        """視覚的なレポートを生成"""
        if not results:
            return
        
        # 図のサイズを設定
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('パチンコデータ分析レポート', fontsize=16)
        
        # 1. 最終値の分布
        ax1 = axes[0, 0]
        final_values = summary_stats['overall']['final_values']
        ax1.hist(final_values, bins=10, color='skyblue', edgecolor='black')
        ax1.set_title('最終値の分布')
        ax1.set_xlabel('最終値')
        ax1.set_ylabel('頻度')
        ax1.axvline(np.mean(final_values), color='red', linestyle='--', 
                   label=f'平均: {np.mean(final_values):.0f}')
        ax1.legend()
        
        # 2. 変動幅の分布
        ax2 = axes[0, 1]
        ranges = summary_stats['overall']['ranges']
        ax2.hist(ranges, bins=10, color='lightgreen', edgecolor='black')
        ax2.set_title('変動幅の分布')
        ax2.set_xlabel('変動幅')
        ax2.set_ylabel('頻度')
        ax2.axvline(np.mean(ranges), color='red', linestyle='--', 
                   label=f'平均: {np.mean(ranges):.0f}')
        ax2.legend()
        
        # 3. 画像ごとの最終値
        ax3 = axes[1, 0]
        image_names = [r['original_image'].replace('.jpg', '') for r in results]
        final_values_by_image = [list(r['analysis'].values())[0]['final']['value'] 
                                 for r in results if r['analysis']]
        
        x_pos = range(len(final_values_by_image))
        bars = ax3.bar(x_pos, final_values_by_image)
        
        # 正の値は緑、負の値は赤
        for i, (bar, val) in enumerate(zip(bars, final_values_by_image)):
            if val >= 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        ax3.set_title('画像ごとの最終値')
        ax3.set_xlabel('画像')
        ax3.set_ylabel('最終値')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels([name[-10:] for name in image_names], rotation=45)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
        
        # 4. サマリー統計
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        summary_text = f"""
        分析サマリー
        
        総画像数: {summary_stats['total_analyzed']}
        
        全体統計:
        - 平均最大値: {summary_stats['overall'].get('avg_max', 0):.0f}
        - 平均最小値: {summary_stats['overall'].get('avg_min', 0):.0f}
        - 平均最終値: {summary_stats['overall'].get('avg_final', 0):.0f}
        - 平均変動幅: {summary_stats['overall'].get('avg_range', 0):.0f}
        
        プラス収支: {sum(1 for v in final_values if v > 0)}台
        マイナス収支: {sum(1 for v in final_values if v < 0)}台
        """
        
        ax4.text(0.1, 0.5, summary_text, fontsize=12, verticalalignment='center')
        
        plt.tight_layout()
        
        # 保存
        visual_path = os.path.join(self.report_dir, 'visual_report.png')
        plt.savefig(visual_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def generate_text_report(self, results, summary_stats):
        """テキストレポートを生成"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("パチンコデータ分析総合レポート")
        report_lines.append("=" * 80)
        report_lines.append(f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report_lines.append(f"分析画像数: {len(results)}枚")
        report_lines.append("")
        
        # 全体サマリー
        report_lines.append("【全体サマリー】")
        report_lines.append(f"平均最終値: {summary_stats['overall'].get('avg_final', 0):.0f}")
        report_lines.append(f"平均変動幅: {summary_stats['overall'].get('avg_range', 0):.0f}")
        
        final_values = summary_stats['overall']['final_values']
        report_lines.append(f"プラス収支台数: {sum(1 for v in final_values if v > 0)}台")
        report_lines.append(f"マイナス収支台数: {sum(1 for v in final_values if v < 0)}台")
        report_lines.append("")
        
        # 個別結果
        report_lines.append("【個別結果】")
        for i, result in enumerate(results, 1):
            report_lines.append(f"\n{i}. {result['original_image']}")
            
            for color, analysis in result['analysis'].items():
                report_lines.append(f"  色: {color}")
                report_lines.append(f"  最大値: {analysis['max']['value']:.0f} (位置: {analysis['max']['x']})")
                report_lines.append(f"  最小値: {analysis['min']['value']:.0f} (位置: {analysis['min']['x']})")
                report_lines.append(f"  最終値: {analysis['final']['value']:.0f}")
                report_lines.append(f"  変動幅: {analysis['max']['value'] - analysis['min']['value']:.0f}")
        
        # ファイルに保存
        text_path = os.path.join(self.report_dir, 'text_report.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

def main():
    """メイン処理"""
    analyzer = BatchAnalyzer()
    results = analyzer.process_all_images()
    
    print(f"\n分析完了！")
    print(f"処理済み画像数: {len(results)}")

if __name__ == "__main__":
    main()