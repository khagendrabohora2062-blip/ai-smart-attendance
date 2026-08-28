import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()


class Config:

    # =========================================================
    # SECRET KEY
    # =========================================================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "local-development-secret-change-in-render"
    )

    # =========================================================
    # MYSQL DATABASE — TiDB Cloud
    # =========================================================

    MYSQL_HOST = os.getenv(
        "MYSQL_HOST",
        "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"
    )

    MYSQL_USER = os.getenv(
        "MYSQL_USER",
        "fa2WUDKvTiRY9ei.root"
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
            "4000"
        )
    )

    # =========================================================
    # MYSQL SETTINGS
    # =========================================================

    MYSQL_CURSORCLASS = "Cursor"
    MYSQL_AUTOCOMMIT = True

    # =========================================================
    # TiDB Cloud SSL
    # =========================================================

    MYSQL_CUSTOM_OPTIONS = {
        "ssl": {
            "ca": os.getenv(
                "MYSQL_SSL_CA",
                ""
            )
        }
    }