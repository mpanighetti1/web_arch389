Setting Up The Environment:

If using Anaconda to run this environment (recommended):
1. Download conda by using https://docs.conda.io/projects/miniconda/en/latest/
2. Run installer: Miniconda3-latest-Windows-x86_64.exe
3. Navigate to the project's directory 'tvWebServer - Panighetti'
4. Run: conda env create -f environment.yml
5. Run: conda activate webarch_env
6. Move to "Running the Web Server" section.

If NOT using Anaconda:
1. Navigate to the project's directory 'tvWebServer - Panighetti'
2. Run: python -m venv webarch_env
3. Activate webarch_env:
	On Windows,         Run: webarch_env\Scripts\activate
	On macOS and Linux, Run: source webarch_env/bin/activate
4. Install Requirements: 
	Run: pip install -r requirements.txt
5. Move to "Running the Web Server" section.

Running the Web Server:
1. Run: python app.py
2. Open your web-browser to the development server: http://localhost:8000/login
3. Create a new login by registering OR login using:
	username: admin
	password: admin
4. With admin you will have access to the System Administrator UI.
