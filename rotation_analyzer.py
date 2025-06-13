#!/usr/bin/env python3
"""
汎用パチンコ回転数分析ツール
- 任意のCSVファイルから回転数を推定
- 1円・4円パチンコ対応
- 大当り自動検出
- ベース計算
- 回転効率分析
"""

import pandas as pd
import numpy as np
import os
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
from datetime import datetime
import json


def setup_japanese_font():
    """日本語フォント設定"""
    try:
        japanese_fonts = [
            'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao PGothic',
            'IPAexGothic', 'Noto Sans CJK JP', 'DejaVu Sans'
        ]
        
        import matplotlib
        available_fonts = [f.name for f in matplotlib.font_manager.fontManager.ttflist]
        
        for font in japanese_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = font
                plt.rcParams['axes.unicode_minus'] = False
                return True
        
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        return False
    except ImportError:
        return False


class PachinkoRotationAnalyzer:
    """パチンコ回転数分析クラス"""
    
    def __init__(self, ball_cost=4, base_rotations=250):
        """
        初期化
        
        Args:
            ball_cost (int): 1玉の単価（1円パチンコ=1, 4円パチンコ=4）
            base_rotations (int): 1000円あたりの基準回転数
        """
        self.ball_cost = ball_cost
        self.base_rotations = base_rotations
        self.data = None
        self.analysis_results = {}
        
    def load_csv(self, csv_path):
        """
        CSVファイルを読み込み
        
        Args:
            csv_path (str): CSVファイルのパス
        """
        print(f"📁 CSVファイルを読み込み中: {os.path.basename(csv_path)}")
        
        try:
            self.data = pd.read_csv(csv_path)
            print(f"✅ データ読み込み完了: {len(self.data)}行")
            print(f"   列: {list(self.data.columns)}")
            
            # 必要な列の確認
            required_columns = ['y_value']
            if 'x_normalized' in self.data.columns:
                self.data['time_index'] = self.data['x_normalized']
            elif 'x_pixel' in self.data.columns:
                # x_pixelから正規化
                x_min, x_max = self.data['x_pixel'].min(), self.data['x_pixel'].max()
                self.data['time_index'] = (self.data['x_pixel'] - x_min) / (x_max - x_min)
            else:
                # インデックスから時間軸を作成
                self.data['time_index'] = np.linspace(0, 1, len(self.data))
            
            print(f"   収支範囲: {self.data['y_value'].min()} 〜 {self.data['y_value'].max()}円")
            return True
            
        except Exception as e:
            print(f"❌ CSV読み込みエラー: {e}")
            return False
    
    def detect_jackpots(self, min_rise=1000, min_distance=10):
        """
        大当りを自動検出
        
        Args:
            min_rise (int): 大当りと判定する最小上昇額
            min_distance (int): 大当り間の最小距離
        
        Returns:
            list: 大当り発生位置のリスト
        """
        print(f"🎰 大当り検出中（最小上昇額: {min_rise}円）...")
        
        # 収支の差分を計算
        diff = np.diff(self.data['y_value'])
        
        # 急激な上昇を検出
        peaks, properties = find_peaks(diff, height=min_rise, distance=min_distance)
        
        # 検出結果を調整（実際のデータポイントインデックス）
        jackpot_indices = peaks + 1  # diffのインデックスを元データに合わせる
        
        jackpots = []
        for idx in jackpot_indices:
            if idx < len(self.data):
                jackpots.append({
                    'index': idx,
                    'time': self.data.iloc[idx]['time_index'],
                    'balance': self.data.iloc[idx]['y_value'],
                    'rise_amount': diff[idx-1] if idx > 0 else 0
                })
        
        print(f"✅ 大当り検出完了: {len(jackpots)}回")
        for i, jp in enumerate(jackpots, 1):
            print(f"   {i}回目: 位置{jp['index']}, 上昇{jp['rise_amount']:.0f}円")
        
        return jackpots
    
    def find_normal_rotation_segments(self, jackpots):
        """
        通常回転区間を特定
        
        Args:
            jackpots (list): 大当り情報のリスト
        
        Returns:
            list: 通常回転区間のリスト
        """
        print("🔄 通常回転区間を分析中...")
        
        segments = []
        jackpot_indices = [jp['index'] for jp in jackpots]
        
        # 開始から最初の大当りまで
        if jackpot_indices:
            start_idx = 0
            end_idx = jackpot_indices[0]
            if end_idx - start_idx > 10:  # 最小区間長
                segments.append(self._analyze_segment(start_idx, end_idx, "開始〜1回目大当り"))
        
        # 大当り間の区間
        for i in range(len(jackpot_indices) - 1):
            start_idx = jackpot_indices[i]
            end_idx = jackpot_indices[i + 1]
            if end_idx - start_idx > 10:
                segments.append(self._analyze_segment(start_idx, end_idx, f"{i+1}〜{i+2}回目大当り間"))
        
        # 最後の大当りから終了まで
        if jackpot_indices:
            start_idx = jackpot_indices[-1]
            end_idx = len(self.data) - 1
            if end_idx - start_idx > 10:
                segments.append(self._analyze_segment(start_idx, end_idx, f"{len(jackpot_indices)}回目大当り〜終了"))
        
        # 大当りがない場合は全体を分析
        if not jackpot_indices:
            segments.append(self._analyze_segment(0, len(self.data) - 1, "全体（大当りなし）"))
        
        print(f"✅ 通常回転区間: {len(segments)}区間")
        
        return segments
    
    def _analyze_segment(self, start_idx, end_idx, name):
        """
        区間を分析
        
        Args:
            start_idx (int): 開始インデックス
            end_idx (int): 終了インデックス
            name (str): 区間名
        
        Returns:
            dict: 区間分析結果
        """
        segment_data = self.data.iloc[start_idx:end_idx]
        
        start_balance = segment_data.iloc[0]['y_value']
        end_balance = segment_data.iloc[-1]['y_value']
        loss = start_balance - end_balance  # 損失額（正の値）
        
        time_span = segment_data.iloc[-1]['time_index'] - segment_data.iloc[0]['time_index']
        data_points = len(segment_data)
        
        # 収支の傾向を分析
        slope = (end_balance - start_balance) / data_points if data_points > 1 else 0
        
        return {
            'name': name,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'start_balance': start_balance,
            'end_balance': end_balance,
            'loss': loss,
            'time_span': time_span,
            'data_points': data_points,
            'slope': slope,
            'is_normal_rotation': loss > 0 and slope < -5  # 通常回転の条件
        }
    
    def calculate_base_rate(self, segments):
        """
        ベース（回転率）を計算
        
        Args:
            segments (list): 通常回転区間のリスト
        
        Returns:
            dict: ベース計算結果
        """
        print("📊 ベース（回転率）を計算中...")
        
        # 通常回転区間のみを抽出
        normal_segments = [seg for seg in segments if seg['is_normal_rotation']]
        
        if not normal_segments:
            print("⚠️ 通常回転区間が見つかりません")
            return None
        
        # 各区間のベースを計算
        base_rates = []
        total_loss = 0
        total_time = 0
        
        for seg in normal_segments:
            if seg['loss'] > 0 and seg['time_span'] > 0:
                # この区間での1時間単位あたりの損失率
                loss_rate = seg['loss'] / seg['time_span']
                
                # 1000円で何時間遊べるか
                play_time_per_1000 = 1000 / loss_rate if loss_rate > 0 else 0
                
                # 1000円で何回転できるか（時間比例）
                estimated_rotations = play_time_per_1000 * seg['time_span'] * (seg['data_points'] / seg['time_span'])
                
                if estimated_rotations > 0:
                    base_rates.append(estimated_rotations)
                    total_loss += seg['loss']
                    total_time += seg['time_span']
        
        if not base_rates:
            print("⚠️ ベース計算に適した区間がありません")
            return None
        
        # 平均ベース計算
        avg_base = np.mean(base_rates)
        
        # より精密な計算（全体の損失率から）
        if total_loss > 0 and total_time > 0:
            overall_loss_rate = total_loss / total_time
            precise_base = (1000 / self.ball_cost) * (1 / overall_loss_rate) * total_time
            
            # 現実的な範囲でクリップ
            precise_base = max(10, min(precise_base, 500))
        else:
            precise_base = avg_base
        
        base_result = {
            'average_base': avg_base,
            'precise_base': precise_base,
            'normal_segments_count': len(normal_segments),
            'total_loss': total_loss,
            'total_time': total_time,
            'base_rates': base_rates
        }
        
        print(f"✅ ベース計算完了:")
        print(f"   平均ベース: {avg_base:.1f}回転/1000円")
        print(f"   精密ベース: {precise_base:.1f}回転/1000円")
        print(f"   分析区間数: {len(normal_segments)}区間")
        
        return base_result
    
    def calculate_rotation_efficiency(self, jackpots, base_result):
        """
        回転効率を計算
        
        Args:
            jackpots (list): 大当り情報
            base_result (dict): ベース計算結果
        
        Returns:
            dict: 回転効率情報
        """
        print("⚙️ 回転効率を計算中...")
        
        if not base_result:
            return None
        
        total_investment = abs(self.data['y_value'].min())  # 最大損失額
        total_return = self.data['y_value'].max() - self.data['y_value'].min()  # 収支の幅
        net_result = self.data['y_value'].iloc[-1] - self.data['y_value'].iloc[0]  # 最終収支
        
        # 推定総回転数
        estimated_total_rotations = (total_investment / 1000) * base_result['precise_base']
        
        # 大当り効率
        jackpot_efficiency = len(jackpots) / (estimated_total_rotations / 1000) if estimated_total_rotations > 0 else 0
        
        # 時間効率
        total_time = self.data['time_index'].iloc[-1] - self.data['time_index'].iloc[0]
        time_efficiency = estimated_total_rotations / total_time if total_time > 0 else 0
        
        efficiency = {
            'total_investment': total_investment,
            'total_return': total_return,
            'net_result': net_result,
            'estimated_total_rotations': estimated_total_rotations,
            'jackpot_count': len(jackpots),
            'jackpot_efficiency': jackpot_efficiency,
            'time_efficiency': time_efficiency,
            'investment_efficiency': (net_result / total_investment * 100) if total_investment > 0 else 0
        }
        
        print(f"✅ 回転効率計算完了:")
        print(f"   推定総回転数: {estimated_total_rotations:.0f}回転")
        print(f"   大当り効率: {jackpot_efficiency:.3f}回/1000回転")
        print(f"   投資効率: {efficiency['investment_efficiency']:.1f}%")
        
        return efficiency
    
    def generate_report(self, output_path=None):
        """
        分析レポートを生成
        
        Args:
            output_path (str): 出力パス（Noneの場合は自動生成）
        """
        if not hasattr(self, 'analysis_results') or not self.analysis_results:
            print("❌ 分析結果がありません。先にanalyze()を実行してください。")
            return
        
        # 出力パスの設定
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"pachinko_analysis_report_{timestamp}"
        
        # JSONレポート
        json_path = f"{output_path}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
        
        # テキストレポート
        txt_path = f"{output_path}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("パチンコ回転数分析レポート\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"分析日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write(f"玉単価: {self.ball_cost}円\n")
            f.write(f"データポイント数: {len(self.data)}\n\n")
            
            # 大当り情報
            jackpots = self.analysis_results.get('jackpots', [])
            f.write(f"大当り回数: {len(jackpots)}回\n")
            for i, jp in enumerate(jackpots, 1):
                f.write(f"  {i}回目: 上昇額{jp['rise_amount']:.0f}円\n")
            f.write("\n")
            
            # ベース情報
            base_result = self.analysis_results.get('base_result')
            if base_result:
                f.write(f"ベース（回転率）:\n")
                f.write(f"  平均: {base_result['average_base']:.1f}回転/1000円\n")
                f.write(f"  精密: {base_result['precise_base']:.1f}回転/1000円\n\n")
            
            # 効率情報
            efficiency = self.analysis_results.get('efficiency')
            if efficiency:
                f.write(f"回転効率:\n")
                f.write(f"  推定総回転数: {efficiency['estimated_total_rotations']:.0f}回転\n")
                f.write(f"  大当り効率: {efficiency['jackpot_efficiency']:.3f}回/1000回転\n")
                f.write(f"  投資効率: {efficiency['investment_efficiency']:.1f}%\n")
                f.write(f"  最終収支: {efficiency['net_result']:.0f}円\n")
        
        print(f"📋 レポート生成完了:")
        print(f"   JSON: {json_path}")
        print(f"   テキスト: {txt_path}")
    
    def plot_analysis(self, save_path=None):
        """
        分析結果を可視化
        
        Args:
            save_path (str): 保存パス（Noneの場合は表示のみ）
        """
        if not self.analysis_results:
            print("❌ 分析結果がありません")
            return
        
        setup_japanese_font()
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('パチンコ回転数分析結果', fontsize=16, fontweight='bold')
        
        jackpots = self.analysis_results.get('jackpots', [])
        segments = self.analysis_results.get('segments', [])
        
        # 1. 収支推移と大当り
        axes[0, 0].plot(self.data['time_index'], self.data['y_value'], 'b-', linewidth=1, label='収支推移')
        
        # 大当りマーカー
        for jp in jackpots:
            axes[0, 0].axvline(x=jp['time'], color='red', linestyle='--', alpha=0.7)
            axes[0, 0].scatter(jp['time'], jp['balance'], color='red', s=100, zorder=5)
        
        axes[0, 0].axhline(y=0, color='green', linestyle='-', alpha=0.5)
        axes[0, 0].set_title('収支推移と大当り発生')
        axes[0, 0].set_xlabel('時間（正規化）')
        axes[0, 0].set_ylabel('収支（円）')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].legend()
        
        # 2. 通常回転区間
        axes[0, 1].plot(self.data['time_index'], self.data['y_value'], 'lightgray', linewidth=1)
        
        colors = ['orange', 'green', 'purple', 'brown', 'pink']
        for i, seg in enumerate(segments):
            if seg['is_normal_rotation']:
                start_time = self.data.iloc[seg['start_idx']]['time_index']
                end_time = self.data.iloc[seg['end_idx']]['time_index']
                seg_data = self.data.iloc[seg['start_idx']:seg['end_idx']]
                
                color = colors[i % len(colors)]
                axes[0, 1].plot(seg_data['time_index'], seg_data['y_value'], 
                              color=color, linewidth=2, label=f'区間{i+1}')
        
        axes[0, 1].set_title('通常回転区間')
        axes[0, 1].set_xlabel('時間（正規化）')
        axes[0, 1].set_ylabel('収支（円）')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].legend()
        
        # 3. ベース分析
        base_result = self.analysis_results.get('base_result')
        if base_result and base_result['base_rates']:
            axes[1, 0].hist(base_result['base_rates'], bins=10, alpha=0.7, edgecolor='black')
            axes[1, 0].axvline(x=base_result['average_base'], color='red', linestyle='--', 
                             label=f'平均: {base_result["average_base"]:.1f}')
            axes[1, 0].axvline(x=base_result['precise_base'], color='green', linestyle='--', 
                             label=f'精密: {base_result["precise_base"]:.1f}')
            axes[1, 0].set_title('ベース分布')
            axes[1, 0].set_xlabel('回転数/1000円')
            axes[1, 0].set_ylabel('頻度')
            axes[1, 0].legend()
        
        # 4. 効率サマリー
        efficiency = self.analysis_results.get('efficiency')
        if efficiency:
            metrics = ['大当り回数', '推定総回転数', '投資効率(%)', '最終収支']
            values = [
                len(jackpots),
                efficiency['estimated_total_rotations'],
                efficiency['investment_efficiency'],
                efficiency['net_result']
            ]
            
            # 正規化（表示用）
            normalized_values = []
            for i, val in enumerate(values):
                if i == 0:  # 大当り回数
                    normalized_values.append(val * 10)  # 10倍して可視化
                elif i == 1:  # 回転数
                    normalized_values.append(val / 100)  # 100で割って可視化
                elif i == 2:  # 投資効率
                    normalized_values.append(abs(val))  # 絶対値
                else:  # 収支
                    normalized_values.append(abs(val) / 1000)  # 1000で割って可視化
            
            bars = axes[1, 1].bar(range(len(metrics)), normalized_values, alpha=0.7)
            axes[1, 1].set_title('効率サマリー')
            axes[1, 1].set_xticks(range(len(metrics)))
            axes[1, 1].set_xticklabels(metrics, rotation=45)
            
            # 実際の値をバーの上に表示
            for i, (bar, val) in enumerate(zip(bars, values)):
                if i == 1:  # 回転数
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                                   f'{val:.0f}', ha='center', va='bottom')
                elif i == 2:  # 投資効率
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                                   f'{val:.1f}%', ha='center', va='bottom')
                elif i == 3:  # 収支
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                                   f'{val:.0f}円', ha='center', va='bottom')
                else:
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                                   f'{val}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 グラフ保存: {save_path}")
        
        plt.show()
    
    def analyze(self, min_jackpot_rise=1000, min_jackpot_distance=10):
        """
        総合分析を実行
        
        Args:
            min_jackpot_rise (int): 大当り判定の最小上昇額
            min_jackpot_distance (int): 大当り間の最小距離
        
        Returns:
            dict: 分析結果
        """
        if self.data is None:
            print("❌ データが読み込まれていません")
            return None
        
        print("🔍 総合分析を開始...")
        
        # 1. 大当り検出
        jackpots = self.detect_jackpots(min_jackpot_rise, min_jackpot_distance)
        
        # 2. 通常回転区間分析
        segments = self.find_normal_rotation_segments(jackpots)
        
        # 3. ベース計算
        base_result = self.calculate_base_rate(segments)
        
        # 4. 回転効率計算
        efficiency = self.calculate_rotation_efficiency(jackpots, base_result)
        
        # 結果を保存
        self.analysis_results = {
            'jackpots': jackpots,
            'segments': segments,
            'base_result': base_result,
            'efficiency': efficiency,
            'settings': {
                'ball_cost': self.ball_cost,
                'base_rotations': self.base_rotations,
                'min_jackpot_rise': min_jackpot_rise,
                'min_jackpot_distance': min_jackpot_distance
            }
        }
        
        print("✅ 総合分析完了!")
        return self.analysis_results


def find_csv_files():
    """CSVファイルを再帰的に検索"""
    csv_files = []
    
    # 現在のディレクトリ
    current_dir_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    for f in current_dir_files:
        csv_files.append(('current', f))
    
    # よくあるフォルダもチェック
    common_folders = ['graphs', 'graphs/cropped_auto', 'data', 'output']
    
    for folder in common_folders:
        if os.path.exists(folder):
            try:
                folder_files = [f for f in os.listdir(folder) if f.endswith('.csv')]
                for f in folder_files:
                    csv_files.append((folder, f))
            except PermissionError:
                continue
    
    return csv_files


def main():
    """メイン処理"""
    print("=== 汎用パチンコ回転数分析ツール ===")
    print("任意のCSVファイルから回転数・ベースを分析します")
    
    # CSVファイル検索
    print("\n🔍 CSVファイルを検索中...")
    csv_files = find_csv_files()
    
    if not csv_files:
        print("❌ CSVファイルが見つかりません")
        print("\n💡 以下のいずれかを確認してください：")
        print("1. スマートグラフ抽出ツールでCSVを生成済みか")
        print("2. CSVファイルが正しいディレクトリにあるか")
        print("3. ファイル名が .csv で終わっているか")
        
        # 手動パス入力
        manual_path = input("\nCSVファイルのパスを直接入力しますか？ (ファイルパスまたはEnter): ").strip()
        if manual_path and os.path.exists(manual_path) and manual_path.endswith('.csv'):
            selected_path = manual_path
        else:
            return
    else:
        print(f"\n📁 見つかったCSVファイル ({len(csv_files)}個):")
        for i, (folder, file) in enumerate(csv_files, 1):
            if folder == 'current':
                print(f"{i}. {file} (現在のディレクトリ)")
            else:
                print(f"{i}. {file} ({folder}/)")
        
        try:
            file_num = int(input("ファイル番号を選択: "))
            if 1 <= file_num <= len(csv_files):
                folder, filename = csv_files[file_num - 1]
                if folder == 'current':
                    selected_path = filename
                else:
                    selected_path = os.path.join(folder, filename)
            else:
                print("❌ 無効な番号です")
                return
        except ValueError:
            print("❌ 数字を入力してください")
            return
    
    print(f"\n📄 選択されたファイル: {selected_path}")
    
    # パチンコ台設定
    print(f"\n🎰 パチンコ台設定:")
    ball_cost = input("玉単価 (1円パチンコ=1, 4円パチンコ=4, デフォルト=4): ").strip()
    ball_cost = int(ball_cost) if ball_cost else 4
    
    # 分析設定
    print(f"\n⚙️ 分析設定:")
    min_rise = input("大当り判定の最小上昇額（デフォルト=1000円）: ").strip()
    min_rise = int(min_rise) if min_rise else 1000
    
    print(f"\n🔄 分析を開始します...")
    
    # 分析実行
    analyzer = PachinkoRotationAnalyzer(ball_cost=ball_cost)
    
    if not analyzer.load_csv(selected_path):
        return
    
    results = analyzer.analyze(min_jackpot_rise=min_rise)
    
    if results:
        # 結果表示
        print(f"\n" + "="*50)
        print(f"📊 【分析結果サマリー】")
        print(f"="*50)
        print(f"🎰 台設定: {ball_cost}円パチンコ")
        print(f"🎯 大当り回数: {len(results['jackpots'])}回")
        
        if results['base_result']:
            base = results['base_result']['precise_base']
            print(f"🔄 ベース: {base:.1f}回転/1000円")
            
            # ベース評価
            if base >= 100:
                base_rating = "🟢 優秀"
            elif base >= 80:
                base_rating = "🟡 普通"
            else:
                base_rating = "🔴 厳しい"
            print(f"   評価: {base_rating}")
        
        if results['efficiency']:
            eff = results['efficiency']
            print(f"📈 推定総回転数: {eff['estimated_total_rotations']:.0f}回転")
            print(f"💰 投資効率: {eff['investment_efficiency']:.1f}%")
            print(f"💸 最終収支: {eff['net_result']:.0f}円")
            
            # 大当り効率
            if len(results['jackpots']) > 0:
                avg_interval = eff['estimated_total_rotations'] / len(results['jackpots'])
                print(f"🎊 平均大当り間隔: {avg_interval:.0f}回転")
        
        print(f"="*50)
        
        # 詳細分析表示
        if len(results['jackpots']) > 0:
            print(f"\n🎊 大当り詳細:")
            for i, jp in enumerate(results['jackpots'], 1):
                print(f"   {i}回目: +{jp['rise_amount']:.0f}円 (位置{jp['index']})")
        
        # 出力オプション
        print(f"\n💾 出力オプション:")
        save_report = input("詳細レポートを保存しますか？ (y/n, デフォルト: y): ").strip().lower()
        if save_report != 'n':
            analyzer.generate_report()
        
        show_graph = input("分析グラフを表示しますか？ (y/n, デフォルト: y): ").strip().lower()
        if show_graph != 'n':
            save_graph = input("グラフを保存しますか？ (y/n, デフォルト: n): ").strip().lower()
            save_path = None
            if save_graph == 'y':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.splitext(os.path.basename(selected_path))[0]
                save_path = f"rotation_analysis_{base_name}_{timestamp}.png"
            
            analyzer.plot_analysis(save_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 処理が中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
    finally:
        print("\n✨ 処理完了")