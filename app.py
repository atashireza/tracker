import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # اگر برنامه به صورت مستقیم با پایتون خام اجرا شد، آن را به سیستم اجرای استریم‌لیت هدایت می‌کند
    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        "--server.address=0.0.0.0",
        "--server.port=8000",
        "--server.headless=true"
    ]
    sys.exit(stcli.main())
