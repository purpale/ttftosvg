"""
TTF转SVG转换器 - 完整版本
支持批量转换、字体信息显示、自定义样式等功能
"""

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import RecordingPen
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom


class TTFtoSVGConverter:
    """TTF转SVG转换器类"""
    
    def __init__(self, ttf_path):
        """
        初始化转换器
        
        参数:
            ttf_path: TTF字体文件路径
        """
        self.ttf_path = ttf_path
        self.font = TTFont(ttf_path)
        self.glyphset = self.font.getGlyphSet()
        self.font_name = self._get_font_name()
        
    def _get_font_name(self):
        """获取字体名称"""
        try:
            # 尝试从name表获取字体名称
            for record in self.font['name'].names:
                if record.nameID == 1:  # Font family name
                    return record.toUnicode()
        except:
            pass
        return os.path.splitext(os.path.basename(self.ttf_path))[0]
    
    def get_font_info(self):
        """获取字体信息"""
        info = {
            'font_name': self.font_name,
            'num_glyphs': self.font['maxp'].numGlyphs,
            'ascent': self.font['hhea'].ascent,
            'descent': self.font['hhea'].descent,
            'x_height': getattr(self.font.get('OS/2'), 'sxHeight', 'N/A'),
            'cap_height': getattr(self.font.get('OS/2'), 'sCapHeight', 'N/A'),
        }
        return info
    
    def get_available_chars(self, start_code=0x4E00, end_code=0x9FA5):
        """获取字体支持的字符列表（默认中文字符范围）"""
        cmap = None
        for table in self.font['cmap'].tables:
            if table.platformID == 3 and table.platEncID in [1, 10]:  # Windows
                cmap = table.cmap
                break
        
        if cmap is None:
            for table in self.font['cmap'].tables:
                cmap = table.cmap
                break
        
        if cmap:
            chars = []
            for code in range(start_code, end_code + 1):
                if code in cmap:
                    chars.append(chr(code))
            return chars
        return []
    
    def char_to_svg(self, char, output_path=None, fill_color="black", 
                    stroke_color="none", stroke_width=0, 
                    viewbox_method="metrics"):
        """
        将单个字符转换为SVG
        
        参数:
            char: 要转换的字符
            output_path: 输出文件路径
            fill_color: 填充颜色
            stroke_color: 描边颜色
            stroke_width: 描边宽度
            viewbox_method: viewBox计算方式 ("metrics" 或 "bounds")
        
        返回:
            str: 生成的SVG内容
        """
        # 获取字形名称
        char_hex = format(ord(char), 'x').upper()
        glyph_name = f'uni{char_hex}'
        
        # 检查字符是否存在
        if glyph_name not in self.glyphset:
            if char in self.glyphset:
                glyph_name = char
            else:
                raise ValueError(f"字符 '{char}' 不在字体文件中")
        
        # 获取字形
        glyph = self.glyphset[glyph_name]
        
        # 使用SVGPathPen提取路径
        pen = SVGPathPen(self.glyphset)
        glyph.draw(pen)
        
        # 计算viewBox
        if viewbox_method == "metrics":
            try:
                width, lsb = self.font['hmtx'][glyph_name]
            except:
                width, lsb = 1000, 0
            ascent, descent = self.font['hhea'].ascent, self.font['hhea'].descent
            height = ascent - descent
            viewbox = f"{lsb} 0 {width} {height}"
        else:  # bounds
            glyph_bounds = glyph.bounds
            if glyph_bounds:
                xMin, yMin, xMax, yMax = glyph_bounds
                width = xMax - xMin
                height = yMax - yMin
                viewbox = f"{xMin} {yMin} {width} {height}"
                ascent = yMax
            else:
                viewbox = "0 0 1000 1000"
                ascent = 1000
        
        # 构建SVG内容
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     version="1.1" 
     viewBox="{viewbox}">
    <defs>
        <style>
            .glyph {{ 
                fill: {fill_color}; 
                stroke: {stroke_color};
                stroke-width: {stroke_width};
            }}
        </style>
    </defs>
    <g transform="matrix(1 0 0 -1 0 {ascent})">
        <path class="glyph" d="{pen.getCommands()}"/>
    </g>
</svg>'''
        
        # 保存文件
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"✓ 字符 '{char}' → {output_path}")
        
        return svg_content
    
    def batch_convert(self, chars, output_dir="output_svg", **kwargs):
        """
        批量转换字符为SVG文件
        
        参数:
            chars: 字符列表或迭代器
            output_dir: 输出目录
            **kwargs: 其他传递给char_to_svg的参数
        
        返回:
            dict: 转换结果统计
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 统计结果
        results = {'success': 0, 'failed': 0, 'failed_chars': []}
        
        for char in chars:
            try:
                # 构建输出文件名
                char_hex = format(ord(char), 'x').upper()
                output_path = os.path.join(output_dir, f"u{char_hex}.svg")
                
                # 转换
                self.char_to_svg(char, output_path, **kwargs)
                results['success'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['failed_chars'].append((char, str(e)))
        
        # 打印统计
        print(f"\n转换完成:")
        print(f"  ✓ 成功: {results['success']}")
        print(f"  ✗ 失败: {results['failed']}")
        
        if results['failed_chars']:
            print(f"\n失败的字符:")
            for char, error in results['failed_chars']:
                print(f"  '{char}': {error}")
        
        return results
    
    def text_to_svg(self, text, output_path=None, line_height=1.2, **kwargs):
        """
        将文本转换为SVG文件
        
        参数:
            text: 要转换的文本
            output_path: 输出文件路径
            line_height: 行高倍数
            **kwargs: 其他样式参数
        
        返回:
            str: 生成的SVG内容
        """
        lines = text.split('\n')
        line_heights = []
        
        # 计算每一行的宽度和高度
        max_width = 0
        total_height = 0
        
        for i, line in enumerate(lines):
            line_width = 0
            for char in line:
                try:
                    char_hex = format(ord(char), 'x').upper()
                    glyph_name = f'uni{char_hex}'
                    if glyph_name in self.glyphset:
                        width, _ = self.font['hmtx'][glyph_name]
                        line_width += width
                except:
                    line_width += 1000  # 默认宽度
            
            max_width = max(max_width, line_width)
        
        ascent, descent = self.font['hhea'].ascent, self.font['hhea'].descent
        base_height = ascent - descent
        line_spacing = base_height * line_height
        
        total_height = len(lines) * line_spacing
        
        # 构建SVG
        svg_parts = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     version="1.1" 
     viewBox="0 0 {max_width} {total_height}">
<defs>
    <style>
        .text {{ 
            fill: {kwargs.get('fill_color', 'black')}; 
        }}
    </style>
</defs>''']
        for i, line in enumerate(lines):
            y_pos = (i + 1) * line_spacing
            x_pos = 0
            for char in line:
                try:
                    char_hex = format(ord(char), 'x').upper()
                    glyph_name = f'uni{char_hex}'
                    if glyph_name in self.glyphset:
                        glyph = self.glyphset[glyph_name]
                        pen = SVGPathPen(self.glyphset)
                        glyph.draw(pen)
                        width, lsb = self.font['hmtx'][glyph_name]
                        svg_parts.append(f'''    <g transform="translate({x_pos - lsb}, {y_pos}) scale(1, -1) translate(0, -{ascent})">
        <path class="text" d="{pen.getCommands()}"/>
    </g>''')
                        x_pos += width
                    else:
                        x_pos += 1000
                except Exception as e:
                    print(f"处理字符 '{char}' 时出错: {e}")
                    x_pos += 1000
        svg_parts.append('</svg>')
        svg_content = '\n'.join(svg_parts)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"✓ 文本已转换为 {output_path}")
        
        return svg_content


# 示例使用
if __name__ == "__main__":
    # 使用示例
    converter = TTFtoSVGConverter("input.ttf") #ttf字体名字
    
    # 1. 显示字体信息
    print("=" * 50)
    print("字体信息:")
    info = converter.get_font_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    print("=" * 50)
    
    # 2. 转换单个字符
    i=input("\n转换单个字符--请输入字符:")
    converter.char_to_svg(i, i+".svg", fill_color="#333333")
    