# ベースイメージとしてPythonの公式イメージを使用します。
# slim-busterは軽量なイメージで、容量を節約できます。
FROM python:3.9-slim-buster

# 作業ディレクトリを /app に設定します。
# 以降のコマンドはこのディレクトリ内で実行されます。
WORKDIR /app

# ホストのカレントディレクトリにある requirements.txt をコンテナの /app にコピーします。
# これにより、必要なPythonライブラリをインストールできます。
COPY requirements.txt .

# requirements.txt に記述されたPythonライブラリをインストールします。
# --no-cache-dir はキャッシュを使わないことでイメージサイズを削減します。
# -r はファイルから依存関係を読み込むことを意味します。
RUN pip install --no-cache-dir -r requirements.txt

# ホストのカレントディレクトリにあるすべてのファイルをコンテナの /app にコピーします。
# これには、PythonスクリプトやStreamlitアプリケーションのファイルが含まれます。
COPY . .

# ここでは、Streamlitアプリケーションがデフォルトで利用するポート（8501）を公開します。
# これは、他のコンテナやホストからStreamlitアプリケーションにアクセスできるようにするためです。
EXPOSE 8501

# コンテナが起動したときにデフォルトで実行されるコマンドを設定します。
# このDockerfileは、Streamlitアプリケーションの起動を想定しています。
# pythonスクリプトの実行は、docker-compose.ymlのservicesで個別に指定することもできます。
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]