"""
scripts/init_dirs.py
====================
初始化專案所需的所有資料夾。已存在的資料夾不會報錯（exist_ok=True）。

執行方式：
    python -m scripts.init_dirs
"""

from config.paths import ALL_DIRS, ROOT_DIR


def run():
    """依 config/paths.py 的 ALL_DIRS 清單建立所有資料夾。"""
    for directory in ALL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        # 印出相對路徑，比較好讀
        print(f"OK  {directory.relative_to(ROOT_DIR)}")
    print("\n所有資料夾已就緒。")


if __name__ == "__main__":
    run()
