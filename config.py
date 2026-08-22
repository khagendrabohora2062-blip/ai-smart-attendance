import os


class Config:
    # =========================================================
    # SECRET KEY
    # =========================================================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "local-development-secret-change-in-render"
    )

    # =========================================================
    # MYSQL DATABASE
    # =========================================================

    MYSQL_HOST = os.getenv(
        "MYSQL_HOST",
        "localhost"
    )

    MYSQL_USER = os.getenv(
        "MYSQL_USER",
        "root"
    )

    MYSQL_PASSWORD = os.getenv(
        "MYSQL_PASSWORD",
        ""
    )

    MYSQL_DB = os.getenv(
        "MYSQL_DB",
        "smart_attendance"
    )

    MYSQL_PORT = int(
        os.getenv(
            "MYSQL_PORT",
            "3306"
        )
    )

    MYSQL_CURSORCLASS = "Cursor"

    MYSQL_AUTOCOMMIT = True