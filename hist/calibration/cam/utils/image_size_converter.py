import os
from PIL import Image

def resize_images_in_folder(folder_path, target_resolution=(1280, 720)):
    """
    将指定文件夹内所有图片缩放到目标分辨率。

    Args:
        folder_path (str): 包含图片的文件夹路径。
        target_resolution (tuple): 目标分辨率 (宽度, 高度)。
    """
    # 创建一个用于存放缩放后图片的子文件夹
    output_folder = os.path.join(folder_path, "resized")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"创建输出文件夹: {output_folder}")

    # 支持的图片文件扩展名
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        # 检查文件是否为支持的图片格式
        if filename.lower().endswith(supported_formats):
            file_path = os.path.join(folder_path, filename)
            
            # 确保它是一个文件而不是文件夹
            if os.path.isfile(file_path):
                try:
                    # 打开图片
                    with Image.open(file_path) as img:
                        print(f"正在处理: {filename}...")
                        
                        # 缩放图片
                        resized_img = img.resize(target_resolution, Image.Resampling.LANCZOS)
                        
                        # 构建新的文件名和保存路径
                        new_filename = f"resized_{filename}"
                        save_path = os.path.join(output_folder, new_filename)
                        
                        # 保存缩放后的图片
                        resized_img.save(save_path)
                        print(f"已保存到: {save_path}")

                except Exception as e:
                    print(f"处理文件 {filename} 时出错: {e}")

    print("\n所有图片处理完成！✅")

if __name__ == "__main__":
    # --- 使用说明 ---
    # 1. 将下面的 'your_image_folder_path' 替换为你的图片文件夹的实际路径。
    #    - Windows 示例: r"C:\Users\YourUser\Pictures\MyPhotos"
    #    - macOS/Linux 示例: "/home/user/pictures/myphotos"
    # 2. 运行这个脚本。
    # 3. 缩放后的图片将会被保存在原文件夹下的一个名为 "resized" 的新文件夹中。
    
    image_folder = "无人机标定图片"  # ⚠️ 请修改这里

    if not os.path.isdir(image_folder):
        print("错误：请将 image_folder 变量设置为一个有效的文件夹路径。")
    else:
        resize_images_in_folder(image_folder)