#!/usr/bin/env python3
"""
画像高画質化ツール
複数の手法で画像品質を向上させる
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os
from pathlib import Path

class ImageEnhancer:
    """画像高画質化クラス"""
    
    def __init__(self, input_dir="graphs/manual_crop/cropped", output_dir="graphs/enhanced"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # 出力ディレクトリ作成
        os.makedirs(output_dir, exist_ok=True)
        
        # 各手法用のサブディレクトリ
        self.dirs = {
            'super_resolution': os.path.join(output_dir, 'super_resolution'),
            'denoise': os.path.join(output_dir, 'denoise'),
            'sharpen': os.path.join(output_dir, 'sharpen'),
            'combined': os.path.join(output_dir, 'combined')
        }
        
        for dir_path in self.dirs.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def enhance_with_opencv_sr(self, img_path):
        """OpenCVのSuper Resolution（EDSR）を使用"""
        # EDSRモデルが必要な場合はダウンロードが必要
        # ここでは代替として補間アルゴリズムを使用
        img = cv2.imread(img_path)
        
        # 2倍に拡大（高品質補間）
        height, width = img.shape[:2]
        upscaled = cv2.resize(img, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
        
        # エッジ保持しながらノイズ除去
        denoised = cv2.bilateralFilter(upscaled, 9, 75, 75)
        
        return denoised
    
    def denoise_image(self, img_path):
        """ノイズ除去"""
        img = cv2.imread(img_path)
        
        # Non-local Means Denoisingを適用
        denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        
        return denoised
    
    def sharpen_image(self, img_path):
        """シャープネス強化"""
        # PILを使用
        img_pil = Image.open(img_path)
        
        # シャープネスフィルタ
        sharpened = img_pil.filter(ImageFilter.SHARPEN)
        
        # さらにエンハンサーでシャープネス調整
        enhancer = ImageEnhance.Sharpness(sharpened)
        sharpened = enhancer.enhance(1.5)  # 1.5倍のシャープネス
        
        # OpenCV形式に変換
        sharpened_cv = cv2.cvtColor(np.array(sharpened), cv2.COLOR_RGB2BGR)
        
        return sharpened_cv
    
    def combined_enhancement(self, img_path):
        """複合的な高画質化"""
        img = cv2.imread(img_path)
        
        # 1. まず2倍に拡大（LANCZOS補間）
        height, width = img.shape[:2]
        upscaled = cv2.resize(img, (width*2, height*2), interpolation=cv2.INTER_LANCZOS4)
        
        # 2. ノイズ除去（エッジ保持）
        denoised = cv2.bilateralFilter(upscaled, 5, 50, 50)
        
        # 3. アンシャープマスキング
        gaussian = cv2.GaussianBlur(denoised, (0, 0), 2.0)
        sharpened = cv2.addWeighted(denoised, 1.5, gaussian, -0.5, 0)
        
        # 4. コントラスト調整（CLAHE）
        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        
        # CLAHEを明度チャンネルに適用
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_channel = clahe.apply(l_channel)
        
        enhanced = cv2.merge([l_channel, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # 5. 細部強調
        # エッジを検出して強調
        edges = cv2.Canny(enhanced, 50, 150)
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # エッジを薄く重ねる
        final = cv2.addWeighted(enhanced, 1.0, edges_colored, 0.1, 0)
        
        return final
    
    def process_image(self, img_path):
        """単一画像を処理"""
        base_name = os.path.basename(img_path)
        print(f"\n処理中: {base_name}")
        
        # 1. Super Resolution風（2倍拡大）
        sr_img = self.enhance_with_opencv_sr(img_path)
        sr_path = os.path.join(self.dirs['super_resolution'], base_name.replace('.png', '_sr.png'))
        cv2.imwrite(sr_path, sr_img)
        print(f"  - Super Resolution: {sr_img.shape[:2]}")
        
        # 2. ノイズ除去
        denoised_img = self.denoise_image(img_path)
        denoised_path = os.path.join(self.dirs['denoise'], base_name.replace('.png', '_denoised.png'))
        cv2.imwrite(denoised_path, denoised_img)
        print(f"  - ノイズ除去完了")
        
        # 3. シャープ化
        sharpened_img = self.sharpen_image(img_path)
        sharpened_path = os.path.join(self.dirs['sharpen'], base_name.replace('.png', '_sharp.png'))
        cv2.imwrite(sharpened_path, sharpened_img)
        print(f"  - シャープ化完了")
        
        # 4. 複合強化
        combined_img = self.combined_enhancement(img_path)
        combined_path = os.path.join(self.dirs['combined'], base_name.replace('.png', '_enhanced.png'))
        cv2.imwrite(combined_path, combined_img)
        print(f"  - 複合強化完了: {combined_img.shape[:2]}")
        
        return {
            'original': img_path,
            'super_resolution': sr_path,
            'denoised': denoised_path,
            'sharpened': sharpened_path,
            'combined': combined_path
        }
    
    def create_comparison(self, paths, output_name):
        """比較画像を作成"""
        # オリジナルと強化版を並べて表示
        original = cv2.imread(paths['original'])
        combined = cv2.imread(paths['combined'])
        
        # サイズを合わせる（combinedは2倍なので縮小）
        h_orig, w_orig = original.shape[:2]
        combined_resized = cv2.resize(combined, (w_orig, h_orig))
        
        # 横に並べる
        comparison = np.hstack([original, combined_resized])
        
        # テキストを追加
        cv2.putText(comparison, "Original", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(comparison, "Enhanced", (w_orig + 10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        comparison_path = os.path.join(self.output_dir, f"{output_name}_comparison.png")
        cv2.imwrite(comparison_path, comparison)
        
        return comparison_path
    
    def process_all(self):
        """すべての画像を処理"""
        import glob
        image_files = glob.glob(os.path.join(self.input_dir, "*.png"))
        
        print(f"画像高画質化開始")
        print(f"対象: {len(image_files)}枚")
        
        results = []
        
        for img_path in image_files[:3]:  # まず3枚でテスト
            paths = self.process_image(img_path)
            results.append(paths)
            
            # 比較画像作成
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            comparison_path = self.create_comparison(paths, base_name)
            print(f"  - 比較画像: {comparison_path}")
        
        print(f"\n完了！")
        print(f"強化画像の保存先:")
        for method, dir_path in self.dirs.items():
            print(f"  - {method}: {dir_path}")
        
        return results

def main():
    """メイン処理"""
    enhancer = ImageEnhancer()
    results = enhancer.process_all()

if __name__ == "__main__":
    main()