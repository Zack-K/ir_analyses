import os
import toml
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    def __init__(self, path: str = None):
        self.config = self._load_config(path)

    def _load_config(self, path: str = None):
        """
        設定ファイル（config.toml）を読み込む。

        テスト時など、特定のパスから読み込みたい場合はpath引数を指定する。
        指定しない場合は、このファイルの位置を基準にプロジェクトルートを特定し、
        `config/config.toml` を読み込む。

        Args:
            path (str, optional): 読み込む設定ファイルの絶対パス. Defaults to None.

        Returns:
            dict: 設定ファイルの内容。読み込みに失敗した場合は空の辞書。
        """

        paths_to_check = []
        if path:
            # テスト時など、特定のパスが指定された場合
            paths_to_check.append(path)
        else:
            # 通常実行時：このファイルの場所を基準にパスを解決
            try:
                current_file_path = os.path.abspath(__file__)
                utils_dir = os.path.dirname(current_file_path)
                project_root = os.path.dirname(utils_dir)
                default_config_path = os.path.join(
                    project_root, "config", "config.toml"
                )
                paths_to_check.append(default_config_path)
            except NameError:
                # 対話モードなどで __file__ が未定義の場合のフォールバック
                paths_to_check.append("./config/config.toml")

        for config_path in paths_to_check:
            if os.path.exists(config_path):
                try:
                    config_data = toml.load(config_path)
                    logger.info("設定ファイルを読み込みました: %s", config_path)
                    return config_data  # ★成功したら即座に返す
                except Exception as e:
                    logger.error(
                        "設定ファイルの読み込みに失敗しました: %s, エラー: %s",
                        config_path,
                        e,
                    )
                    continue  # 次の候補パスへ

        logger.warning("有効な設定ファイルが見つかりませんでした。")
        return {}  # すべての候補で見つからなかった場合
