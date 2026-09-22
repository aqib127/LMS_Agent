from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LMS core ---
    lms_base_url: str
    lms_login_url: str
    lms_dashboard_url: str = "https://cms.bahria.edu.pk/Sys/Student/Dashboard.aspx"
    lms_base: str = "https://lms.bahria.edu.pk/Student"
    cms_base: str = "https://cms.bahria.edu.pk/Sys/Student"
    lms_enrollment_no: str = ""
    lms_password: str = ""
    lms_institute: str = "Lahore"
    lms_role: str = "Student"
    lms_post_login_url_pattern: str = "/dashboard"

    # --- LMS selectors (comma-separated fallbacks, first visible wins) ---
    lms_login_user_selectors: str = (
        'input[id*="Enrollment"],input[id*="tbEnrollment"],'
        'input[id*="txtEnrollment"],#BodyPH_tbEnrollment,'
        'input[name*="Enrollment"]'
    )
    lms_login_pass_selectors: str = (
        '#BodyPH_tbPassword,input[id*="tbPassword"],'
        'input[id*="txtPassword"],input[type="password"]'
    )
    lms_login_institute_selectors: str = (
        '#BodyPH_ddlInstituteID,select[id*="ddlInstitute"],'
        'select[name*="Institute"]'
    )
    lms_login_role_selectors: str = (
        '#BodyPH_ddlSubUserType,select[id*="SubUserType"],'
        'select[id*="ddlRole"]'
    )
    lms_login_submit_selectors: str = (
        '#BodyPH_btnLogin,a[id*="btnLogin"],input[id*="btnLogin"]'
    )

       # --- Email ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    email_to: str = ""


       # --- LLM ---
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:3b"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_host: str = "http://localhost:11434"

    # --- Runtime ---
    headless: bool = True
    poll_interval_minutes: int = 30
    tz: str = "Asia/Karachi"
    log_level: str = "INFO"


        # --- Discord ---
    discord_bot_token: str = ""
    discord_channel_id: str = ""

    # ---- Helpers ----
    def user_selectors(self) -> list[str]:
        return [s.strip() for s in self.lms_login_user_selectors.split(",") if s.strip()]

    def pass_selectors(self) -> list[str]:
        return [s.strip() for s in self.lms_login_pass_selectors.split(",") if s.strip()]

    def institute_selectors(self) -> list[str]:
        return [s.strip() for s in self.lms_login_institute_selectors.split(",") if s.strip()]

    def role_selectors(self) -> list[str]:
        return [s.strip() for s in self.lms_login_role_selectors.split(",") if s.strip()]

    def submit_selectors(self) -> list[str]:
        return [s.strip() for s in self.lms_login_submit_selectors.split(",") if s.strip()]


settings = Settings()
